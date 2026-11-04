<?php

namespace App\Services;

use App\Http\Controllers\Api\BusinessController;
use App\Models\AgentDecision;
use App\Models\Conversation;
use App\Models\JeffreyMemory;
use App\Models\Message;
use App\Models\Project;
use App\Models\Business;
use App\Models\Task;
use App\Models\User;
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
     * Process message in persistent conversation thread with contextual awareness, multimodal attachments, and tool calling.
     */
    public function talkInConversation(
        Conversation $conversation,
        string $userMessage,
        ?string $provider = null,
        ?int $userId = null,
        array $attachments = []
    ): Message {
        // Prepare lightweight metadata to store on the user message record
        $storedAttachmentsMeta = array_map(fn($a) => [
            'name' => $a['name'] ?? 'anexo',
            'url' => $a['url'] ?? '',
            'mime_type' => $a['mime_type'] ?? 'application/octet-stream',
            'size' => $a['size'] ?? 0,
            'is_voice' => !empty($a['is_voice']),
            'is_image' => !empty($a['is_image']),
        ], $attachments);

        // 1. Persist user message
        $userMsgRecord = Message::create([
            'conversation_id' => $conversation->id,
            'role' => 'user',
            'content' => $userMessage,
            'tokens' => !empty($storedAttachmentsMeta) ? ['attachments' => $storedAttachmentsMeta] : null,
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
        BusinessController::ensureCoreBusinessesExist();
        $businessId = $conversation->business_id;
        $projectId = $conversation->project_id;

        $project = $projectId ? Project::find($projectId) : null;
        $business = $businessId ? Business::find($businessId) : null;
        if (!$business) {
            // Default context includes TikTok Shop Afiliados if none selected
            $business = Business::where('slug', 'tiktok-shop-afiliados')->first();
        }

        $user = $userId ? User::find($userId) : User::first();
        $userProfileSummary = 'Comandante Spirandeli';
        if ($user) {
            $pData = is_array($user->profile_data) ? $user->profile_data : [];
            $title = $pData['title'] ?? 'Comandante do Império';
            $focusSlug = $pData['focus_business_slug'] ?? 'tiktok-shop-afiliados';
            $dailyGoal = $pData['daily_goal'] ?? '';
            $customRules = $pData['custom_instructions'] ?? '';
            $userProfileSummary = "{$user->name} ({$title}) | Foco: {$focusSlug}"
                . ($dailyGoal ? " | Meta Diária: {$dailyGoal}" : '')
                . ($customRules ? " | Diretriz Pessoal: {$customRules}" : '');
        }

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

        // 3. System Prompt & Live Tasks Context
        $projectContext = $project ? "PROJETO: {$project->name} ({$project->slug})" : "Sem projeto selecionado.";
        $businessAccountsStr = '';
        $businessParamsStr = '';
        if ($business) {
            $accs = collect($business->accounts_list)->map(fn($a) => ($a['platform'] ?? 'Conta') . ': ' . ($a['handle'] ?? '') . (!empty($a['account_id']) ? " [ID:{$a['account_id']}]" : ''))->implode(', ');
            $p = $business->automation_config;
            $businessAccountsStr = $accs ? " | Contas: {$accs}" : '';
            $businessParamsStr = !empty($p['niche']) ? " | Nicho: {$p['niche']} | Meta: " . ($p['daily_deliverables_goal'] ?? 3) . "/dia | CTA: " . ($p['cta_template'] ?? '') : '';
        }
        $businessContext = $business
            ? "NEGÓCIO ATIVO: {$business->name} (ID: {$business->id}, {$business->category}) - Teto: R$ {$business->budget_limit_brl}{$businessAccountsStr}{$businessParamsStr}"
            : "Sem negócio específico em foco.";

        $recentTasks = Task::latest()->limit(3)->get();
        $tasksContext = 'Nenhuma tarefa em background registrada no momento.';
        if ($recentTasks->isNotEmpty()) {
            $taskLines = [];
            foreach ($recentTasks as $rt) {
                $resText = is_array($rt->result) ? ($rt->result['response'] ?? '') : '';
                $resShort = $resText ? ' -> Resultado: ' . mb_substr($resText, 0, 180) . '...' : '';
                $taskLines[] = "#{$rt->id} [{$rt->status}] {$rt->title} ({$rt->agent_name}){$resShort}";
            }
            $tasksContext = implode(" | ", $taskLines);
        }

        // Check if cloud providers (Gemini or OpenAI) are configured via .env or UI Config;
        // if running purely on CPU local Ollama, use a compact prompt (~160 tokens) so CPU prompt-evaluation takes ~2s.
        $cloudConfigured = $this->aiGateway->isCloudExecutorConfigured();
        $forceLocal = in_array($provider ?: env('AI_PROVIDER', 'hybrid'), ['ollama', 'llama'], true);
        $useCompactLocalPrompt = !$cloudConfigured || $forceLocal;

        if ($useCompactLocalPrompt) {
            $systemPrompt = <<<PROMPT
Você é Jeffrey, o agente executivo central do SpirandeliEmpire OS.
PERFIL DO COMANDANTE: {$userProfileSummary}
Orçamento: R$ {$budgetStatus['current_spent_brl']}/R$ {$budgetStatus['monthly_limit_brl']}. {$projectContext} | {$businessContext}
Tarefas reais no sistema: {$tasksContext}
FERRAMENTAS: list_projects, inspect_project, read_project_file, list_businesses, get_business_status, update_business_automation, manage_business_accounts, run_business_automation, get_system_metrics, list_docker_containers, inspect_ai_models, create_task, list_tasks, web_search.
REGRA: Entregue a resposta diretamente agora. Se precisar executar uma ferramenta ou delegar pesquisa/trabalho/automação de negócio em 2º plano, adicione no final:
[TOOL_CALL: create_task, {"title": "Resumo da tarefa", "type": "research", "agent_name": "Research Agent"}]
Responda em português brasileiro de forma executiva, objetiva e direta.
PROMPT;
        } else {
            $systemPrompt = <<<PROMPT
Você é Jeffrey, o agente executivo central e arquiteto de software do SpirandeliEmpire OS.
Sua missão: Administrar o império de forma automatizada, gerir cada negócio usando suas contas vinculadas e parâmetros operacionais, planejar novos negócios digitais, analisar código de projetos existentes, gerenciar tarefas e coordenar a VPS.

PERFIL DO COMANDANTE ATIVO:
{$userProfileSummary}

DIRETRIZES FUNDAMENTAIS:
1. Respeite sempre o limite orçamentário mensal de R$ 200,00.
2. Status atual do orçamento: R$ {$budgetStatus['current_spent_brl']} gastos de R$ {$budgetStatus['monthly_limit_brl']}.
3. Priorize soluções seguras, eficientes e de custo zero.
4. Jamais invente versículos ou dados históricos falsos para o RISADA.exe.
5. Você gerencia diretamente os negócios (especialmente TikTok Shop Afiliados) usando suas contas vinculadas (@handle, ID de afiliado, link da vitrine) e parâmetros de automação.
6. Jamais diga que está pesquisando ou encaminhando à equipe sem disparar uma ferramenta real. Se precisar executar uma ação real, configurar contas/parâmetros de negócio ou criar uma tarefa em segundo plano, utilize a sintaxe exata:
[TOOL_CALL: nome_da_ferramenta, {"parametro": "valor"}]

CONTEXTO ATUAL:
{$projectContext}
{$businessContext}
TAREFAS ATIVAS/RECENTES:
{$tasksContext}

MEMÓRIA OPERACIONAL ATIVA:
{$formattedMemories}

{$toolsManifest}

Responda sempre com postura executiva, clara, proativa, técnica e em português brasileiro.
PROMPT;
        }

        // 4. Build message history (keep short on local CPU to avoid timeout)
        $historyLimit = $useCompactLocalPrompt ? 2 : 8;
        $previousMessages = Message::where('conversation_id', $conversation->id)
            ->where('id', '<', $userMsgRecord->id)
            ->orderBy('id', 'desc')
            ->limit($historyLimit)
            ->get()
            ->reverse();

        $conversationHistory = '';
        foreach ($previousMessages as $pm) {
            $sender = $pm->role === 'user' ? 'Comandante' : 'Jeffrey';
            $conversationHistory .= "{$sender}: {$pm->content}\n\n";
        }

        $fullPrompt = $conversationHistory . "Comandante: " . $userMessage;

        // Enrich prompt with any attached text/code/CSV/MD files and collect multimodal inline_data (images, voice audio, PDFs)
        $inlineMedia = [];
        $attachedTextsForLlama = [];
        foreach ($attachments as $att) {
            if (!empty($att['text_content'])) {
                $attName = $att['name'] ?? 'arquivo';
                $attachedTextsForLlama[] = "=== ARQUIVO ANEXADO: {$attName} ===\n" . $att['text_content'];
                $fullPrompt .= "\n\n[CONTEÚDO DO ANEXO {$attName}]:\n" . $att['text_content'];
            }
            if (!empty($att['data_base64']) && !empty($att['mime_type'])) {
                $inlineMedia[] = [
                    'mime_type' => $att['mime_type'],
                    'data' => $att['data_base64'],
                ];
            }
        }
        $fullPrompt .= "\n\nJeffrey:";

        // 5. Query AI Gateway with Role Division (Llama = Read/Analyze, Gemini/OpenAI = Execute Tasks)
        $taskRole = $this->aiGateway->getTokenManager()->classifyTaskRole($userMessage);
        if (!empty($inlineMedia)) {
            // Multimodal (Voice message, Image screenshot, or PDF) -> Gemini 3.8 Flash
            $response = $this->aiGateway->generate($fullPrompt, $systemPrompt, $provider, null, 'execute_task', $inlineMedia);
        } elseif ($cloudConfigured && !$forceLocal && (!empty($attachedTextsForLlama) || preg_match('/\b(analis|leia|ler|inspecion|resum).*?(e\s+depois|e\s+execut|e\s+crie|e\s+gere|e\s+rode)/iu', $userMessage))) {
            $rawContextForLlama = !empty($attachedTextsForLlama)
                ? implode("\n\n", $attachedTextsForLlama)
                : "{$projectContext}\n{$businessContext}\nTarefas: {$tasksContext}\nMemórias:\n{$formattedMemories}";
            $response = $this->aiGateway->analyzeWithLlamaThenExecute($rawContextForLlama, $fullPrompt, $systemPrompt, $provider);
        } else {
            $response = $this->aiGateway->generate($fullPrompt, $systemPrompt, $provider, null, $taskRole);
        }

        if ($response['success']) {
            $replyText = $response['response'];
        } else {
            $errDetail = $response['error'] ?? 'Provedores de IA offline ou sem modelos carregados.';
            $replyText = "Saudações, Comandante. Eu sou Jeffrey.\n\nRecebi sua solicitação: \"{$userMessage}\".\n\nO SpirandeliEmpire OS registrou a conversa com sucesso, porém o motor de inferência de IA relatou:\n> _{$errDetail}_\n\n**Para habilitar a geração de respostas completas:**\n1. **Modelo Local no Ollama (Custo R$ 0,00):** Baixe o modelo na VPS rodando:\n   `docker compose exec -it ollama ollama pull qwen2.5:3b`\n2. **Google Gemini (Free Tier 15 RPM):** Defina no arquivo `.env` da VPS:\n   `GEMINI_API_KEY=sua_chave_aqui`\n\nAssim que o modelo for baixado ou a chave for inserida, o SpirandeliEmpire OS responderá automaticamente através do gateway.";
        }

        $toolCallsExecuted = [];
        $toolResults = [];

        // 6. Detect and execute tool calls (supports nested JSON objects and multiple calls)
        $extractedCalls = $this->extractToolCalls($replyText);
        if (!empty($extractedCalls)) {
            foreach ($extractedCalls as $call) {
                $toolName = $call['name'];
                $toolArgs = $call['arguments'];

                $toolResult = $this->tools->executeTool($toolName, $toolArgs, $userId, $conversation->id);
                $toolCallsExecuted[] = ['name' => $toolName, 'arguments' => $toolArgs];
                $toolResults[] = ['name' => $toolName, 'result' => $toolResult];

                if ($toolName === 'create_task' && isset($toolResult['task']->id)) {
                    $tId = $toolResult['task']->id;
                    $tTitle = $toolResult['task']->title;
                    $replyText .= "\n\n---\n⚙️ **Tarefa Real Enfileirada [#$tId]:** _{$tTitle}_\nO worker em 2º plano já recebeu a missão. Acompanhe no **Monitor do Jeffrey** ao lado.";
                } else {
                    $formattedResult = json_encode($toolResult, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
                    $replyText .= "\n\n---\n**Execução de Ferramenta Real [{$toolName}]:**\n```json\n{$formattedResult}\n```";
                }
            }
        } elseif (
            preg_match('/(estou\s+(fazendo a pesquisa|pesquisando|encaminhando|trabalhando|analisando|coletando|buscando|iniciando)|vou\s+(pesquisar|encaminhar|iniciar|coletar|preparar))/iu', $replyText)
        ) {
            // Auto-enqueue a real background task if the model promised background work without emitting [TOOL_CALL]
            $taskPrompt = $userMessage;
            if (mb_strlen($userMessage) < 35 && $previousMessages->isNotEmpty()) {
                $lastUserMsg = $previousMessages->where('role', 'user')->last();
                if ($lastUserMsg) {
                    $taskPrompt = $lastUserMsg->content . ' — ' . $userMessage;
                }
            }
            $taskTitle = mb_substr($taskPrompt, 0, 90);

            $duplicateTask = Task::whereIn('status', ['pending', 'in_progress'])
                ->where('title', $taskTitle)
                ->where('created_at', '>=', now()->subMinutes(2))
                ->first();

            if (!$duplicateTask) {
                $toolArgs = [
                    'title' => $taskTitle,
                    'type' => 'research_and_execution',
                    'agent_name' => 'Research Agent',
                    'business_id' => $businessId,
                    'payload' => [
                        'prompt' => "Execute de forma completa, detalhada e prática a seguinte solicitação do Comandante e entregue o resultado final pronto:\n\n" . $taskPrompt,
                        'conversation_id' => $conversation->id,
                    ],
                ];
                $toolResult = $this->tools->executeTool('create_task', $toolArgs, $userId, $conversation->id);
                $toolCallsExecuted[] = ['name' => 'create_task', 'arguments' => $toolArgs];
                $toolResults[] = ['name' => 'create_task', 'result' => $toolResult];

                $createdTaskId = $toolResult['task']->id ?? '?';
                $replyText .= "\n\n---\n⚙️ **Tarefa Real Iniciada [#$createdTaskId]:** _{$taskTitle}_\nAcompanhe o progresso em tempo real no painel **Monitor do Jeffrey** ao lado. Assim que o worker finalizar, o resultado completo será postado nesta conversa.";
            }
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

    /**
     * Extract all [TOOL_CALL: tool_name, {...}] blocks supporting nested JSON braces.
     */
    protected function extractToolCalls(string $text): array
    {
        $calls = [];
        $offset = 0;
        while (preg_match('/\[TOOL_CALL:\s*([a-zA-Z0-9_]+)\s*(?:,\s*)?/s', $text, $m, PREG_OFFSET_CAPTURE, $offset)) {
            $fullMatchStart = $m[0][1];
            $fullMatchLen = strlen($m[0][0]);
            $toolName = trim($m[1][0]);
            $cursor = $fullMatchStart + $fullMatchLen;

            // Check if followed by JSON object '{'
            if ($cursor < strlen($text) && $text[$cursor] === '{') {
                $depth = 0;
                $inString = false;
                $escape = false;
                $jsonStart = $cursor;
                $jsonEnd = null;
                $len = strlen($text);

                for ($i = $cursor; $i < $len; $i++) {
                    $ch = $text[$i];
                    if ($escape) {
                        $escape = false;
                        continue;
                    }
                    if ($ch === '\\' && $inString) {
                        $escape = true;
                        continue;
                    }
                    if ($ch === '"') {
                        $inString = !$inString;
                        continue;
                    }
                    if (!$inString) {
                        if ($ch === '{') {
                            $depth++;
                        } elseif ($ch === '}') {
                            $depth--;
                            if ($depth === 0) {
                                $jsonEnd = $i;
                                break;
                            }
                        }
                    }
                }

                if ($jsonEnd !== null) {
                    $jsonStr = substr($text, $jsonStart, $jsonEnd - $jsonStart + 1);
                    $decoded = json_decode($jsonStr, true);
                    $calls[] = [
                        'name' => $toolName,
                        'arguments' => is_array($decoded) ? $decoded : [],
                    ];
                    $offset = $jsonEnd + 1;
                    continue;
                }
            }

            // Tool call with no arguments e.g. [TOOL_CALL: list_projects]
            $calls[] = [
                'name' => $toolName,
                'arguments' => [],
            ];
            $offset = $cursor;
        }

        return $calls;
    }
}
