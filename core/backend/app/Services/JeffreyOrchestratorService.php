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
Você é Jeffrey, o agente executivo central do SpirandeliEmpire OS.
PERFIL DO COMANDANTE: {$userProfileSummary}
Orçamento: R$ {$budgetStatus['current_spent_brl']}/R$ {$budgetStatus['monthly_limit_brl']}. {$projectContext} | {$businessContext}
Tarefas reais no sistema: {$tasksContext}
FERRAMENTAS: list_projects, inspect_project, read_project_file, list_businesses, get_business_status, update_business_automation, manage_business_accounts, run_business_automation, get_system_metrics, list_docker_containers, inspect_ai_models, create_task, list_tasks, web_search.
REGRAS ANTI-ALUCINAÇÃO:
1. JAMAIS invente links falsos como 'https://www.tiktokshop.com.br/...' (esse formato de link não existe!). Use EXCLUSIVAMENTE as URLs reais presentes em <live_web_research_results> ou links reais de busca https://www.tiktok.com/search?q=Termo.
2. Baseie produtos, preços e tendências nos resultados reais de <live_web_research_results>.
3. Se precisar delegar tarefa em 2º plano, adicione no final:
[TOOL_CALL: create_task, {"title": "Resumo da tarefa", "type": "research", "agent_name": "Research Agent"}]
Responda em português brasileiro de forma executiva, objetiva e direta.
PROMPT;
        } else {
            $systemPrompt = <<<PROMPT
Você é Jeffrey, o agente executivo central e arquiteto de software do SpirandeliEmpire OS.
Sua missão: Administrar o império de forma automatizada, gerir cada negócio usando suas contas vinculadas e parâmetros operacionais, planejar novos negócios digitais, analisar código de projetos existentes, gerenciar tarefas e coordenar a VPS.

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
2. PROIBIDO INVENTAR LINKS FALSOS OU DADOS FICTÍCIOS: Jamais invente URLs como 'https://www.tiktokshop.com.br/nome-produto' (esse domínio/formato não existe). Utilize EXCLUSIVAMENTE as URLs reais fornecidas em <live_web_research_results> ou links reais de busca no formato https://www.tiktok.com/search?q=Nome+do+Produto.
3. Baseie toda recomendação de produtos, preços e tendências nos dados reais coletados em <live_web_research_results>.
4. Jamais invente versículos ou dados históricos falsos para o RISADA.exe.
5. Você gerencia diretamente os negócios (especialmente TikTok Shop Afiliados) usando suas contas vinculadas (@handle, ID de afiliado, link da vitrine) e parâmetros de automação.
6. ORQUESTRAÇÃO EM CADEIA (PIPELINE DE TAREFAS): Quando o Comandante pedir uma missão em 2 etapas (ex: "Pesquise/identifique X produtos/vídeos E crie/planeje Y ganchos/hooks/roteiros"), explique o plano de execução e dispare a ferramenta `create_task_pipeline` com 2 etapas encadeadas:
   - Etapa 1 (`Research Agent`): Pesquisa e identificação completa dos produtos/vídeos/dados reais.
   - Etapa 2 (`Copy & Hooks Agent`): Aguarda automaticamente o resultado da Etapa 1 (`depends_on_task_id`) para planejar os hooks de 3 segundos / roteiros sobre os itens reais encontrados na Etapa 1.
   Sintaxe:
   [TOOL_CALL: create_task_pipeline, {"steps": [{"title": "Etapa 1/2: Pesquisar...", "type": "research", "agent_name": "Research Agent", "prompt": "..."}, {"title": "Etapa 2/2: Planejar hooks...", "type": "content_creation", "agent_name": "Copy & Hooks Agent", "prompt": "..."}]}]
7. Jamais responda apenas com uma tag `[TOOL_CALL: ...]` vazia sem texto executivo para o Comandante.
</anti_hallucination_rules>

<tools_catalog>
{$toolsManifest}
</tools_catalog>

<response_guidelines>
1. Responda em português brasileiro com postura executiva de alto nível, assertiva, técnica e proativa.
2. Use formatação Markdown rica: use títulos (###), tabelas comparativas quando houver produtos/preços, negritos estratégicos e blocos de código com linguagem indicada.
3. Se disparar ferramentas ou pipelines em segundo plano, explique claramente o objetivo antes.
4. Ao final da resposta, inclua sempre 2 a 3 sugestões de ações práticas imediatas para o Comandante avançar com um clique, no seguinte formato estrito:
<suggested_actions>
- Sugestão de Ação 1
- Sugestão de Ação 2
- Sugestão de Ação 3
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

        $fullPrompt = $conversationHistory . "Comandante: " . $userMessage;

        // Check upfront if this is a 2-stage chained pipeline mission (e.g. "Pesquise 10 produtos... e crie 3 hooks...")
        $pipelineAllowed = ($enabledCaps['cooperative_pipeline'] ?? true) !== false;
        $pipelineStages = $pipelineAllowed ? $this->detectChainedPipelineStages($userMessage) : null;

        // Fast-path orchestration for 2-stage chained task pipelines:
        // Immediately create and enqueue Task #1 (Research) and Task #2 (Hooks/Copy waiting on Task #1)
        // so the Commander gets an instant (< 500ms) confirmation and the background worker executes both stages!
        if ($pipelineStages !== null && empty($attachments)) {
            $pipeResult = $this->tools->executeTool('create_task_pipeline', [
                'business_id' => $businessId,
                'steps' => $pipelineStages,
            ], $userId, $conversation->id);

            $toolCallsExecuted = [['name' => 'create_task_pipeline', 'arguments' => ['business_id' => $businessId, 'steps' => $pipelineStages]]];
            $toolResults = [['name' => 'create_task_pipeline', 'result' => $pipeResult]];

            $pTasks = $pipeResult['pipeline_tasks'] ?? [];
            $t1 = $pTasks[0] ?? null;
            $t2 = $pTasks[1] ?? null;

            $replyText = "Comandante, estruturei sua solicitação em um **Pipeline de Execução Encadeada em 2 Etapas** no worker em 2º plano:\n\n"
                . "1. **Etapa 1 — Pesquisa & Filtragem (`Research Agent`):** Pesquisa em tempo real na internet dos produtos/vídeos solicitados (com preços reais em R\$, estimativa de comissão e links verificados).\n"
                . "2. **Etapa 2 — Planejamento de Hooks de 3s (`Copy & Hooks Agent`):** Fica aguardando o relatório final da Etapa 1 e, assim que concluída, recebe automaticamente os produtos encontrados para criar os ganchos (hooks) de 3 segundos para cada um.\n\n"
                . "---\n### ⛓️ Pipeline de Tarefas Encadeadas Enfileirado:\n"
                . ($t1 ? "- ⚡ **Tarefa [#$t1->id] (`{$t1->agent_name}` — EM EXECUÇÃO):** _{$t1->title}_\n" : '')
                . ($t2 ? "- ⏳ **Tarefa [#$t2->id] (`{$t2->agent_name}` — AGUARDANDO TAREFA #" . ($t1->id ?? '1') . "):** _{$t2->title}_\n" : '')
                . "\n> Acompanhe no **Monitor do Jeffrey (Ao Vivo)** ao lado: assim que a **Tarefa #" . ($t1->id ?? '1') . "** entregar a pesquisa aqui no chat, a **Tarefa #" . ($t2->id ?? '2') . "** iniciará automaticamente!";

            $assistantMsg = Message::create([
                'conversation_id' => $conversation->id,
                'role' => 'assistant',
                'content' => $replyText,
                'provider' => 'jeffrey_orchestrator',
                'model' => 'pipeline-v3',
                'latency_ms' => 120,
                'tool_calls' => $toolCallsExecuted,
                'tool_results' => $toolResults,
                'fallback_used' => false,
            ]);

            $this->auditDecision(
                'Jeffrey',
                $businessId,
                'task_pipeline_dispatched',
                'Pipeline encadeado de 2 tarefas criado na conversa #' . $conversation->id,
                [
                    'conversation_id' => $conversation->id,
                    'task_1_id' => $t1->id ?? null,
                    'task_2_id' => $t2->id ?? null,
                ]
            );

            return $assistantMsg;
        }

        // 4.5 Automatic Real-Time Web Search before AI generation when message asks for products, TikTok Shop, trends, prices, or web research
        $liveWebResults = [];
        $webSearchAllowed = ($enabledCaps['live_web_search'] ?? true) !== false;
        if ($webSearchAllowed && preg_match('/(pesquis|internet|web|tiktok|produto|viral|virais|tendência|tendencia|mercado|concorr|amazon|kdp|shopee|top\s*\d+|identific|levantamento|preço|preco|notícia|noticia|atual|hoje|2025|2026|vendido|afiliado)/iu', $userMessage)) {
            $liveWebResults = $this->tools->performWebSearch($userMessage);
            if (!empty($liveWebResults)) {
                $webBlockLines = ["<live_web_research_results>"];
                foreach ($liveWebResults as $idx => $item) {
                    $num = $idx + 1;
                    $webBlockLines[] = "  {$num}. {$item['title']} — {$item['snippet']} (URL Real Verificada: {$item['url']})";
                }
                $webBlockLines[] = "</live_web_research_results>";
                $webBlockText = implode("\n", $webBlockLines);
                $fullPrompt .= "\n\n[DADOS REAIS PESQUISADOS NA INTERNET AGORA PELO SISTEMA — USE ESTES DADOS E LINKS REAIS, NÃO INVENTE URLs]:\n" . $webBlockText;
            }
        }

        // Enrich prompt with any attached text/code/CSV/MD files and collect multimodal inline_data (images, voice audio, PDFs)
        $inlineMedia = [];
        $attachedTextsForLlama = [];
        if (!empty($liveWebResults)) {
            $attachedTextsForLlama[] = "=== PESQUISA WEB EM TEMPO REAL ===\n" . ($webBlockText ?? '');
        }
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

        // 5. Query AI Gateway with Role Division (Llama = Read/Analyze, Gemini/OpenAI = Execute Tasks) & User Login Restriction
        $taskRole = $this->aiGateway->getTokenManager()->classifyTaskRole($userMessage);
        if (!empty($inlineMedia)) {
            // Multimodal (Voice message, Image screenshot, or PDF) -> Gemini 3.8 Flash (if authorized for user)
            $response = $this->aiGateway->generate($fullPrompt, $systemPrompt, $provider, null, 'execute_task', $inlineMedia, $user, $conversationTurns);
        } elseif ($cloudConfigured && !$forceLocal && (!empty($attachedTextsForLlama) || preg_match('/\b(analis|leia|ler|inspecion|resum).*?(e\s+depois|e\s+execut|e\s+crie|e\s+gere|e\s+rode)/iu', $userMessage))) {
            $rawContextForLlama = !empty($attachedTextsForLlama)
                ? implode("\n\n", $attachedTextsForLlama)
                : "{$projectContext}\n{$businessContext}\nTarefas: {$tasksContext}\nMemórias:\n{$formattedMemories}";
            $response = $this->aiGateway->analyzeWithLlamaThenExecute($rawContextForLlama, $fullPrompt, $systemPrompt, $provider, $user);
        } else {
            $response = $this->aiGateway->generate($fullPrompt, $systemPrompt, $provider, null, $taskRole, [], $user, $conversationTurns);
        }

        if ($response['success']) {
            $replyText = $response['response'];
            // Anti-hallucination URL sanitizer: replace any invented tiktokshop.com.br/slug link with a real TikTok search URL
            $replyText = preg_replace_callback(
                '#https?://(?:www\.)?tiktokshop\.com(?:\.br)?/([a-zA-Z0-9_\-/]+)#i',
                fn($m) => 'https://www.tiktok.com/search?q=' . urlencode(trim(str_replace(['-', '/'], ' ', $m[1]))),
                $replyText
            );
            if (!empty($liveWebResults) && !str_contains($replyText, 'Fontes e Links Reais')) {
                $sourcesLines = ["\n\n---\n### 🌐 Fontes e Links Reais Consultados na Internet:"];
                foreach (array_slice($liveWebResults, 0, 8) as $i => $sItem) {
                    $n = $i + 1;
                    $snipShort = mb_substr($sItem['snippet'] ?? '', 0, 140);
                    $sourcesLines[] = "{$n}. **[{$sItem['title']}]({$sItem['url']})** — _{$snipShort}_";
                }
                $replyText .= implode("\n", $sourcesLines);
            }
        } else {
            $errDetail = $response['error'] ?? 'Provedores de IA offline ou sem modelos carregados.';
            $replyText = "Saudações, Comandante. Eu sou Jeffrey.\n\nRecebi sua solicitação: \"{$userMessage}\".\n\nO SpirandeliEmpire OS registrou a conversa com sucesso, porém o motor de inferência de IA relatou:\n> _{$errDetail}_\n\n**Para habilitar a geração de respostas completas:**\n1. **Modelo Local no Ollama (Custo R$ 0,00):** Baixe o modelo na VPS rodando:\n   `docker compose exec -it ollama ollama pull qwen2.5:3b`\n2. **Google Gemini (Free Tier 15 RPM):** Defina no arquivo `.env` da VPS:\n   `GEMINI_API_KEY=sua_chave_aqui`\n\nAssim que o modelo for baixado ou a chave for inserida, o SpirandeliEmpire OS responderá automaticamente através do gateway.";
        }

        $toolCallsExecuted = [];
        $toolResults = [];
        $createdTasksCount = 0;

        // 6. Detect and execute tool calls (supports nested JSON objects and multiple calls)
        $extractedCalls = $this->extractToolCalls($replyText);
        // Strip raw [TOOL_CALL: ...] syntax so the user never sees raw tags in chat
        $replyText = $this->stripRawToolCalls($replyText);

        if (!empty($extractedCalls)) {
            foreach ($extractedCalls as $call) {
                $toolName = $call['name'];
                $toolArgs = $call['arguments'];

                // Skip redundant raw web_search dump if pre-search already ran or if we are launching a chained pipeline
                if ($toolName === 'web_search' && (!empty($liveWebResults) || $this->detectChainedPipelineStages($userMessage) !== null)) {
                    continue;
                }

                $toolResult = $this->tools->executeTool($toolName, $toolArgs, $userId, $conversation->id);
                $toolCallsExecuted[] = ['name' => $toolName, 'arguments' => $toolArgs];
                $toolResults[] = ['name' => $toolName, 'result' => $toolResult];

                if ($toolName === 'create_task_pipeline' && !empty($toolResult['pipeline_tasks'])) {
                    $pTasks = $toolResult['pipeline_tasks'];
                    $createdTasksCount += count($pTasks);
                    $lines = ["\n\n---\n### ⛓️ Pipeline de Tarefas Encadeadas Iniciado no Worker:"];
                    foreach ($pTasks as $idx => $pt) {
                        $waitInfo = !empty($pt->payload['depends_on_task_id'])
                            ? "⏳ **Aguardando resultado da Tarefa #{$pt->payload['depends_on_task_id']}**"
                            : "⚡ **Em Execução Imediata**";
                        $lines[] = ($idx + 1) . ". **Tarefa [#$pt->id]** ({$pt->agent_name}): _{$pt->title}_ — {$waitInfo}";
                    }
                    $lines[] = "\nAcompanhe em tempo real no **Monitor do Jeffrey** ao lado. Assim que a 1ª tarefa concluir a pesquisa, a 2ª iniciará automaticamente usando os produtos/dados encontrados!";
                    $replyText .= implode("\n", $lines);
                } elseif ($toolName === 'create_task' && isset($toolResult['task']->id)) {
                    $createdTasksCount++;
                    $tId = $toolResult['task']->id;
                    $tTitle = $toolResult['task']->title;
                    $depId = $toolResult['depends_on_task_id'] ?? null;
                    $statusNote = $depId
                        ? "⏳ Aguardando conclusão da Tarefa #{$depId} para iniciar automaticamente."
                        : "⚡ O worker em 2º plano já recebeu a missão.";
                    $replyText .= "\n\n---\n⚙️ **Tarefa Real Enfileirada [#$tId]:** _{$tTitle}_\n{$statusNote} Acompanhe no **Monitor do Jeffrey** ao lado.";
                } else {
                    $formattedResult = json_encode($toolResult, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
                    $replyText .= "\n\n---\n**Execução de Ferramenta Real [{$toolName}]:**\n```json\n{$formattedResult}\n```";
                }
            }
        }

        // 6.5 Deterministic Multi-Stage Pipeline Orchestration:
        // Whenever the Commander requests a 2-step mission (e.g. "Pesquise/identifique 10 produtos virais... e crie 3 hooks de 3s para cada um")
        // and the LLM did not already create >= 2 chained tasks, automatically create the chained pipeline!
        $pipelineStages = $this->detectChainedPipelineStages($userMessage);
        if ($pipelineStages !== null && $createdTasksCount < 2) {
            $pipeResult = $this->tools->executeTool('create_task_pipeline', [
                'business_id' => $businessId,
                'steps' => $pipelineStages,
            ], $userId, $conversation->id);

            $toolCallsExecuted[] = ['name' => 'create_task_pipeline', 'arguments' => ['business_id' => $businessId, 'steps' => $pipelineStages]];
            $toolResults[] = ['name' => 'create_task_pipeline', 'result' => $pipeResult];

            if (!empty($pipeResult['pipeline_tasks'])) {
                $pTasks = $pipeResult['pipeline_tasks'];
                $t1 = $pTasks[0] ?? null;
                $t2 = $pTasks[1] ?? null;

                if (mb_strlen(trim($replyText)) < 40) {
                    $replyText = "Comandante, estruturei sua solicitação em um **Pipeline de Execução Encadeada em 2 Etapas** para garantir que os ganchos (hooks) sejam criados somente sobre produtos reais já validados pela pesquisa:\n\n"
                        . "1. **Etapa 1 — Pesquisa & Filtragem (`Research Agent`):** Identificação em tempo real dos produtos viralizados na TikTok Shop Brasil (com preços, comissões estimadas >= 15% e links reais).\n"
                        . "2. **Etapa 2 — Planejamento de Hooks de 3s (`Copy & Hooks Agent`):** Fica em espera aguardando o relatório final da Etapa 1 e, assim que concluída, recebe automaticamente a lista dos produtos para criar os 3 ganchos (hooks) de 3 segundos de alta retenção para cada produto.";
                }

                $lines = ["\n\n---\n### ⛓️ Pipeline de Tarefas Encadeadas Enfileirado:"];
                if ($t1) {
                    $lines[] = "- ⚡ **Tarefa [#$t1->id] (`{$t1->agent_name}` — EM EXECUÇÃO):** _{$t1->title}_";
                }
                if ($t2) {
                    $dep = $t1 ? $t1->id : '?';
                    $lines[] = "- ⏳ **Tarefa [#$t2->id] (`{$t2->agent_name}` — AGUARDANDO TAREFA #{$dep}):** _{$t2->title}_";
                }
                $lines[] = "\n> Acompanhe no **Monitor do Jeffrey (Ao Vivo)** ao lado: assim que a **Tarefa #" . ($t1->id ?? '1') . "** entregar a pesquisa dos produtos, a **Tarefa #" . ($t2->id ?? '2') . "** será disparada automaticamente com os resultados!";
                $replyText .= implode("\n", $lines);
            }
        } elseif (
            $createdTasksCount === 0 &&
            preg_match('/(estou\s+(fazendo a pesquisa|pesquisando|encaminhando|trabalhando|analisando|coletando|buscando|iniciando)|vou\s+(pesquisar|encaminhar|iniciar|coletar|preparar))/iu', $replyText)
        ) {
            // Auto-enqueue a single background task if the model promised background work without emitting [TOOL_CALL]
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
}
