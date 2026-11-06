<?php

namespace App\Services;

use App\Enums\AgentMessageRole;
use App\Enums\LogLevel;
use App\Exceptions\GeminiApiException;
use App\Models\AgentConversation;
use App\Models\AgentLog;
use App\Models\AgentMessage;
use App\Models\User;
use App\Services\Gemini\GeminiClient;
use App\Services\Gemini\Prompts\AutonomousCooPrompt;
use App\Services\Gemini\Tools\CheckUserScheduleTool;
use App\Services\Gemini\Tools\CreateCalendarEventTool;
use App\Services\Gemini\Tools\CreateReminderTool;
use App\Services\Gemini\Tools\CreateBusinessVentureTool;
use App\Services\Gemini\Tools\CreateTaskTool;
use App\Services\Gemini\Tools\CreateFunnelFixTaskTool;
use App\Services\Gemini\Tools\SaveBusinessLearningTool;
use App\Services\Gemini\Tools\SaveTikTokProductStrategyTool;
use App\Services\Gemini\Tools\ScaleWinningAssetTool;
use App\Services\Gemini\Tools\SubmitForHumanApprovalTool;
use App\Services\Gemini\Tools\ToolExecutionContext;
use App\Services\Gemini\Tools\ToolRegistry;
use Illuminate\Support\Facades\Log;

class GeminiAgentService
{
    private const MAX_FUNCTION_CALL_TURNS = 5;

    public function __construct(
        private readonly IntegrationService $integrationService,
        private readonly ToolRegistry $toolRegistry,
    ) {
    }

    /**
     * Factory para construir o serviço com todas as ferramentas nativas registradas no container.
     */
    public static function createDefault(
        IntegrationService $integrationService,
        BusinessService $businessService,
        TaskService $taskService,
        ApprovalService $approvalService,
        GoogleWorkspaceService $googleService,
        AppleCalDavService $appleService,
    ): self {
        $registry = new ToolRegistry([
            new CreateBusinessVentureTool($businessService),
            new CreateTaskTool($taskService),
            new SubmitForHumanApprovalTool($approvalService),
            new CheckUserScheduleTool(),
            new SaveTikTokProductStrategyTool(),
            new CreateCalendarEventTool($googleService, $appleService),
            new CreateReminderTool($googleService, $appleService),
            new ScaleWinningAssetTool($approvalService),
            new CreateFunnelFixTaskTool($taskService),
            new SaveBusinessLearningTool(),
        ]);

        return new self($integrationService, $registry);
    }

    public function getToolRegistry(): ToolRegistry
    {
        return $this->toolRegistry;
    }

    /**
     * Processa uma mensagem do usuário dentro de uma conversa, disparando o loop do Gemini 3.8.
     *
     * @param  AgentConversation  $conversation
     * @param  string  $userMessageText
     * @return AgentMessage A última mensagem (resposta textual) gerada pelo modelo
     *
     * @throws GeminiApiException
     */
    public function replyToUser(AgentConversation $conversation, string $userMessageText): AgentMessage
    {
        // 1. Persiste a mensagem do usuário
        $conversation->messages()->create([
            'role' => AgentMessageRole::User,
            'content' => $userMessageText,
            'parts' => [
                ['text' => $userMessageText],
            ],
        ]);

        return $this->orchestrateTurn($conversation);
    }

    /**
     * Dispara um turno autônomo (usado por workers e cron jobs do agente em background).
     *
     * @param  AgentConversation  $conversation
     * @param  string|null  $systemTriggerPrompt Prompt que contextualiza a execução do job
     * @return AgentMessage
     */
    public function runAutonomousTurn(AgentConversation $conversation, ?string $systemTriggerPrompt = null): AgentMessage
    {
        if ($systemTriggerPrompt !== null) {
            $conversation->messages()->create([
                'role' => AgentMessageRole::User,
                'content' => $systemTriggerPrompt,
                'parts' => [
                    ['text' => $systemTriggerPrompt],
                ],
            ]);
        }

        return $this->orchestrateTurn($conversation);
    }

    /**
     * Loop central de Function Calling e geração com o Gemini 3.8.
     */
    public function orchestrateTurn(AgentConversation $conversation): AgentMessage
    {
        $user = $conversation->user;
        $business = $conversation->business;

        // 0. Bloqueio Preventivo (Kill-Switch Admin & Limite Rígido de Tokens)
        if (! $user->isAiActive()) {
            AgentLog::record(
                $user->id,
                'ai_blocked',
                'Chamada de IA bloqueada pelo administrador (Kill-Switch ativo).',
                LogLevel::Warning,
                ['user_id' => $user->id],
                ['business_id' => $business?->id, 'agent_conversation_id' => $conversation->id]
            );
            throw new GeminiApiException('O acesso aos serviços de IA foi temporariamente suspenso para este usuário pela administração.');
        }

        if ($user->hasExceededMonthlyTokenLimit()) {
            AgentLog::record(
                $user->id,
                'ai_limit_exceeded',
                "Usuário atingiu o limite mensal de tokens ({$user->tokens_used_this_month} / {$user->monthly_token_limit}).",
                LogLevel::Warning,
                ['tokens_used' => $user->tokens_used_this_month, 'limit' => $user->monthly_token_limit],
                ['business_id' => $business?->id, 'agent_conversation_id' => $conversation->id]
            );
            throw new GeminiApiException('Limite mensal de tokens de IA atingido. Solicite uma expansão de cota ao administrador.');
        }

        // Recupera a chave e modelo apropriados para este usuário
        $apiKey = $this->integrationService->geminiApiKeyFor($user);
        if (empty($apiKey)) {
            throw new GeminiApiException('Nenhuma API Key do Gemini configurada (defina no painel de Integrações ou em GEMINI_API_KEY).');
        }

        $model = $this->integrationService->geminiModelFor($user) ?: config('services.gemini.model', 'gemini-3.8');
        $baseUrl = config('services.gemini.base_url', 'https://generativelanguage.googleapis.com/v1beta');

        $client = new GeminiClient(
            apiKey: $apiKey,
            model: $model,
            baseUrl: $baseUrl,
            timeout: 120
        );

        $systemInstruction = AutonomousCooPrompt::build(
            $user,
            $business,
            $conversation->context_type
        );

        $tools = $this->toolRegistry->toGeminiTools();
        $context = new ToolExecutionContext($user, $business, $conversation);

        $loopCount = 0;
        $lastModelMessage = null;

        while ($loopCount < self::MAX_FUNCTION_CALL_TURNS) {
            $loopCount++;

            // Constrói o histórico atualizado de mensagens da conversa
            $contents = $conversation->messages()
                ->orderBy('id')
                ->get()
                ->map(fn (AgentMessage $m) => $m->toGeminiContent())
                ->values()
                ->all();

            $startTime = microtime(true);

            AgentLog::record(
                $user->id,
                'gemini_request',
                "Enviando requisição ao modelo {$model} (turno {$loopCount}).",
                LogLevel::Debug,
                ['messages_in_payload' => count($contents)],
                ['business_id' => $business?->id, 'agent_conversation_id' => $conversation->id]
            );

            $response = $client->generateContent(
                contents: $contents,
                systemInstruction: $systemInstruction,
                tools: $tools
            );

            $latencyMs = (int) round((microtime(true) - $startTime) * 1000);

            $candidate = $response['candidates'][0] ?? null;
            if (! $candidate) {
                throw new GeminiApiException('O Gemini não retornou nenhum candidato de resposta.');
            }

            $finishReason = $candidate['finishReason'] ?? 'STOP';
            $usage = $response['usageMetadata'] ?? [];
            $promptTokens = (int) ($usage['promptTokenCount'] ?? 0);
            $completionTokens = (int) ($usage['candidatesTokenCount'] ?? 0);

            // FinOps: Registra consumo em ai_usage_logs e incrementa o saldo mensal
            $user->recordAiUsage(
                promptTokens: $promptTokens,
                completionTokens: $completionTokens,
                model: $model,
                context: $business ? 'business_operation' : 'incubator_chat',
                businessId: $business?->id,
                conversationId: $conversation->id,
                latencyMs: $latencyMs
            );

            $parts = $candidate['content']['parts'] ?? [];

            // Identifica se há chamadas de tools (Function Calls) nos parts
            $functionCalls = [];
            $textParts = [];

            foreach ($parts as $part) {
                if (isset($part['functionCall'])) {
                    $functionCalls[] = $part['functionCall'];
                } elseif (isset($part['text'])) {
                    $textParts[] = $part['text'];
                }
            }

            $textContent = implode("\n\n", $textParts);

            // Persiste a mensagem gerada pelo modelo (seja texto, functionCall ou mista)
            $lastModelMessage = $conversation->messages()->create([
                'role' => AgentMessageRole::Model,
                'content' => $textContent ?: null,
                'parts' => $parts,
                'prompt_tokens' => $promptTokens,
                'completion_tokens' => $completionTokens,
                'finish_reason' => $finishReason,
                'latency_ms' => $latencyMs,
            ]);

            $conversation->registerUsage($promptTokens, $completionTokens);

            // Se não houver chamadas de ferramentas, a resposta do modelo é final!
            if (empty($functionCalls)) {
                AgentLog::record(
                    $user->id,
                    'gemini_response_completed',
                    "Resposta final concluída pelo Gemini {$model}.",
                    LogLevel::Info,
                    ['finish_reason' => $finishReason, 'latency_ms' => $latencyMs],
                    ['business_id' => $business?->id, 'agent_conversation_id' => $conversation->id]
                );

                return $lastModelMessage;
            }

            // Caso haja chamadas de ferramentas, executa cada uma no PHP
            foreach ($functionCalls as $call) {
                $toolName = $call['name'] ?? 'unknown';
                $toolArgs = $call['args'] ?? [];

                $toolStart = microtime(true);

                AgentLog::record(
                    $user->id,
                    'tool_call',
                    "Agente invocando tool \"{$toolName}\".",
                    LogLevel::Info,
                    ['tool' => $toolName, 'args' => $toolArgs],
                    ['business_id' => $business?->id, 'agent_conversation_id' => $conversation->id]
                );

                $toolResult = $this->toolRegistry->execute($toolName, $toolArgs, $context);
                $toolDurationMs = (int) round((microtime(true) - $toolStart) * 1000);

                $isFailed = isset($toolResult['success']) && $toolResult['success'] === false;

                AgentLog::record(
                    $user->id,
                    'tool_result',
                    "Resultado da tool \"{$toolName}\" (" . ($isFailed ? 'Falha' : 'Sucesso') . ").",
                    $isFailed ? LogLevel::Warning : LogLevel::Success,
                    ['result' => $toolResult],
                    ['business_id' => $business?->id, 'agent_conversation_id' => $conversation->id],
                    $toolDurationMs
                );

                // Formato oficial do part de functionResponse da REST API v1beta do Gemini
                $functionResponsePart = [
                    'functionResponse' => [
                        'name' => $toolName,
                        'response' => [
                            'content' => $toolResult,
                        ],
                    ],
                ];

                // Persiste a resposta da tool no histórico para a próxima rodada
                $conversation->messages()->create([
                    'role' => AgentMessageRole::Tool,
                    'content' => json_encode($toolResult, JSON_UNESCAPED_UNICODE),
                    'parts' => [$functionResponsePart],
                    'tool_name' => $toolName,
                    'tool_args' => $toolArgs,
                    'tool_result' => $toolResult,
                    'tool_failed' => $isFailed,
                    'latency_ms' => $toolDurationMs,
                ]);
            }

            // O loop continua e reenviará os functionResponse de volta para o Gemini.
        }

        // Se atingiu o limite de segurança de loops de function calling
        Log::warning('Loop de Function Calling atingiu o limite máximo de iterações', [
            'conversation_id' => $conversation->id,
            'max_turns' => self::MAX_FUNCTION_CALL_TURNS,
        ]);

        return $lastModelMessage ?? $conversation->messages()->latest('id')->first();
    }
}

