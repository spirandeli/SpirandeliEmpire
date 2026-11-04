<?php

namespace App\Services;

use App\Models\AgentDecision;
use App\Models\Conversation;
use App\Models\JeffreyMemory;
use App\Models\Message;
use App\Models\Project;
use App\Models\Business;
use Illuminate\Support\Facades\Log;

class JeffreyOrchestratorService
{
    protected AiGatewayService $aiGateway;
    protected BudgetGuardService $budget;
    protected ToolRegistryService $tools;

    public function __construct(AiGatewayService $aiGateway, BudgetGuardService $budget, ToolRegistryService $tools)
    {
        $this->aiGateway = $aiGateway;
        $this->budget = $budget;
        $this->tools = $tools;
    }

    /**
     * Process message in persistent conversation thread with contextual awareness and tool calling capability.
     */
    public function talkInConversation(
        Conversation $conversation,
        string $userMessage,
        ?string $provider = null,
        ?int $userId = null
    ): Message {
        // 1. Persist user message
        $userMsgRecord = Message::create([
            'conversation_id' => $conversation->id,
            'role' => 'user',
            'content' => $userMessage,
        ]);

        // Auto-title conversation if it is the default title
        if ($conversation->title === 'Nova Conversa') {
            $words = explode(' ', trim($userMessage));
            $newTitle = implode(' ', array_slice($words, 0, 6));
            if (strlen($newTitle) > 40) {
                $newTitle = substr($newTitle, 0, 37) . '...';
            }
            $conversation->update(['title' => $newTitle ?: 'Conversa']);
        }

        // 2. Fetch context
        $businessId = $conversation->business_id;
        $projectId = $conversation->project_id;

        $project = $projectId ? Project::find($projectId) : null;
        $business = $businessId ? Business::find($businessId) : null;

        $activeMemories = JeffreyMemory::where('is_active', true)
            ->where(function ($q) use ($businessId) {
                $q->whereNull('business_id');
                if ($businessId) {
                    $q->orWhere('business_id', $businessId);
                }
            })
            ->get();

        $formattedMemories = '';
        if ($activeMemories->isNotEmpty()) {
            $formattedMemories = "<context_memories>\n";
            foreach ($activeMemories as $mem) {
                $cleanContent = htmlspecialchars($mem->content, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
                $formattedMemories .= "  <memory category=\"{$mem->category}\">{$cleanContent}</memory>\n";
            }
            $formattedMemories .= "</context_memories>";
        } else {
            $formattedMemories = 'Nenhuma memória operacional ativa no momento.';
        }

        $budgetStatus = $this->budget->getBudgetStatus();
        $availableTools = $this->tools->getAvailableTools();

        $toolsManifest = "FERRAMENTAS DISPONÍVEIS:\n";
        foreach ($availableTools as $t) {
            $paramsStr = json_encode($t['parameters'], JSON_UNESCAPED_UNICODE);
            $toolsManifest .= "- {$t['name']}: {$t['description']} (Parâmetros: {$paramsStr})\n";
        }

        // 3. System Prompt
        $projectContext = $project ? "PROJETO SELECIONADO: {$project->name} ({$project->slug}) - Caminho: {$project->path} - Branch: {$project->git_branch}" : "Nenhum projeto específico selecionado no momento.";
        $businessContext = $business ? "NEGÓCIO DIGITAL ATIVO: {$business->name} ({$business->category}) - Status: {$business->status} - Teto: R$ {$business->budget_limit_brl}" : "Nenhum negócio específico em foco.";

        $systemPrompt = <<<PROMPT
Você é Jeffrey, o agente executivo central e arquiteto de software do SpirandeliEmpire OS.
Sua missão: Administrar o império, planejar novos negócios digitais, analisar código de projetos existentes, gerenciar tarefas e coordenar a VPS.

DIRETRIZES FUNDAMENTAIS:
1. Respeite sempre o limite orçamentário mensal de R$ 200,00.
2. Status atual do orçamento: R$ {$budgetStatus['current_spent_brl']} gastos de R$ {$budgetStatus['monthly_limit_brl']}.
3. Priorize soluções seguras, eficientes e de custo zero.
4. Jamais invente versículos ou dados históricos falsos para o RISADA.exe.
5. Se precisar executar uma ação real de consulta ou modificação em projetos, negócios, containers ou métricas, utilize uma chamada de ferramenta com a sintaxe exata:
[TOOL_CALL: nome_da_ferramenta, {"parametro": "valor"}]

CONTEXTO ATUAL:
{$projectContext}
{$businessContext}

MEMÓRIA OPERACIONAL ATIVA:
{$formattedMemories}

{$toolsManifest}

Responda sempre com postura executiva, clara, proativa, técnica e em português brasileiro.
PROMPT;

        // 4. Build message history (last 10 messages for token efficiency)
        $previousMessages = Message::where('conversation_id', $conversation->id)
            ->where('id', '<', $userMsgRecord->id)
            ->orderBy('id', 'desc')
            ->limit(8)
            ->get()
            ->reverse();

        $conversationHistory = '';
        foreach ($previousMessages as $pm) {
            $sender = $pm->role === 'user' ? 'Comandante' : 'Jeffrey';
            $conversationHistory .= "{$sender}: {$pm->content}\n\n";
        }

        $fullPrompt = $conversationHistory . "Comandante: " . $userMessage . "\n\nJeffrey:";

        // 5. Query AI Gateway
        $response = $this->aiGateway->generate($fullPrompt, $systemPrompt, $provider);

        if ($response['success']) {
            $replyText = $response['response'];
        } else {
            $errDetail = $response['error'] ?? 'Provedores de IA offline ou sem modelos carregados.';
            $replyText = "Saudações, Comandante. Eu sou Jeffrey.\n\nRecebi sua solicitação: \"{$userMessage}\".\n\nO SpirandeliEmpire OS registrou a conversa com sucesso, porém o motor de inferência de IA relatou:\n> _{$errDetail}_\n\n**Para habilitar a geração de respostas completas:**\n1. **Modelo Local no Ollama (Custo R$ 0,00):** Baixe o modelo na VPS rodando:\n   `docker compose exec -it ollama ollama pull qwen2.5:3b`\n2. **Google Gemini (Free Tier 15 RPM):** Defina no arquivo `.env` da VPS:\n   `GEMINI_API_KEY=sua_chave_aqui`\n\nAssim que o modelo for baixado ou a chave for inserida, o SpirandeliEmpire OS responderá automaticamente através do gateway.";
        }

        $toolCallsExecuted = [];
        $toolResults = [];

        // 6. Detect and execute tool calls if present in the response
        if (preg_match('/\[TOOL_CALL:\s*([a-zA-Z0-9_]+),\s*(\{.*?\})\]/s', $replyText, $matches)) {
            $toolName = trim($matches[1]);
            $argsRaw = trim($matches[2]);
            $toolArgs = json_decode($argsRaw, true) ?: [];

            $toolResult = $this->tools->executeTool($toolName, $toolArgs, $userId);
            $toolCallsExecuted[] = ['name' => $toolName, 'arguments' => $toolArgs];
            $toolResults[] = ['name' => $toolName, 'result' => $toolResult];

            // Append execution summary
            $formattedResult = json_encode($toolResult, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
            $replyText .= "\n\n---\n**Execução de Ferramenta Real [{$toolName}]:**\n```json\n{$formattedResult}\n```";
        }

        // 7. Persist Assistant Message
        $assistantMsg = Message::create([
            'conversation_id' => $conversation->id,
            'role' => 'assistant',
            'content' => $replyText,
            'provider' => $response['provider'] ?? 'none',
            'model' => $response['model'] ?? 'offline',
            'latency_ms' => $response['latency_ms'] ?? 0,
            'tokens' => $response['tokens'] ?? null,
            'tool_calls' => !empty($toolCallsExecuted) ? $toolCallsExecuted : null,
            'tool_results' => !empty($toolResults) ? $toolResults : null,
            'fallback_used' => $response['fallback_used'] ?? false,
            'fallback_reason' => $response['fallback_reason'] ?? null,
        ]);

        // 8. Audit decision
        $this->auditDecision(
            'Jeffrey',
            $businessId,
            'conversation_interaction',
            'Interação conversacional persistente thread #' . $conversation->id,
            [
                'conversation_id' => $conversation->id,
                'provider' => $response['provider'] ?? 'none',
                'model' => $response['model'] ?? 'offline',
                'tool_calls' => $toolCallsExecuted,
                'latency_ms' => $response['latency_ms'] ?? 0,
            ]
        );

        return $assistantMsg;
    }

    /**
     * Legacy stateless chat method for backward compatibility (e.g. Telegram Bot / API direct).
     */
    public function talk(string $message, ?int $businessId = null, ?string $provider = null): array
    {
        // Auto-create or get latest system conversation
        $conversation = Conversation::firstOrCreate(
            ['title' => 'Linha Direta Jeffrey'],
            ['business_id' => $businessId]
        );

        $assistantMsg = $this->talkInConversation($conversation, $message, $provider);

        return [
            'reply' => $assistantMsg->content,
            'agent' => 'Jeffrey',
            'model' => $assistantMsg->model,
            'provider' => $assistantMsg->provider,
            'latency_ms' => $assistantMsg->latency_ms,
            'tool_calls' => $assistantMsg->tool_calls,
            'conversation_id' => $conversation->id,
            'fallback_used' => $assistantMsg->fallback_used,
            'fallback_reason' => $assistantMsg->fallback_reason,
            'budget_status' => $this->budget->getBudgetStatus(),
        ];
    }

    public function auditDecision(string $agentName, ?int $businessId, string $actionType, string $justification, array $payload = []): AgentDecision
    {
        return AgentDecision::create([
            'agent_name' => $agentName,
            'business_id' => $businessId,
            'action_type' => $actionType,
            'justification' => $justification,
            'input_payload' => $payload,
            'status' => 'executed',
        ]);
    }
}
