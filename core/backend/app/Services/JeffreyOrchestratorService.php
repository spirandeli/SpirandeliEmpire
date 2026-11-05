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

        // Check if cloud providers (Gemini or OpenAI) are configured & authorized for this user login;
        // if running purely on CPU local Ollama, use a compact prompt (~160 tokens) so CPU prompt-evaluation takes ~2s.
        $availabilityCfg = $this->aiGateway->getAiAvailabilityConfig();
        $enabledCaps = $availabilityCfg['enabled_capabilities'] ?? [];
        $cloudConfigured = $this->aiGateway->isCloudExecutorConfigured($user);
        $forceLocal = in_array($provider ?: env('AI_PROVIDER', 'hybrid'), ['ollama', 'llama'], true);
        $useCompactLocalPrompt = !$cloudConfigured || $forceLocal;

        if ($useCompactLocalPrompt) {
            $systemPrompt = <<<PROMPT
Você é Jeffrey, o co-piloto executivo do SpirandeliEmpire OS (inspirado no padrão Antigravity: inteligente, parceiro, claro e resolutivo).
PERFIL DO COMANDANTE: {$userProfileSummary}
Orçamento: R$ {$budgetStatus['current_spent_brl']}/R$ {$budgetStatus['monthly_limit_brl']}. {$projectContext} | {$businessContext}
Tarefas reais no sistema: {$tasksContext}
FERRAMENTAS: list_projects, inspect_project, read_project_file, list_businesses, get_business_status, update_business_automation, manage_business_accounts, run_business_automation, get_system_metrics, list_docker_containers, inspect_ai_models, create_task, list_tasks, web_search.
REGRAS OBRIGATÓRIAS:
1. NUNCA responda em JSON puro ou bloco de código sem explicação. Responda com texto executivo claro em português brasileiro.
2. JAMAIS invente links falsos como 'https://www.tiktokshop.com.br/...'. Use EXCLUSIVAMENTE URLs reais presentes em <live_web_research_results> ou buscas no formato https://www.tiktok.com/search?q=Termo.
3. Se precisar delegar tarefa em 2º plano, adicione no final:
[TOOL_CALL: create_task, {"title": "Resumo da tarefa", "type": "research", "agent_name": "Research Agent"}]
Responda em português brasileiro de forma executiva, clara e proativa.
PROMPT;
        } else {
            $systemPrompt = <<<PROMPT
Você é Jeffrey, o co-piloto executivo, estrategista e orquestrador de operações de IA do SpirandeliEmpire OS.
Sua missão: Atuar lado a lado com o Comandante com a máxima excelência, administrando negócios digitais, coordenando agentes em background, analisando código e dados de mercado, e gerindo a VPS com responsabilidade financeira.

<commander_profile>
{$userProfileSummary}
Orçamento Mensal: R$ {$budgetStatus['monthly_limit_brl']} (Gasto Atual: R$ {$budgetStatus['current_spent_brl']})
</commander_profile>

<business_context>
{$projectContext}
{$businessContext}
</business_context>

<tasks_and_telemetry>
{$tasksContext}
</tasks_and_telemetry>

<operational_memories>
{$formattedMemories}
</operational_memories>

<anti_hallucination_rules>
1. Respeite sempre o limite orçamentário mensal de R$ 200,00.
2. DADOS EXTERNOS E BUSCA NA WEB: Quando precisar de informações em tempo real da internet (preços reais, concorrentes, produtos em alta no TikTok Shop Brasil), acione autonomamente a ferramenta `web_search` passando uma query específica e focada. Utilize EXCLUSIVAMENTE as URLs reais retornadas ou links de busca no formato https://www.tiktok.com/search?q=Termo. Jamais invente domínios inexistentes como 'tiktokshop.com.br/slug-falso'.
3. TELEMETRIA DA VPS E GESTÃO: Para verificar CPU/RAM/Disco da VPS, acione `get_system_metrics`. Para listar ou inspecionar negócios e projetos, use `list_businesses` ou `list_projects`.
4. DELEGAÇÃO AO WORKER (TAREFAS EM 2º PLANO): Quando o Comandante pedir para produzir roteiros, minerar produtos ou criar campanhas em background, acione `create_task` ou `create_task_pipeline` para que os workers no Celery/Redis executem de forma assíncrona sem travar o painel.
5. Jamais responda apenas com uma tag `[TOOL_CALL: ...]` vazia sem texto executivo para o Comandante.
</anti_hallucination_rules>

<tools_catalog>
{$toolsManifest}
</tools_catalog>

<response_guidelines>
1. POSTURA E ESTILO EXECUTIVO ANTIGRAVITY:
   - Adote a postura executiva, parceria inteligente, clareza cirúrgica e tom consultivo proativo inspirados no Antigravity da equipe Google DeepMind.
   - Responda em português brasileiro impecável, direto, polido e estratégico. Trate o operador como Comandante.
2. PROIBIÇÃO ABSOLUTA DE DUMP DE JSON OU DADOS BRUTOS:
   - NUNCA responda ao Comandante com um JSON isolado, tags soltas `{...}` ou dados brutos sem contextualização executiva.
   - Sempre que consultar ferramentas ou apurar dados, forneça um texto executivo analisando as informações, trazendo insights estratégicos e sugerindo os próximos passos.
3. FORMATAÇÃO MARKDOWN RICA E ESTRUTURADA:
   - Use formatação Markdown rica: títulos estruturados (###), bullet points com destaques em negrito, tabelas limpas para produtos/métricas e caixas de alerta explicativas quando relevante.
4. SUGESTÕES PRÁTICAS DE AÇÃO:
   - Ao final da resposta, inclua sempre 2 a 3 sugestões de ações práticas imediatas para o Comandante avançar com um clique, no formato estrito:
<suggested_actions>
- Sugestão 1
- Sugestão 2
- Sugestão 3
</suggested_actions>
</response_guidelines>
PROMPT;
        }

        // 4. Build message history (both native turns for Gemini/OpenAI and flat text for local Llama)
        $historyLimit = $useCompactLocalPrompt ? 3 : 10;
        $previousMessages = Message::where('conversation_id', $conversation->id)
            ->where('id', '<', $userMsgRecord->id)
            ->orderBy('id', 'desc')
            ->limit($historyLimit)
            ->get()
            ->reverse();

        $conversationTurns = [];
        $conversationHistory = '';
        foreach ($previousMessages as $pm) {
            $sender = $pm->role === 'user' ? 'Comandante' : 'Jeffrey';
            $conversationHistory .= "{$sender}: {$pm->content}\n\n";
            $conversationTurns[] = [
                'role' => $pm->role === 'user' ? 'user' : 'model',
                'content' => $pm->content,
            ];
        }

        // Enrich clean prompt turn with any attached text files / multimodal inline_data
        $cleanUserPrompt = $userMessage;
        $inlineMedia = [];
        foreach ($attachments as $att) {
            if (!empty($att['text_content'])) {
                $attName = $att['name'] ?? 'arquivo';
                $cleanUserPrompt .= "\n\n[CONTEÚDO DO ANEXO {$attName}]:\n" . $att['text_content'];
            }
            if (!empty($att['data_base64']) && !empty($att['mime_type'])) {
                $inlineMedia[] = [
                    'mime_type' => $att['mime_type'],
                    'data' => $att['data_base64'],
                ];
            }
        }

        // For local Ollama (which uses flat text completion), prepend history turns.
        // For Gemini/OpenAI (native multi-turn), send clean user turn without duplicating history turns.
        $promptForGateway = $useCompactLocalPrompt
            ? ($conversationHistory . "Comandante: " . $cleanUserPrompt . "\n\nJeffrey:")
            : $cleanUserPrompt;

        // 5. Query AI Gateway. Gemini is the PRIMARY AI for all tasks, direct multimodal, and live reasoning.
        $taskRole = $this->aiGateway->getTokenManager()->classifyTaskRole($userMessage);
        $response = $this->aiGateway->generate($promptForGateway, $systemPrompt, $provider, null, $taskRole, $inlineMedia, $user, $conversationTurns);

        if ($response['success']) {
            $replyText = $this->sanitizeLlmText($response['response']);
            // Anti-hallucination URL sanitizer: replace any invented tiktokshop.com.br/slug link with a real TikTok search URL
            $replyText = preg_replace_callback(
                '#https?://(?:www\.)?tiktokshop\.com(?:\.br)?/([a-zA-Z0-9_\-/]+)#i',
                fn($m) => 'https://www.tiktok.com/search?q=' . urlencode(trim(str_replace(['-', '/'], ' ', $m[1]))),
                $replyText
            );
        } else {
            $errDetail = $response['error'] ?? 'Provedores de IA offline ou sem modelos carregados.';
            $replyText = "Saudações, Comandante. Eu sou Jeffrey.\n\nRecebi sua solicitação: \"{$userMessage}\".\n\nO SpirandeliEmpire OS registrou a conversa com sucesso, porém o motor de inferência de IA relatou:\n> _{$errDetail}_\n\n**Para habilitar a geração de respostas completas:**\n1. **Modelo Local no Ollama (Custo R$ 0,00):** Baixe o modelo na VPS rodando:\n   `docker compose exec -it ollama ollama pull qwen2.5:3b`\n2. **Google Gemini (Free Tier 15 RPM):** Defina no arquivo `.env` da VPS:\n   `GEMINI_API_KEY=sua_chave_aqui`\n\nAssim que o modelo for baixado ou a chave for inserida, o SpirandeliEmpire OS responderá automaticamente através do gateway.";
        }

        $toolCallsExecuted = [];
        $toolResults = [];

        // 6. Detect and execute tool calls requested autonomously by the AI
        $extractedCalls = $this->extractToolCalls($replyText);
        $replyText = $this->stripRawToolCalls($replyText);

        if (!empty($extractedCalls)) {
            foreach ($extractedCalls as $call) {
                $toolName = $call['name'];
                $toolArgs = $call['arguments'];

                $toolResult = $this->tools->executeTool($toolName, $toolArgs, $userId, $conversation->id);
                $toolCallsExecuted[] = ['name' => $toolName, 'arguments' => $toolArgs];
                $toolResults[] = ['name' => $toolName, 'result' => $toolResult];

                if ($toolName === 'create_task_pipeline' && !empty($toolResult['pipeline_tasks'])) {
                    $pTasks = $toolResult['pipeline_tasks'];
                    $lines = ["\n\n---\n### ⛓️ Pipeline de Tarefas Encadeadas Iniciado no Worker:"];
                    foreach ($pTasks as $idx => $pt) {
                        $waitInfo = !empty($pt->payload['depends_on_task_id'])
                            ? "⏳ **Aguardando resultado da Tarefa #{$pt->payload['depends_on_task_id']}**"
                            : "⚡ **Em Execução Imediata**";
                        $lines[] = ($idx + 1) . ". **Tarefa [#$pt->id]** ({$pt->agent_name}): _{$pt->title}_ — {$waitInfo}";
                    }
                    $lines[] = "\nAcompanhe em tempo real no **Monitor do Jeffrey** ao lado.";
                    $replyText .= implode("\n", $lines);
                } elseif ($toolName === 'create_task' && isset($toolResult['task']->id)) {
                    $tId = $toolResult['task']->id;
                    $tTitle = $toolResult['task']->title;
                    $depId = $toolResult['depends_on_task_id'] ?? null;
                    $statusNote = $depId
                        ? "⏳ Aguardando conclusão da Tarefa #{$depId} para iniciar automaticamente."
                        : "⚡ O worker em 2º plano já recebeu a missão.";
                    $replyText .= "\n\n---\n⚙️ **Tarefa Real Enfileirada [#$tId]:** _{$tTitle}_\n{$statusNote} Acompanhe no **Monitor do Jeffrey** ao lado.";
                } elseif ($toolName === 'web_search') {
                    $searchResults = $toolResult['results'] ?? [];
                    if (!empty($searchResults)) {
                        $sourcesLines = ["\n\n---\n### 🌐 Fontes e Links Reais Consultados na Internet:"];
                        foreach (array_slice($searchResults, 0, 8) as $i => $sItem) {
                            $n = $i + 1;
                            $snipShort = mb_substr($sItem['snippet'] ?? '', 0, 140);
                            $sourcesLines[] = "{$n}. **[{$sItem['title']}]({$sItem['url']})** — _{$snipShort}_";
                        }
                        $replyText .= implode("\n", $sourcesLines);
                    }
                } else {
                    $replyText .= $this->formatToolResultForHuman($toolName, $toolResult);
                }
            }

            if (trim($replyText) === '' || str_starts_with(trim($replyText), '---')) {
                $replyText = "Ordem processada com sucesso, Comandante. Dados apurados no sistema:\n\n" . ltrim($replyText);
            }
        }

        // Extract structured suggested next actions if present in reply
        $suggestedActions = [];
        if (preg_match('/<suggested_actions>(.*?)<\/suggested_actions>/is', $replyText, $m)) {
            $rawActions = trim($m[1]);
            $lines = explode("\n", $rawActions);
            foreach ($lines as $line) {
                $cleanLine = trim(preg_replace('/^[-*•\d.]+\s*/', '', trim($line)));
                if ($cleanLine !== '' && mb_strlen($cleanLine) < 80) {
                    $suggestedActions[] = $cleanLine;
                }
            }
            $replyText = trim(str_replace($m[0], '', $replyText));
        }

        if (trim($replyText) === '') {
            $replyText = "Ordem recebida e processada, Comandante. Verifique os resultados acima ou no Monitor do Jeffrey ao lado.";
        }

        // 7. Persist Assistant Message
        $tokensPayload = is_array($response['tokens'] ?? null) ? $response['tokens'] : [];
        if (!empty($suggestedActions)) {
            $tokensPayload['suggested_actions'] = $suggestedActions;
        }

        $assistantMsg = Message::create([
            'conversation_id' => $conversation->id,
            'role' => 'assistant',
            'content' => $replyText,
            'provider' => $response['provider'] ?? 'none',
            'model' => $response['model'] ?? 'offline',
            'latency_ms' => $response['latency_ms'] ?? 0,
            'tokens' => !empty($tokensPayload) ? $tokensPayload : null,
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
    public function talk(string $message, ?int $businessId = null, ?string $provider = null, ?int $userId = null): array
    {
        // Auto-create or get latest system conversation
        $conversation = Conversation::firstOrCreate(
            ['title' => 'Linha Direta Jeffrey'],
            ['business_id' => $businessId]
        );

        $assistantMsg = $this->talkInConversation($conversation, $message, $provider, $userId);

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

    /**
     * Remove raw [TOOL_CALL: ...] blocks from the assistant text so only clean prose and formatted results remain.
     */
    protected function stripRawToolCalls(string $text): string
    {
        $cleaned = preg_replace('/\[TOOL_CALL:\s*[a-zA-Z0-9_]+.*?\]\s*$/ms', '', $text);
        $cleaned = preg_replace('/\[TOOL_CALL:\s*[a-zA-Z0-9_]+\s*(?:,\s*\{.*?\}\s*)?\]/s', '', $cleaned ?? $text);
        return trim($cleaned ?? $text);
    }

    /**
     * Detect if the Commander's request requires a 2-stage Chained Task Pipeline:
     * Stage 1 (Research Agent): Research/identify products, videos, trends, or market data.
     * Stage 2 (Copy & Hooks Agent): Wait for Stage 1's output and create hooks, scripts, copy, or action plan.
     */
    protected function detectChainedPipelineStages(string $userMessage): ?array
    {
        $msg = trim($userMessage);
        if (mb_strlen($msg) < 25) {
            return null;
        }

        $hasResearchStage = (bool) preg_match(
            '/\b(pesquis|identifiq|identificar|levant|busqu|buscar|encontr|analis|mapear|mapeie|listar|liste|selecion)\w*.*?\b(produto|vídeo|video|viral|virais|tiktok|nicho|tendência|tendencia|mercado|concorr|oferta|achadinho)/isu',
            $msg
        );

        $hasCreationStage = (bool) preg_match(
            '/\b(crie|criar|planej|gerar|gere|escrev|elabor|faça|fazer|desenvolv|estrutur|produz)\w*.*?\b(gancho|hook|roteiro|script|copy|vídeo|video|campanha|anúncio|anuncio|cta|legenda|título|titulo)/isu',
            $msg
        );

        if (!$hasResearchStage || !$hasCreationStage) {
            return null;
        }

        // Try splitting at the conjunction between Stage 1 and Stage 2 (e.g. "e crie", "e planeje", "e gere", "depois crie")
        $stage1Desc = $msg;
        $stage2Desc = $msg;
        if (preg_match('/^(.*?)\s+(?:e\s+depois\s+|e\s+em\s+seguida\s+|,\s*depois\s+|e\s+)((?:crie|criar|planej|gerar|gere|escrev|elabor|faça|fazer|estrutur)\b.*)$/isu', $msg, $parts)) {
            $stage1Desc = trim($parts[1], " ,.-");
            $stage2Desc = trim($parts[2], " ,.-");
        }

        return [
            [
                'title' => 'Etapa 1/2: ' . mb_substr($stage1Desc, 0, 95),
                'type' => 'research',
                'agent_name' => 'Research Agent',
                'prompt' => "ETAPA 1 DE 2 (PESQUISA E IDENTIFICAÇÃO EM TEMPO REAL):\n"
                    . "Objetivo desta etapa: {$stage1Desc}\n\n"
                    . "Instruções obrigatórias:\n"
                    . "1. Pesquise dados reais na web e identifique os produtos/vídeos solicitados com nomes específicos, preços reais no Brasil (R$), estimativa de comissão, motivo da viralização e links reais verificados.\n"
                    . "2. NÃO invente links fictícios (jamais use tiktokshop.com.br/slug-falso). Use apenas as URLs reais coletadas na busca ou links reais de busca no TikTok (https://www.tiktok.com/search?q=...).\n"
                    . "3. Entregue a lista numerada, estruturada e completa, pois a Etapa 2 (Copy & Hooks Agent) está aguardando este resultado para criar os ganchos de 3 segundos!",
            ],
            [
                'title' => 'Etapa 2/2: ' . mb_substr($stage2Desc, 0, 95),
                'type' => 'content_creation',
                'agent_name' => 'Copy & Hooks Agent',
                'prompt' => "ETAPA 2 DE 2 (PLANEJAMENTO DE HOOKS / COPY BASEADO NA PESQUISA DA ETAPA 1):\n"
                    . "Objetivo desta etapa: {$stage2Desc}\n\n"
                    . "Instruções obrigatórias:\n"
                    . "1. Utilize EXCLUSIVAMENTE a lista de produtos/dados reais entregues pela Etapa 1 (fornecida acima no bloco RESULTADO ENTREGUE PELA TAREFA ANTERIOR).\n"
                    . "2. Para CADA UM dos produtos identificados na Etapa 1, planeje e escreva os ganchos (hooks) de 3 segundos solicitados (ex: Gancho 1: Choque/Dor, Gancho 2: Curiosidade/Segredo, Gancho 3: Prova Social/Oferta) + indicação visual de cena + CTA para o link da vitrine.\n"
                    . "3. Entregue tudo organizado produto por produto, pronto para gravação/edição imediata.",
            ],
        ];
    }

    /**
     * Check if the message is a self-introduction, capability or "how can you help me" query.
     */
    public function isHelpOrCapabilityQuery(string $msg): bool
    {
        $clean = mb_strtolower(trim($msg));
        $clean = preg_replace('/[?!.,;:]+$/u', '', $clean);

        return (bool) preg_match(
            '/^(?:olá|ola|oi|hey|e\s*aí|e\s*ai)?\s*,?\s*(?:como\s+(?:você|vc|o\s+jeffrey|ele)?\s*(?:pode|poderia)\s+me\s+ajudar|como\s+me\s+ajudar|o\s+que\s+(?:você|vc|o\s+jeffrey)\s+(?:faz|pode\s+fazer|sabe\s+fazer)(?:\s+por\s+mim)?|quem\s+é\s+(?:você|vc|o\s+jeffrey)|quais\s+(?:são\s+)?(?:as\s+)?(?:suas\s+)?(?:habilidades|funções|capacidades|ferramentas)|me\s+ajud[ae]|apresente-se|como\s+funciona\s+(?:o\s+)?jeffrey)$/iu',
            $clean
        );
    }

    /**
     * Build an executive, Antigravity-style presentation of Jeffrey and his capabilities.
     */
    public function buildExecutiveSelfIntroduction(): string
    {
        return <<<'MD'
Saudações, Comandante! 🧙‍♂️ Eu sou **Jeffrey**, seu co-piloto executivo, estrategista e orquestrador central do **SpirandeliEmpire OS**.

Minha missão é operar lado a lado com você com a máxima inteligência e clareza: administrando múltiplos negócios digitais, minerando tendências de mercado em tempo real, orquestrando pipelines de agentes autônomos em background e mantendo a infraestrutura da sua VPS 100% otimizada com controle orçamentário rígido.

Aqui está o mapa executivo de como posso impulsionar sua operação:

---

### 1. 🛍️ TikTok Shop & Negócios de Afiliados
- **Mineração de Produtos Virais:** Varredura em tempo real dos produtos que estão viralizando no Brasil, com preços reais em R$, estimativas de comissão e links verificados.
- **Engenharia de Retenção (Hooks de 3s):** Criação de ganchos visuais e verbais de alta retenção (Choque/Curiosidade/Prova Social) e CTAs focados em converter visualizações em vendas na vitrine.
- **Roteiros & Scripts de Alta Conversão:** Estruturação completa para vídeos de 30s a 60s prontos para gravação ou narração neural.

### 2. ⛓️ Orquestração de Agentes Autônomos (Pipelines em 2º Plano)
- **Execução Desacoplada:** Você pode me pedir missões completas (ex: *"Pesquise 10 produtos virais e crie 3 hooks para cada um"*).
- **Processamento Assíncrono:** Divido a solicitação em etapas encadeadas que rodam no worker em segundo plano sem travar o chat ou a interface.
- **Monitoramento em Tempo Real:** Você acompanha o progresso de cada agente (`Research Agent`, `Copy & Hooks Agent`, `Voice Agent`) diretamente no painel ao lado.

### 3. 🌐 Pesquisa Web em Tempo Real & Anti-Alucinação
- **Fontes 100% Reais:** Conecto-me à internet para trazer preços, novidades e referências reais.
- **Filtro Anti-Alucinação:** Proibição absoluta de links inventados ou preposições soltas; apenas links e fontes reais do TikTok e da web.

### 4. 🖥️ Gestão da VPS e Infraestrutura
- **Saúde do Servidor:** Acompanhamento instantâneo de consumo de CPU, memória RAM, armazenamento em disco e latência.
- **Controle dos Containers Docker:** Supervisão de containers ativos (`backend`, `frontend`, `ollama`, `redis`, `worker`).

### 5. 💰 Guardião Financeiro do Império
- **Teto Rígido de R$ 200,00/mês:** Monitoro cada token e requisição consumida.
- **Priorização de Custo Zero:** Uso preferencial do **Google Gemini Free Tier** e modelos locais no **Ollama**, garantindo que sua operação seja extremamente lucrativa e sustentável.

---

Como deseja iniciar hoje, Comandante? Você pode escolher uma das ações rápidas abaixo ou me dar uma ordem direta:
MD;
    }

    /**
     * Sanitize LLM text to ensure that raw JSON dumps are converted to rich Markdown sections.
     */
    public function sanitizeLlmText(string $text): string
    {
        $trimmed = trim($text);

        // If wrapped in ```json ... ```, extract content
        if (preg_match('/^```(?:json)?\s*(\{.*\})\s*```$/s', $trimmed, $m)) {
            $trimmed = trim($m[1]);
        }

        // Check if the whole text is a JSON object
        if (str_starts_with($trimmed, '{') && str_ends_with($trimmed, '}')) {
            $decoded = json_decode($trimmed, true);
            if (is_array($decoded)) {
                // If there is an explicit reply key, return its value
                foreach (['reply', 'response', 'message', 'text', 'content', 'resposta', 'mensagem'] as $key) {
                    if (!empty($decoded[$key]) && is_string($decoded[$key])) {
                        return trim($decoded[$key]);
                    }
                }

                // Otherwise, convert key-value structure to executive Markdown sections
                $lines = ["Comandante, processei os dados requisitados:\n"];
                foreach ($decoded as $key => $val) {
                    $sectionTitle = ucfirst(str_replace(['_', '-'], ' ', (string) $key));
                    $lines[] = "### 📌 {$sectionTitle}";
                    if (is_array($val)) {
                        foreach ($val as $subK => $subV) {
                            if (is_scalar($subV)) {
                                $lines[] = is_numeric($subK) ? "- {$subV}" : "- **{$subK}:** {$subV}";
                            } elseif (is_array($subV)) {
                                $itemSummary = implode(' | ', array_map(fn($k, $v) => is_scalar($v) ? "{$k}: {$v}" : '', array_keys($subV), $subV));
                                $lines[] = "- " . trim($itemSummary, ' |');
                            }
                        }
                    } elseif (is_scalar($val)) {
                        $lines[] = (string) $val;
                    }
                    $lines[] = "";
                }
                return trim(implode("\n", $lines));
            }
        }

        return $text;
    }

    /**
     * Format tool execution outputs as clean, human-readable executive Markdown instead of raw JSON.
     */
    public function formatToolResultForHuman(string $toolName, mixed $result): string
    {
        if (!is_array($result)) {
            return "\n\n> ℹ️ **Resultado [{$toolName}]:** {$result}";
        }

        switch ($toolName) {
            case 'list_businesses':
                $businesses = $result['businesses'] ?? $result;
                if (empty($businesses) || !is_array($businesses)) {
                    return "\n\n---\n### 🏢 Negócios Registrados no Império:\n> Nenhum negócio registrado no momento.";
                }
                $lines = [
                    "\n\n---\n### 🏢 Negócios Registrados no Império:",
                    "| ID | Nome do Negócio | Categoria | Teto Mensal | Status |",
                    "| :--- | :--- | :--- | :--- | :--- |",
                ];
                foreach ($businesses as $b) {
                    $id = $b['id'] ?? '?';
                    $name = $b['name'] ?? 'Sem nome';
                    $cat = $b['category'] ?? 'Geral';
                    $limit = isset($b['budget_limit_brl']) ? 'R$ ' . number_format($b['budget_limit_brl'], 2, ',', '.') : 'N/A';
                    $status = ($b['status'] ?? ($b['is_active'] ?? 'active')) === 'active' ? '🟢 Ativo' : '⚪ ' . ($b['status'] ?? 'Pausado');
                    $lines[] = "| #{$id} | **{$name}** | {$cat} | {$limit} | {$status} |";
                }
                return implode("\n", $lines);

            case 'list_projects':
                $projects = $result['projects'] ?? $result;
                if (empty($projects) || !is_array($projects)) {
                    return "\n\n---\n### 📁 Projetos Mapeados no Sistema:\n> Nenhum projeto mapeado.";
                }
                $lines = ["\n\n---\n### 📁 Projetos Mapeados no Sistema:"];
                foreach ($projects as $p) {
                    $name = $p['name'] ?? 'Projeto';
                    $slug = $p['slug'] ?? '';
                    $path = $p['path'] ?? '';
                    $branch = !empty($p['git_branch']) ? " (`{$p['git_branch']}`)" : '';
                    $lines[] = "- 📂 **{$name}** (`{$slug}`){$branch}" . ($path ? " — Local: `{$path}`" : '');
                }
                return implode("\n", $lines);

            case 'get_system_metrics':
                $m = $result['metrics'] ?? $result;
                $cpu = $m['cpu_usage'] ?? ($m['cpu'] ?? 'N/D');
                $ram = $m['memory_usage'] ?? ($m['memory'] ?? 'N/D');
                $disk = $m['disk_usage'] ?? ($m['disk'] ?? 'N/D');
                $budget = $result['budget'] ?? null;
                $budgetStr = '';
                if ($budget) {
                    $spent = number_format($budget['current_spent_brl'] ?? 0, 2, ',', '.');
                    $lim = number_format($budget['monthly_limit_brl'] ?? 200, 2, ',', '.');
                    $budgetStr = "\n- **Orçamento Mensal:** R$ {$spent} / R$ {$lim} ({$budget['usage_percent']}%)";
                }
                return "\n\n---\n### 🖥️ Telemetria da VPS em Tempo Real:\n"
                    . "- **CPU:** {$cpu}%\n"
                    . "- **Memória RAM:** {$ram}\n"
                    . "- **Armazenamento:** {$disk}"
                    . $budgetStr;

            case 'list_docker_containers':
                $containers = $result['containers'] ?? $result;
                if (empty($containers) || !is_array($containers)) {
                    return "\n\n---\n### 🐳 Containers Docker:\n> Nenhum container reportado.";
                }
                $lines = ["\n\n---\n### 🐳 Containers Docker em Execução:"];
                foreach ($containers as $c) {
                    $name = is_array($c) ? ($c['name'] ?? ($c['Names'] ?? 'container')) : (string) $c;
                    $status = is_array($c) ? ($c['status'] ?? ($c['Status'] ?? 'rodando')) : '';
                    $lines[] = "- 📦 `{$name}`" . ($status ? " ({$status})" : '');
                }
                return implode("\n", $lines);

            case 'inspect_ai_models':
                $models = $result['models'] ?? $result;
                $lines = ["\n\n---\n### 🧠 Modelos de IA Disponíveis:"];
                if (is_array($models)) {
                    foreach ($models as $m) {
                        $mName = is_array($m) ? ($m['name'] ?? json_encode($m)) : (string) $m;
                        $lines[] = "- ⚡ `{$mName}`";
                    }
                }
                return implode("\n", $lines);

            case 'list_tasks':
                $tasks = $result['tasks'] ?? $result;
                if (empty($tasks) || !is_array($tasks)) {
                    return "\n\n---\n### 📋 Fila de Tarefas:\n> Nenhuma tarefa recente.";
                }
                $lines = ["\n\n---\n### 📋 Fila de Tarefas Recentes:"];
                foreach (array_slice($tasks, 0, 5) as $t) {
                    $tId = $t['id'] ?? '?';
                    $tStatus = $t['status'] ?? 'pendente';
                    $tTitle = $t['title'] ?? 'Sem título';
                    $tAgent = $t['agent_name'] ?? 'Agente';
                    $lines[] = "- **#{$tId} [{$tStatus}]** ({$tAgent}): _{$tTitle}_";
                }
                return implode("\n", $lines);

            case 'web_search':
                return ''; // Handled by sources block

            case 'create_business':
                $biz = $result['business'] ?? [];
                $name = $biz['name'] ?? 'Novo Negócio';
                $id = $biz['id'] ?? '?';
                $cat = $biz['category'] ?? 'Geral';
                $lim = isset($biz['budget_limit_brl']) ? 'R$ ' . number_format($biz['budget_limit_brl'], 2, ',', '.') : 'R$ 30,00';
                return "\n\n---\n### 🏢 Novo Negócio Criado e Ativado:\n"
                    . "- **Nome:** **{$name}** (`#{$id}`)\n"
                    . "- **Categoria:** {$cat}\n"
                    . "- **Teto Mensal Alocado:** {$lim}\n"
                    . "- **Status:** 🟢 Ativo no SpirandeliEmpire OS";

            case 'save_memory':
                $content = $result['message'] ?? 'Memória salva com sucesso.';
                return "\n\n---\n> 🧠 **Memória Operacional Persistida:** {$content}";

            case 'trigger_video_generation':
                $taskId = $result['task_id'] ?? '?';
                $msg = $result['message'] ?? 'Pipeline de vídeo enfileirado.';
                return "\n\n---\n### 🎬 Pipeline de Vídeo Disparado [Tarefa #{$taskId}]:\n"
                    . "{$msg}\n"
                    . "> Acompanhe no **Monitor do Jeffrey** ao lado: roteiro com Gemini 3.8 Flash + narração neural + renderização vertical.";

            case 'manage_docker_service':
                $service = $result['service'] ?? 'serviço';
                $msg = $result['message'] ?? ($result['status_output'] ?? 'Ação executada.');
                return "\n\n---\n> 🐳 **Infraestrutura Docker ({$service}):** {$msg}";

            default:
                $summary = [];
                foreach ($result as $k => $v) {
                    if (is_scalar($v) && !str_contains($k, '_token') && !str_contains($k, 'password')) {
                        $label = ucfirst(str_replace('_', ' ', (string) $k));
                        $summary[] = "- **{$label}:** {$v}";
                    }
                }
                if (!empty($summary)) {
                    return "\n\n---\n### ⚙️ Execução da Ferramenta [{$toolName}]:\n" . implode("\n", array_slice($summary, 0, 8));
                }
                return "\n\n> ⚙️ **Ferramenta [{$toolName}] executada com sucesso pelo sistema.**";
        }
    }
}
