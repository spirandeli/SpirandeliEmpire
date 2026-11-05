<?php

namespace App\Services;

use App\Http\Controllers\Api\BusinessController;
use App\Models\ApprovalRequest;
use App\Models\Business;
use App\Models\JeffreyMemory;
use App\Models\Project;
use App\Models\Task;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Redis;
use Illuminate\Support\Facades\Schema;

class ToolRegistryService
{
    protected VpsMonitorService $vps;
    protected OllamaClientService $ollama;
    protected BudgetGuardService $budget;

    public function __construct(VpsMonitorService $vps, OllamaClientService $ollama, BudgetGuardService $budget)
    {
        $this->vps = $vps;
        $this->ollama = $ollama;
        $this->budget = $budget;
    }

    /**
     * Get definitions of all tools available to Jeffrey and specialized agents.
     */
    public function getAvailableTools(): array
    {
        return [
            [
                'name' => 'list_projects',
                'description' => 'Lista todos os projetos e workspaces cadastrados no SpirandeliEmpire OS com seus respectivos caminhos e status.',
                'parameters' => [],
                'category' => 'A', // Safe
            ],
            [
                'name' => 'inspect_project',
                'description' => 'Inspeciona a estrutura de pastas e arquivos de um projeto autorizado.',
                'parameters' => [
                    'project_id' => ['type' => 'integer', 'required' => true, 'description' => 'ID do projeto'],
                    'subpath' => ['type' => 'string', 'required' => false, 'description' => 'Subpasta opcional dentro do projeto'],
                ],
                'category' => 'A',
            ],
            [
                'name' => 'read_project_file',
                'description' => 'Lê o conteúdo de um arquivo de código ou texto dentro de um projeto autorizado (com proteção contra traversal e leitura de segredos).',
                'parameters' => [
                    'project_id' => ['type' => 'integer', 'required' => true, 'description' => 'ID do projeto'],
                    'relative_path' => ['type' => 'string', 'required' => true, 'description' => 'Caminho relativo do arquivo'],
                ],
                'category' => 'A',
            ],
            [
                'name' => 'search_project_files',
                'description' => 'Pesquisa por termos ou padrões de texto nos arquivos de um projeto.',
                'parameters' => [
                    'project_id' => ['type' => 'integer', 'required' => true, 'description' => 'ID do projeto'],
                    'query' => ['type' => 'string', 'required' => true, 'description' => 'Termo de busca'],
                ],
                'category' => 'A',
            ],
            [
                'name' => 'create_project_file',
                'description' => 'Cria um novo arquivo em um projeto autorizado.',
                'parameters' => [
                    'project_id' => ['type' => 'integer', 'required' => true, 'description' => 'ID do projeto'],
                    'relative_path' => ['type' => 'string', 'required' => true, 'description' => 'Caminho relativo do arquivo a ser criado'],
                    'content' => ['type' => 'string', 'required' => true, 'description' => 'Conteúdo do arquivo'],
                ],
                'category' => 'B', // Controlled
            ],
            [
                'name' => 'edit_project_file',
                'description' => 'Edita um arquivo existente em um projeto autorizado substituindo um trecho de código específico.',
                'parameters' => [
                    'project_id' => ['type' => 'integer', 'required' => true, 'description' => 'ID do projeto'],
                    'relative_path' => ['type' => 'string', 'required' => true, 'description' => 'Caminho relativo do arquivo'],
                    'target_text' => ['type' => 'string', 'required' => true, 'description' => 'Texto exato a ser substituído'],
                    'replacement_text' => ['type' => 'string', 'required' => true, 'description' => 'Novo texto de substituição'],
                ],
                'category' => 'B',
            ],
            [
                'name' => 'get_project_git_status',
                'description' => 'Obtém o status do repositório Git (arquivos alterados, branch e commits não enviados).',
                'parameters' => [
                    'project_id' => ['type' => 'integer', 'required' => true, 'description' => 'ID do projeto'],
                ],
                'category' => 'A',
            ],
            [
                'name' => 'list_businesses',
                'description' => 'Lista todos os negócios digitais cadastrados (incluindo TikTok Shop Afiliados), suas contas vinculadas, parâmetros de automação e tetos orçamentários.',
                'parameters' => [],
                'category' => 'A',
            ],
            [
                'name' => 'get_business_status',
                'description' => 'Obtém métricas detalhadas, contas vinculadas, parâmetros do agente e tarefas recentes de um negócio digital específico.',
                'parameters' => [
                    'business_id' => ['type' => 'integer', 'required' => true, 'description' => 'ID do negócio'],
                ],
                'category' => 'A',
            ],
            [
                'name' => 'update_business_automation',
                'description' => 'Atualiza os parâmetros de automação do agente para um negócio (nicho, público-alvo, meta diária, comissão mínima, tom de voz, CTA, frequência e regras customizadas).',
                'parameters' => [
                    'business_id' => ['type' => 'integer', 'required' => true, 'description' => 'ID do negócio'],
                    'automation_params' => ['type' => 'object', 'required' => true, 'description' => 'Parâmetros de automação (niche, target_audience, daily_deliverables_goal, min_commission_percent, cta_template, custom_prompt_rules, auto_enabled, frequency)'],
                    'budget_limit_brl' => ['type' => 'number', 'required' => false, 'description' => 'Teto mensal em BRL'],
                ],
                'category' => 'B',
            ],
            [
                'name' => 'manage_business_accounts',
                'description' => 'Adiciona ou atualiza uma conta vinculada a um negócio (ex: conta TikTok Shop, YouTube Shorts, Instagram Reels, ID de afiliado, @handle e link da vitrine).',
                'parameters' => [
                    'business_id' => ['type' => 'integer', 'required' => true, 'description' => 'ID do negócio'],
                    'platform' => ['type' => 'string', 'required' => true, 'description' => 'Plataforma (ex: TikTok Shop, YouTube Shorts, Instagram Reels)'],
                    'handle' => ['type' => 'string', 'required' => true, 'description' => '@handle ou nome do perfil'],
                    'account_id' => ['type' => 'string', 'required' => false, 'description' => 'ID de Afiliado / Seller ID'],
                    'affiliate_showcase_url' => ['type' => 'string', 'required' => false, 'description' => 'Link da vitrine ou canal'],
                    'email_or_login' => ['type' => 'string', 'required' => false, 'description' => 'E-mail ou login da conta'],
                    'notes' => ['type' => 'string', 'required' => false, 'description' => 'Observações operacionais para o agente'],
                ],
                'category' => 'B',
            ],
            [
                'name' => 'run_business_automation',
                'description' => 'Dispara imediatamente um ciclo automatizado do agente para gerir um negócio usando suas contas vinculadas e parâmetros configurados.',
                'parameters' => [
                    'business_id' => ['type' => 'integer', 'required' => true, 'description' => 'ID do negócio'],
                    'custom_objective' => ['type' => 'string', 'required' => false, 'description' => 'Objetivo específico opcional para este ciclo'],
                ],
                'category' => 'B',
            ],
            [
                'name' => 'get_system_metrics',
                'description' => 'Obtém a telemetria em tempo real da VPS (uso de CPU, Memória RAM, Armazenamento e Uptime).',
                'parameters' => [],
                'category' => 'A',
            ],
            [
                'name' => 'list_docker_containers',
                'description' => 'Lista os containers Docker em execução e seu estado de saúde na infraestrutura do império.',
                'parameters' => [],
                'category' => 'A',
            ],
            [
                'name' => 'inspect_ai_models',
                'description' => 'Inspeciona os modelos de IA disponíveis no Ollama local e verifica conectividade com provedores.',
                'parameters' => [],
                'category' => 'A',
            ],
            [
                'name' => 'create_task',
                'description' => 'Cria uma nova tarefa assíncrona para execução por agentes especializados (suporta encadeamento via depends_on_task_id).',
                'parameters' => [
                    'title' => ['type' => 'string', 'required' => true, 'description' => 'Título da tarefa'],
                    'type' => ['type' => 'string', 'required' => true, 'description' => 'Tipo da tarefa (research, content_creation, business_automation)'],
                    'agent_name' => ['type' => 'string', 'required' => false, 'description' => 'Nome do agente responsável (ex: Research Agent, Copy & Hooks Agent)'],
                    'business_id' => ['type' => 'integer', 'required' => false, 'description' => 'ID do negócio associado'],
                    'depends_on_task_id' => ['type' => 'integer', 'required' => false, 'description' => 'ID de outra tarefa que deve terminar antes desta iniciar'],
                    'payload' => ['type' => 'object', 'required' => false, 'description' => 'Parâmetros da tarefa'],
                ],
                'category' => 'B',
            ],
            [
                'name' => 'create_task_pipeline',
                'description' => 'Cria um pipeline encadeado de 2 ou mais tarefas onde a segunda tarefa aguarda automaticamente o resultado completo da primeira tarefa terminar (ex: Task 1 pesquisa 10 produtos virais -> Task 2 aguarda a Task 1 e cria os hooks de 3 segundos para cada produto).',
                'parameters' => [
                    'business_id' => ['type' => 'integer', 'required' => false, 'description' => 'ID do negócio associado'],
                    'steps' => ['type' => 'array', 'required' => true, 'description' => 'Lista ordenada de etapas [{title, type, agent_name, prompt}]'],
                ],
                'category' => 'B',
            ],
            [
                'name' => 'get_task_status',
                'description' => 'Consulta o progresso e resultado de uma tarefa específica.',
                'parameters' => [
                    'task_id' => ['type' => 'integer', 'required' => true, 'description' => 'ID da tarefa'],
                ],
                'category' => 'A',
            ],
            [
                'name' => 'list_tasks',
                'description' => 'Lista as tarefas recentes e em andamento do Jeffrey e agentes especializados.',
                'parameters' => [],
                'category' => 'A',
            ],
            [
                'name' => 'web_search',
                'description' => 'Pesquisa na internet em tempo real quando você necessitar de dados atualizados do mercado, tendências, preços reais ou produtos virais (ex: TikTok Shop Brasil). Use queries objetivas.',
                'parameters' => [
                    'query' => ['type' => 'string', 'required' => true, 'description' => 'Termo de busca na web'],
                ],
                'category' => 'A',
            ],
            [
                'name' => 'create_business',
                'description' => 'Cadastra um novo negócio digital no império (ex: canais dark, programas de afiliados, infoprodutos), configurando metas e contas vinculadas.',
                'parameters' => [
                    'name' => ['type' => 'string', 'required' => true, 'description' => 'Nome do negócio'],
                    'category' => ['type' => 'string', 'required' => true, 'description' => 'Categoria (ex: Affiliate Marketing, YouTube Dark Channel, E-commerce)'],
                    'description' => ['type' => 'string', 'required' => false, 'description' => 'Descrição do modelo de negócio'],
                    'budget_limit_brl' => ['type' => 'number', 'required' => false, 'description' => 'Teto orçamentário mensal em BRL (padrão: 30.00)'],
                    'automation_params' => ['type' => 'object', 'required' => false, 'description' => 'Parâmetros (niche, target_audience, daily_deliverables_goal, min_commission_percent, cta_template)'],
                    'accounts' => ['type' => 'array', 'required' => false, 'description' => 'Contas vinculadas [{platform, handle, account_id, affiliate_showcase_url}]'],
                ],
                'category' => 'B',
            ],
            [
                'name' => 'save_memory',
                'description' => 'Registra uma memória operacional persistente no sistema (regras estratégicas, preferências do Comandante ou diretrizes operacionais).',
                'parameters' => [
                    'content' => ['type' => 'string', 'required' => true, 'description' => 'Fato, preferência ou diretriz a ser memorizada'],
                    'category' => ['type' => 'string', 'required' => false, 'description' => 'Categoria (preferencia, regra_negocio, estrategia, aprendizado)'],
                    'business_id' => ['type' => 'integer', 'required' => false, 'description' => 'ID opcional do negócio associado'],
                ],
                'category' => 'A',
            ],
            [
                'name' => 'trigger_video_generation',
                'description' => 'Dispara a geração completa de vídeo (roteiro persuasivo via Gemini 3.8 Flash, síntese de voz neural e renderização de vídeo vertical 9:16 anti-ban).',
                'parameters' => [
                    'product_name' => ['type' => 'string', 'required' => true, 'description' => 'Nome do produto ou tema do vídeo'],
                    'product_price' => ['type' => 'string', 'required' => false, 'description' => 'Preço ou oferta (ex: R$ 49,90)'],
                    'category' => ['type' => 'string', 'required' => false, 'description' => 'Nicho/categoria do produto'],
                    'business_id' => ['type' => 'integer', 'required' => false, 'description' => 'ID do negócio associado'],
                ],
                'category' => 'B',
            ],
            [
                'name' => 'manage_docker_service',
                'description' => 'Gerencia ou reinicia um container da infraestrutura (ex: reiniciar o worker de tarefas ou o serviço ollama).',
                'parameters' => [
                    'action' => ['type' => 'string', 'required' => true, 'description' => 'Ação a executar (restart, status)'],
                    'service' => ['type' => 'string', 'required' => true, 'description' => 'Nome do serviço (worker, backend, frontend, redis, ollama)'],
                ],
                'category' => 'B',
            ],
        ];
    }

    /**
     * Execute a tool safely with permissions validation.
     */
    public function executeTool(string $toolName, array $arguments, ?int $userId = null, ?int $conversationId = null): array
    {
        Log::info("Tool execution requested: [{$toolName}]", ['args' => $arguments]);

        switch ($toolName) {
            case 'list_projects':
                return [
                    'success' => true,
                    'projects' => Project::all(['id', 'name', 'slug', 'description', 'path', 'status', 'git_branch'])->toArray(),
                ];

            case 'inspect_project':
                $project = Project::find($arguments['project_id'] ?? 0);
                if (!$project) return ['success' => false, 'error' => 'Projeto não encontrado.'];

                $targetPath = $this->resolveSafeProjectPath($project->path, $arguments['subpath'] ?? '');
                if (!$targetPath || !File::exists($targetPath)) {
                    return ['success' => false, 'error' => 'Caminho inacessível ou fora do workspace autorizado.'];
                }

                $files = [];
                $directories = [];
                foreach (File::directories($targetPath) as $dir) {
                    $base = basename($dir);
                    if ($base !== 'node_modules' && $base !== 'vendor' && $base !== '.git') {
                        $directories[] = $base;
                    }
                }
                foreach (File::files($targetPath) as $file) {
                    $base = basename($file);
                    if (!str_starts_with($base, '.env')) {
                        $files[] = [
                            'name' => $base,
                            'size' => File::size($file),
                            'last_modified' => date('Y-m-d H:i:s', File::lastModified($file)),
                        ];
                    }
                }

                return [
                    'success' => true,
                    'project' => $project->name,
                    'current_path' => $targetPath,
                    'directories' => $directories,
                    'files' => $files,
                ];

            case 'read_project_file':
                $project = Project::find($arguments['project_id'] ?? 0);
                if (!$project) return ['success' => false, 'error' => 'Projeto não encontrado.'];

                $filePath = $this->resolveSafeProjectPath($project->path, $arguments['relative_path'] ?? '');
                if (!$filePath || !File::exists($filePath) || File::isDirectory($filePath)) {
                    return ['success' => false, 'error' => 'Arquivo não encontrado ou acesso restrito.'];
                }

                // Security: Prevent reading secrets, keys, credentials, or sqlite dumps
                $filename = basename($filePath);
                if (preg_match('/(\.env|\.pem|\.key|\.p12|\.pfx|id_rsa|auth\.json|credentials|\.sqlite)/i', $filename)) {
                    return ['success' => false, 'error' => 'Acesso negado: leitura de arquivos sensíveis ou credenciais é proibida pelo escudo de segurança.'];
                }

                $content = File::get($filePath);
                // Limit read size to 64KB for safety
                if (strlen($content) > 65536) {
                    $content = substr($content, 0, 65536) . "\n\n... [Arquivo truncado para 64KB]";
                }

                return [
                    'success' => true,
                    'file' => $arguments['relative_path'],
                    'size_bytes' => File::size($filePath),
                    'content' => $content,
                ];

            case 'search_project_files':
                $project = Project::find($arguments['project_id'] ?? 0);
                if (!$project) return ['success' => false, 'error' => 'Projeto não encontrado.'];

                $targetPath = $this->resolveSafeProjectPath($project->path, '');
                if (!$targetPath || !File::exists($targetPath)) {
                    return ['success' => false, 'error' => 'Caminho do projeto inacessível.'];
                }

                $query = trim((string) ($arguments['query'] ?? ''));
                if ($query === '') {
                    return ['success' => false, 'error' => 'Informe um termo de busca (query).'];
                }

                $matches = [];
                foreach (File::allFiles($targetPath) as $file) {
                    $rel = str_replace($targetPath . DIRECTORY_SEPARATOR, '', $file->getPathname());
                    if (preg_match('/(node_modules|vendor|\.git|\.env)/i', $rel)) {
                        continue;
                    }
                    if ($file->getSize() > 524288) {
                        continue;
                    }
                    $fileContent = @File::get($file->getPathname());
                    if ($fileContent && stripos($fileContent, $query) !== false) {
                        $matches[] = [
                            'file' => $rel,
                            'size_bytes' => $file->getSize(),
                        ];
                        if (count($matches) >= 25) break;
                    }
                }

                return [
                    'success' => true,
                    'project' => $project->name,
                    'query' => $query,
                    'matches' => $matches,
                ];

            case 'create_project_file':
                $project = Project::find($arguments['project_id'] ?? 0);
                if (!$project) return ['success' => false, 'error' => 'Projeto não encontrado.'];

                $filePath = $this->resolveSafeProjectPath($project->path, $arguments['relative_path'] ?? '');
                if (!$filePath) return ['success' => false, 'error' => 'Caminho inválido fora do workspace.'];

                $dir = dirname($filePath);
                if (!File::exists($dir)) {
                    File::makeDirectory($dir, 0755, true);
                }

                File::put($filePath, $arguments['content'] ?? '');
                return [
                    'success' => true,
                    'message' => "Arquivo criado com sucesso em {$arguments['relative_path']}",
                    'size_bytes' => File::size($filePath),
                ];

            case 'edit_project_file':
                $project = Project::find($arguments['project_id'] ?? 0);
                if (!$project) return ['success' => false, 'error' => 'Projeto não encontrado.'];

                $filePath = $this->resolveSafeProjectPath($project->path, $arguments['relative_path'] ?? '');
                if (!$filePath || !File::exists($filePath)) {
                    return ['success' => false, 'error' => 'Arquivo não existe.'];
                }

                $currentContent = File::get($filePath);
                $target = $arguments['target_text'] ?? '';
                $replacement = $arguments['replacement_text'] ?? '';

                if (!str_contains($currentContent, $target)) {
                    return ['success' => false, 'error' => 'O texto alvo especificado não foi encontrado no arquivo.'];
                }

                $newContent = str_replace($target, $replacement, $currentContent);
                File::put($filePath, $newContent);

                return [
                    'success' => true,
                    'message' => "Arquivo {$arguments['relative_path']} atualizado com sucesso.",
                ];

            case 'get_project_git_status':
                $project = Project::find($arguments['project_id'] ?? 0);
                if (!$project) return ['success' => false, 'error' => 'Projeto não encontrado.'];

                $dir = escapeshellarg($project->path);
                $statusOutput = shell_exec("git -C {$dir} status --short 2>&1");
                $branchOutput = shell_exec("git -C {$dir} branch --show-current 2>&1");

                return [
                    'success' => true,
                    'project' => $project->name,
                    'branch' => trim($branchOutput ?: 'main'),
                    'status' => trim($statusOutput ?: 'Working tree clean (sem arquivos pendentes)'),
                ];

            case 'list_businesses':
                BusinessController::ensureCoreBusinessesExist();
                return [
                    'success' => true,
                    'businesses' => Business::all()->map(fn($b) => [
                        'id' => $b->id,
                        'name' => $b->name,
                        'slug' => $b->slug,
                        'category' => $b->category,
                        'status' => $b->status,
                        'budget_limit_brl' => $b->budget_limit_brl,
                        'accounts' => $b->accounts_list,
                        'automation_params' => $b->automation_config,
                    ])->toArray(),
                ];

            case 'get_business_status':
                BusinessController::ensureCoreBusinessesExist();
                $business = Business::with(['tasks' => fn($q) => $q->latest()->limit(5)])->find($arguments['business_id'] ?? 0);
                if (!$business) return ['success' => false, 'error' => 'Negócio não encontrado.'];

                return [
                    'success' => true,
                    'business' => $business,
                    'accounts' => $business->accounts_list,
                    'automation_params' => $business->automation_config,
                ];

            case 'update_business_automation':
                $business = Business::find($arguments['business_id'] ?? 0);
                if (!$business) return ['success' => false, 'error' => 'Negócio não encontrado.'];

                $settings = is_array($business->settings) ? $business->settings : [];
                $mergedAutomation = array_merge($business->automation_config, $arguments['automation_params'] ?? []);
                $settings['automation_params'] = $mergedAutomation;
                $business->settings = $settings;
                if (isset($arguments['budget_limit_brl'])) {
                    $business->budget_limit_brl = (float) $arguments['budget_limit_brl'];
                }
                if (Schema::hasColumn('businesses', 'automation_params')) {
                    $business->automation_params = $mergedAutomation;
                }
                $business->save();

                return [
                    'success' => true,
                    'message' => "Parâmetros de automação do negócio {$business->name} atualizados com sucesso.",
                    'automation_params' => $business->automation_config,
                ];

            case 'manage_business_accounts':
                $business = Business::find($arguments['business_id'] ?? 0);
                if (!$business) return ['success' => false, 'error' => 'Negócio não encontrado.'];

                $accounts = $business->accounts_list;
                $newAcc = [
                    'id' => $arguments['id'] ?? ('acc_' . substr(md5(($arguments['platform'] ?? '') . ($arguments['handle'] ?? '')), 0, 8)),
                    'platform' => $arguments['platform'] ?? 'TikTok Shop',
                    'handle' => $arguments['handle'] ?? '@conta',
                    'account_id' => $arguments['account_id'] ?? '',
                    'email_or_login' => $arguments['email_or_login'] ?? '',
                    'affiliate_showcase_url' => $arguments['affiliate_showcase_url'] ?? '',
                    'webhook_url' => $arguments['webhook_url'] ?? '',
                    'status' => $arguments['status'] ?? 'active',
                    'notes' => $arguments['notes'] ?? '',
                ];

                $replaced = false;
                foreach ($accounts as $idx => $existing) {
                    if (($existing['handle'] ?? '') === $newAcc['handle'] && ($existing['platform'] ?? '') === $newAcc['platform']) {
                        $accounts[$idx] = array_merge($existing, $newAcc);
                        $replaced = true;
                        break;
                    }
                }
                if (!$replaced) {
                    $accounts[] = $newAcc;
                }

                $settings = is_array($business->settings) ? $business->settings : [];
                $settings['accounts'] = $accounts;
                $business->settings = $settings;
                if (Schema::hasColumn('businesses', 'accounts')) {
                    $business->accounts = $accounts;
                }
                $business->save();

                return [
                    'success' => true,
                    'message' => "Conta {$newAcc['handle']} ({$newAcc['platform']}) vinculada ao negócio {$business->name}.",
                    'accounts' => $business->accounts_list,
                ];

            case 'run_business_automation':
                $business = Business::find($arguments['business_id'] ?? 0);
                if (!$business) return ['success' => false, 'error' => 'Negócio não encontrado.'];

                $params = $business->automation_config;
                $accounts = $business->accounts_list;
                $agentName = $params['assigned_agent'] ?? 'Jeffrey';
                $customObjective = $arguments['custom_objective'] ?? null;

                $accountsSummary = collect($accounts)->map(function ($acc) {
                    $plat = $acc['platform'] ?? 'Plataforma';
                    $handle = $acc['handle'] ?? 'sem-handle';
                    $affId = !empty($acc['account_id']) ? " (ID: {$acc['account_id']})" : '';
                    $url = !empty($acc['affiliate_showcase_url']) ? " [Link: {$acc['affiliate_showcase_url']}]" : '';
                    return "- {$plat}: {$handle}{$affId}{$url}";
                })->implode("\n");
                if (empty($accountsSummary)) {
                    $accountsSummary = "- Nenhuma conta cadastrada.";
                }

                $taskTitle = $customObjective
                    ? "[{$business->name}] {$customObjective}"
                    : "Ciclo Autônomo [{$business->name}]: Gerar {$params['daily_deliverables_goal']} entregáveis ({$params['niche']})";

                $fullPrompt = <<<PROMPT
Execute o ciclo de gestão automatizada para o negócio **{$business->name}** (Categoria: {$business->category}).

### 1. CONTAS VINCULADAS DO NEGÓCIO (gerencie e direcione a produção para estas contas):
{$accountsSummary}

### 2. PARÂMETROS OPERACIONAIS DO NEGÓCIO:
- **Nicho / Foco:** {$params['niche']}
- **Público-Alvo:** {$params['target_audience']}
- **Meta Diária:** {$params['daily_deliverables_goal']} entregáveis completos
- **Comissão Mínima / Margem:** {$params['min_commission_percent']}% | Faixa de Preço: R$ {$params['price_range_brl']}
- **Tom de Voz:** {$params['tone_of_voice']}
- **CTA Padrão:** {$params['cta_template']}
- **Modo de Pipeline:** {$params['pipeline_mode']}
- **Regras Específicas:** {$params['custom_prompt_rules']}
PROMPT;
                if ($customObjective) {
                    $fullPrompt .= "\n\n### 3. OBJETIVO ESPECÍFICO DESTE CICLO:\n{$customObjective}";
                }

                return $this->executeTool('create_task', [
                    'title' => mb_substr($taskTitle, 0, 120),
                    'type' => 'business_automation',
                    'agent_name' => $agentName,
                    'business_id' => $business->id,
                    'payload' => [
                        'prompt' => $fullPrompt,
                        'business_slug' => $business->slug,
                        'business_name' => $business->name,
                        'accounts' => $accounts,
                        'automation_params' => $params,
                    ],
                ], $userId, $conversationId);

            case 'get_system_metrics':
                return [
                    'success' => true,
                    'metrics' => $this->vps->getSystemSummary(),
                    'budget' => $this->budget->getBudgetStatus(),
                ];

            case 'list_docker_containers':
                $output = shell_exec('docker ps --format "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null');
                $containers = [];
                if ($output) {
                    $lines = explode("\n", trim($output));
                    foreach ($lines as $line) {
                        $parts = explode("\t", $line);
                        if (count($parts) >= 4) {
                            $containers[] = [
                                'id' => $parts[0],
                                'name' => $parts[1],
                                'image' => $parts[2],
                                'status' => $parts[3],
                                'ports' => $parts[4] ?? '',
                            ];
                        }
                    }
                }
                return [
                    'success' => true,
                    'containers' => $containers,
                    'count' => count($containers),
                ];

            case 'inspect_ai_models':
                return [
                    'success' => true,
                    'ollama_models' => $this->ollama->listModels(),
                    'connection' => $this->ollama->testConnection(),
                ];

            case 'create_task':
                $payloadData = $arguments['payload'] ?? [];
                if ($conversationId && empty($payloadData['conversation_id'])) {
                    $payloadData['conversation_id'] = $conversationId;
                }
                if ($userId && empty($payloadData['user_id'])) {
                    $payloadData['user_id'] = $userId;
                }
                if (!isset($payloadData['allow_gemini'])) {
                    try {
                        $aiGateway = app(AiGatewayService::class);
                        $u = $userId ? \App\Models\User::find($userId) : null;
                        $payloadData['allow_gemini'] = $aiGateway->canUserAccessProvider($u, 'gemini');
                    } catch (\Throwable $e) {
                        $payloadData['allow_gemini'] = true;
                    }
                }
                if (empty($payloadData['prompt'])) {
                    $payloadData['prompt'] = $arguments['prompt'] ?? $arguments['title'] ?? 'Executar tarefa solicitada';
                }

                $dependsOnTaskId = $arguments['depends_on_task_id'] ?? ($payloadData['depends_on_task_id'] ?? null);
                if ($dependsOnTaskId) {
                    $payloadData['depends_on_task_id'] = (int) $dependsOnTaskId;
                }

                $task = Task::create([
                    'title' => $arguments['title'] ?? 'Nova Tarefa',
                    'type' => $arguments['type'] ?? 'research',
                    'agent_name' => $arguments['agent_name'] ?? 'Jeffrey',
                    'business_id' => $arguments['business_id'] ?? null,
                    'payload' => $payloadData,
                    'status' => 'pending',
                ]);

                // Only push to Redis immediately if this task is NOT waiting on another task to finish first
                if (!$dependsOnTaskId) {
                    try {
                        $queuePayload = json_encode([
                            'id' => (string) $task->id,
                            'type' => $task->type,
                            'agent_name' => $task->agent_name,
                            'business_id' => $task->business_id,
                            'payload' => array_merge($payloadData, [
                                'task_id' => $task->id,
                                'conversation_id' => $conversationId,
                                'prompt' => $payloadData['prompt'],
                            ]),
                            'created_at' => now()->toIso8601String(),
                        ]);
                        Redis::lpush('empire:jeffrey:tasks', $queuePayload);
                    } catch (\Exception $e) {
                        Log::warning("Redis queue push deferred for task #{$task->id}: " . $e->getMessage());
                    }
                }

                return [
                    'success' => true,
                    'task' => $task,
                    'depends_on_task_id' => $dependsOnTaskId ? (int) $dependsOnTaskId : null,
                    'message' => $dependsOnTaskId
                        ? "Tarefa #{$task->id} criada em fila encadeada (aguardando conclusão da Tarefa #{$dependsOnTaskId})."
                        : "Tarefa #{$task->id} enfileirada no worker assíncrono do Império.",
                ];

            case 'create_task_pipeline':
                $steps = $arguments['steps'] ?? [];
                $businessId = $arguments['business_id'] ?? null;
                if (empty($steps) || !is_array($steps)) {
                    return ['success' => false, 'error' => 'Nenhuma etapa (steps) informada para o pipeline de tarefas.'];
                }

                $createdTasks = [];
                $previousTaskId = null;

                foreach ($steps as $idx => $step) {
                    $stepNum = $idx + 1;
                    $totalSteps = count($steps);
                    $rawTitle = $step['title'] ?? "Etapa {$stepNum}/{$totalSteps}";
                    $stepTitle = str_starts_with($rawTitle, 'Etapa') ? $rawTitle : "Etapa {$stepNum}/{$totalSteps}: {$rawTitle}";
                    $stepType = $step['type'] ?? ($idx === 0 ? 'research' : 'content_creation');
                    $stepAgent = $step['agent_name'] ?? ($idx === 0 ? 'Research Agent' : 'Copy & Hooks Agent');
                    $stepPrompt = $step['prompt'] ?? $rawTitle;

                    $res = $this->executeTool('create_task', [
                        'title' => mb_substr($stepTitle, 0, 120),
                        'type' => $stepType,
                        'agent_name' => $stepAgent,
                        'business_id' => $businessId,
                        'depends_on_task_id' => $previousTaskId,
                        'payload' => [
                            'prompt' => $stepPrompt,
                            'pipeline_step' => $stepNum,
                            'pipeline_total' => $totalSteps,
                            'depends_on_task_id' => $previousTaskId,
                            'conversation_id' => $conversationId,
                        ],
                    ], $userId, $conversationId);

                    if (!empty($res['task']->id)) {
                        $createdTasks[] = $res['task'];
                        $previousTaskId = $res['task']->id;
                    }
                }

                return [
                    'success' => true,
                    'pipeline_tasks' => $createdTasks,
                    'message' => count($createdTasks) . ' tarefas encadeadas criadas com sucesso.',
                ];

            case 'get_task_status':
                $task = Task::find($arguments['task_id'] ?? 0);
                if (!$task) return ['success' => false, 'error' => 'Tarefa não encontrada.'];
                return [
                    'success' => true,
                    'task' => $task,
                ];

            case 'list_tasks':
                $tasks = Task::latest()->limit(10)->get(['id', 'title', 'type', 'agent_name', 'status', 'result', 'error_message', 'started_at', 'completed_at', 'created_at']);
                return [
                    'success' => true,
                    'tasks' => $tasks->toArray(),
                ];

            case 'web_search':
                $query = trim((string) ($arguments['query'] ?? ''));
                if ($query === '') {
                    return ['success' => false, 'error' => 'Termo de busca vazio.'];
                }
                return [
                    'success' => true,
                    'query' => $query,
                    'results' => $this->performWebSearch($query),
                ];

            case 'create_business':
                $name = trim((string) ($arguments['name'] ?? ''));
                if ($name === '') return ['success' => false, 'error' => 'Nome do negócio é obrigatório.'];
                $slug = \Illuminate\Support\Str::slug($name);
                $category = $arguments['category'] ?? 'General Digital Business';
                $budget = (float) ($arguments['budget_limit_brl'] ?? 30.00);
                $params = $arguments['automation_params'] ?? [];
                $accounts = $arguments['accounts'] ?? [];

                $business = Business::create([
                    'name' => $name,
                    'slug' => $slug,
                    'category' => $category,
                    'description' => $arguments['description'] ?? "Negócio digital criado autonomamente por Jeffrey.",
                    'status' => 'active',
                    'template_used' => 'autonomous-business',
                    'storage_path' => "businesses/{$slug}",
                    'budget_limit_brl' => $budget,
                    'settings' => [
                        'accounts' => $accounts,
                        'automation_params' => $params,
                    ],
                    'accounts' => $accounts,
                    'automation_params' => $params,
                ]);

                return [
                    'success' => true,
                    'business' => [
                        'id' => $business->id,
                        'name' => $business->name,
                        'slug' => $business->slug,
                        'category' => $business->category,
                        'budget_limit_brl' => $business->budget_limit_brl,
                    ],
                    'message' => "Negócio '{$business->name}' (ID #{$business->id}) criado e ativado com sucesso!",
                ];

            case 'save_memory':
                $content = trim((string) ($arguments['content'] ?? ''));
                if ($content === '') return ['success' => false, 'error' => 'Conteúdo da memória não pode ser vazio.'];
                $category = $arguments['category'] ?? 'aprendizado';
                $bizId = $arguments['business_id'] ?? null;

                $mem = JeffreyMemory::create([
                    'business_id' => $bizId,
                    'category' => $category,
                    'content' => $content,
                    'confidence_score' => 1.0,
                    'is_active' => true,
                ]);

                return [
                    'success' => true,
                    'memory_id' => $mem->id,
                    'message' => "Diretriz memorizada com sucesso: \"{$content}\"",
                ];

            case 'trigger_video_generation':
                $productName = trim((string) ($arguments['product_name'] ?? ''));
                if ($productName === '') return ['success' => false, 'error' => 'Nome do produto/vídeo é obrigatório.'];
                $price = $arguments['product_price'] ?? 'Oferta Especial';
                $cat = $arguments['category'] ?? 'generic';
                $bizId = $arguments['business_id'] ?? null;

                $task = Task::create([
                    'business_id' => $bizId,
                    'agent_name' => 'Video Agent',
                    'title' => "Geração de Vídeo: {$productName}",
                    'type' => 'tiktok_video_pipeline',
                    'status' => 'pending',
                    'payload' => [
                        'product_name' => $productName,
                        'product_price' => $price,
                        'category' => $cat,
                        'allow_gemini' => true,
                    ],
                    'estimated_cost_brl' => 0.00,
                ]);

                try {
                    Redis::lpush('empire:jeffrey:tasks', json_encode([
                        'id' => (string) $task->id,
                        'title' => $task->title,
                        'type' => $task->type,
                        'agent_name' => $task->agent_name,
                        'business_id' => $bizId,
                        'payload' => $task->payload,
                        'created_at' => now()->toIso8601String(),
                    ]));
                } catch (\Throwable $e) {
                    Log::warning("Redis push deferred for video task #{$task->id}: " . $e->getMessage());
                }

                return [
                    'success' => true,
                    'task_id' => $task->id,
                    'message' => "Pipeline de vídeo disparado (Tarefa #{$task->id}) para o produto '{$productName}'. O worker executará o roteiro via Gemini e renderização de vídeo vertical.",
                ];

            case 'manage_docker_service':
                $action = strtolower(trim((string) ($arguments['action'] ?? 'status')));
                $service = strtolower(trim((string) ($arguments['service'] ?? '')));
                $allowedServices = ['worker', 'backend', 'frontend', 'redis', 'ollama'];
                if (!in_array($service, $allowedServices, true)) {
                    return ['success' => false, 'error' => "Serviço não autorizado. Permitidos: " . implode(', ', $allowedServices)];
                }

                if ($action === 'restart') {
                    $cmd = "docker compose restart {$service} 2>&1";
                    $out = shell_exec($cmd);
                    return [
                        'success' => true,
                        'message' => "Comando de reinicialização disparado para '{$service}'.",
                        'output' => trim((string) $out),
                    ];
                }

                $cmd = "docker compose ps {$service} 2>&1";
                $out = shell_exec($cmd);
                return [
                    'success' => true,
                    'service' => $service,
                    'status_output' => trim((string) $out),
                ];

            default:
                return ['success' => false, 'error' => "Ferramenta desconhecida: {$toolName}"];
        }
    }

    /**
     * Clean conversational prompt into high-precision search keywords.
     */
    /**
     * Clean conversational prompt into high-precision search keywords with stop-word stripping.
     */
    public function cleanSearchQuery(string $rawPrompt): string
    {
        $q = preg_replace('/^(execute de forma completa.*?:|execute o ciclo.*?:)\s*/isu', '', $rawPrompt);
        $q = trim(explode("\n", $q)[0] ?? $rawPrompt);
        $q = preg_replace(
            '/\b(identificar|identifique|listar|liste|pesquisar|pesquise|buscar|busque|encontrar|encontre|fazer um levantamento|faça um levantamento|me de|me dê|quero|preciso de|quais são|quais os|os \d+|as \d+|\d+ melhores|\d+ principais)\b/iu',
            ' ',
            $q
        );
        $q = preg_replace('/\btiktokshop\b/iu', 'TikTok Shop Brasil', $q);
        $q = preg_replace('/\bviralizados\b/iu', 'virais mais vendidos', $q);

        // Strip standalone prepositions / short noise words (e.g. "na", "no", "em", "de", "da")
        $q = preg_replace('/\b(na|no|em|de|da|do|dos|das|para|pra|pro|com|um|uma|uns|umas|o|a|os|as)\b/iu', ' ', $q);
        $q = trim(preg_replace('/\s+/', ' ', $q), " -:,.?!");

        // If the query was reduced to empty or generic noise, fallback to rich e-commerce discovery query
        if (mb_strlen($q) < 4) {
            if (preg_match('/(tiktok|shop|produto|viral|afiliad|achadinho)/iu', $rawPrompt)) {
                return 'produtos virais mais vendidos TikTok Shop Brasil achadinhos';
            }
            return 'produtos em alta e tendencias de mercado brasil';
        }

        // If query relates to TikTok or products, anchor it with high-precision commercial intent
        if (preg_match('/(tiktok|shop|achadinho|afiliad|shopee)/iu', $rawPrompt) && !str_contains(strtolower($q), 'tiktok shop')) {
            $q = 'TikTok Shop Brasil ' . $q;
        }

        return mb_substr($q, 0, 110);
    }

    protected function decodeSearchRedirectUrl(string $rawUrl): string
    {
        $u = trim(html_entity_decode($rawUrl));
        if (str_contains($u, 'uddg=')) {
            if (preg_match('/[?&]uddg=([^&]+)/', $u, $m)) {
                return urldecode($m[1]);
            }
        }
        if (str_contains($u, '/RU=')) {
            if (preg_match('#/RU=([^/]+)/RK=#', $u, $m)) {
                return urldecode($m[1]);
            }
        }
        if (str_starts_with($u, '//')) {
            return 'https:' . $u;
        }
        return $u;
    }

    /**
     * Perform live zero-cost multi-engine web search (Bing RSS, Yahoo BR, DuckDuckGo, Google News RSS, Mercado Livre BR).
     */
    public function performWebSearch(string $query): array
    {
        $cleanQ = $this->cleanSearchQuery($query);
        $results = [];
        $seenUrls = [];

        $headers = [
            'User-Agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36',
            'Accept-Language' => 'pt-BR,pt;q=0.9',
        ];

        $addResult = function (string $title, string $url, string $snippet) use (&$results, &$seenUrls) {
            $realUrl = $this->decodeSearchRedirectUrl($url);
            if ($title === '' || $realUrl === '' || !str_starts_with($realUrl, 'http')) {
                return;
            }

            // Noise Blocklist: Narcóticos Anônimos (NA), Dictionaries, Chemistry elements, Disambiguation
            $lowUrl = strtolower($realUrl);
            $lowTitle = strtolower($title);
            $lowSnip = strtolower($snippet);

            $noiseDomains = ['na.org.br', 'na.org', 'virtual-na.org', 'na-pt.org', 'dicio.com.br', 'priberam.pt', 'significados.com.br'];
            foreach ($noiseDomains as $nd) {
                if (str_contains($lowUrl, $nd)) {
                    return; // Discard noise
                }
            }

            if (preg_match('/(narcóticos anônimos|narcotics anonymous|tabela periódica|chemical element sodium|significado de na\b|contr\. de em com a)/iu', $lowTitle . ' ' . $lowSnip)) {
                return; // Discard noise
            }

            if (isset($seenUrls[$realUrl])) {
                return;
            }
            $seenUrls[$realUrl] = true;
            $results[] = [
                'title' => trim(preg_replace('/\s+/', ' ', $title)),
                'url' => $realUrl,
                'snippet' => trim(preg_replace('/\s+/', ' ', $snippet)),
            ];
        };

        // 1. Bing Web Search RSS (PT-BR)
        try {
            $bingUrl = 'https://www.bing.com/search?q=' . urlencode($cleanQ) . '&format=rss&setlang=pt-BR&cc=BR';
            $resp = Http::timeout(6)->withHeaders($headers)->get($bingUrl);
            if ($resp->successful() && str_contains($resp->body(), '<item>')) {
                preg_match_all('/<item>.*?<title>(.*?)<\/title>.*?<link>(.*?)<\/link>.*?<description>(.*?)<\/description>.*?<\/item>/s', $resp->body(), $items);
                foreach (array_slice($items[1] ?? [], 0, 8) as $idx => $rawT) {
                    $t = trim(html_entity_decode(strip_tags(str_replace(['<![CDATA[', ']]>'], '', $rawT))));
                    $l = trim($items[2][$idx] ?? '');
                    $d = trim(html_entity_decode(strip_tags(str_replace(['<![CDATA[', ']]>'], '', $items[3][$idx] ?? ''))));
                    $addResult($t, $l, $d);
                }
            }
        } catch (\Throwable $e) {}

        // 2. Yahoo Brasil Web Search
        if (count($results) < 8) {
            try {
                $yahooUrl = 'https://br.search.yahoo.com/search?p=' . urlencode($cleanQ) . '&ei=UTF-8';
                $resp = Http::timeout(6)->withHeaders($headers)->get($yahooUrl);
                if ($resp->successful()) {
                    preg_match_all('/<div[^>]+class="[^"]*algo-sr[^"]*"[^>]*>(.*?)<\/div>\s*<\/div>\s*<\/li>/s', $resp->body(), $blocks);
                    foreach (array_slice($blocks[1] ?? [], 0, 8) as $blk) {
                        if (preg_match('/<a[^>]+href="([^"]+)"[^>]*>(.*?)<\/a>/s', $blk, $aM)) {
                            $rawHref = $aM[1];
                            $t = trim(html_entity_decode(strip_tags($aM[2])));
                            $s = '';
                            if (preg_match('/<div[^>]+class="[^"]*compText[^"]*"[^>]*>(.*?)<\/div>/s', $blk, $sM)) {
                                $s = trim(html_entity_decode(strip_tags($sM[1])));
                            }
                            $addResult($t, $rawHref, $s);
                        }
                    }
                }
            } catch (\Throwable $e) {}
        }

        // 3. DuckDuckGo HTML Search
        if (count($results) < 8) {
            try {
                $resp = Http::timeout(6)
                    ->withHeaders($headers)
                    ->asForm()
                    ->post('https://html.duckduckgo.com/html/', ['q' => $cleanQ, 'kl' => 'br-pt']);

                if ($resp->successful() && str_contains($resp->body(), 'result__a')) {
                    $body = $resp->body();
                    preg_match_all('/<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)<\/a>/s', $body, $titleMatches);
                    preg_match_all('/<a[^>]+class="result__snippet"[^>]*>(.*?)<\/a>/s', $body, $snipMatches);
                    $urls = $titleMatches[1] ?? [];
                    $titles = $titleMatches[2] ?? [];
                    $snippets = $snipMatches[1] ?? [];

                    foreach (array_slice($titles, 0, 8) as $idx => $rawTitle) {
                        $addResult(
                            trim(html_entity_decode(strip_tags($rawTitle))),
                            $urls[$idx] ?? '',
                            isset($snippets[$idx]) ? trim(html_entity_decode(strip_tags($snippets[$idx]))) : ''
                        );
                    }
                }
            } catch (\Throwable $e) {}
        }

        // 4. Google News RSS (PT-BR)
        if (count($results) < 8) {
            try {
                $rssUrl = 'https://news.google.com/rss/search?q=' . urlencode($cleanQ) . '&hl=pt-BR&gl=BR&ceid=BR:pt-419';
                $resp = Http::timeout(6)->withHeaders($headers)->get($rssUrl);
                if ($resp->successful()) {
                    preg_match_all('/<item>.*?<title>(.*?)<\/title>.*?<link>(.*?)<\/link>.*?<pubDate>(.*?)<\/pubDate>.*?<\/item>/s', $resp->body(), $items);
                    foreach (array_slice($items[1] ?? [], 0, 6) as $idx => $rawT) {
                        $addResult(
                            trim(html_entity_decode(str_replace(['<![CDATA[', ']]>'], '', $rawT))),
                            trim($items[2][$idx] ?? ''),
                            'Notícia/Tendência publicada em ' . trim($items[3][$idx] ?? '')
                        );
                    }
                }
            } catch (\Throwable $e) {}
        }

        // 5. Real Brazilian E-Commerce Products & Prices when searching products / TikTok Shop / viral items
        $lowQ = mb_strtolower($query . ' ' . $cleanQ);
        if (preg_match('/(tiktok|produto|viral|virais|afiliado|loja|shop|vendido|preço|preco|oferta)/iu', $lowQ)) {
            $productTerms = preg_match('/(tiktok|viral|virais|vendidos)/iu', $lowQ)
                ? ['mini processador eletrico usb', 'escova secadora alisadora', 'umidificador difusor led', 'projetor portatil smart', 'massageador eletrico portatil']
                : [$cleanQ];

            foreach (array_slice($productTerms, 0, 4) as $pq) {
                try {
                    $mlResp = Http::timeout(4)->withHeaders($headers)->get('https://api.mercadolibre.com/sites/MLB/search', [
                        'q' => $pq,
                        'limit' => 2,
                    ]);
                    if ($mlResp->successful()) {
                        foreach (array_slice($mlResp->json('results') ?? [], 0, 2) as $prod) {
                            $title = $prod['title'] ?? null;
                            $price = $prod['price'] ?? null;
                            $permalink = $prod['permalink'] ?? null;
                            if ($title && $price && $permalink) {
                                $tiktokUrl = 'https://www.tiktok.com/search?q=' . urlencode(mb_substr($title, 0, 45));
                                $priceFmt = number_format((float) $price, 2, ',', '.');
                                $addResult(
                                    "[Produto Real Brasil] {$title} — R$ {$priceFmt}",
                                    $permalink,
                                    "Preço Real Verificado: R$ {$priceFmt} | Link Real: {$permalink} | Vídeos no TikTok: {$tiktokUrl}"
                                );
                            }
                        }
                    }
                } catch (\Throwable $e) {}
            }
        }

        return array_slice($results, 0, 12);
    }

    /**
     * Resolves and verifies that a project subpath is safely confined within the authorized project directory.
     * Prevents directory traversal attacks and heals container volume paths.
     */
    protected function resolveSafeProjectPath(string $basePath, string $subPath): ?string
    {
        $realBase = realpath($basePath);
        if (!$realBase) {
            // Try storage_path or /var/spirandeli fallback for business workspaces inside Docker
            if (preg_match('#businesses[/\\\\]([a-zA-Z0-9_\-]+)#', $basePath, $m)) {
                $slug = $m[1];
                $candidates = [
                    storage_path("businesses/{$slug}"),
                    "/var/spirandeli/businesses/{$slug}",
                    base_path("businesses/{$slug}"),
                ];
                foreach ($candidates as $cand) {
                    if (File::isDirectory($cand)) {
                        $realBase = realpath($cand);
                        break;
                    }
                }
                if (!$realBase) {
                    $fallbackDir = storage_path("businesses/{$slug}");
                    @File::makeDirectory($fallbackDir, 0775, true);
                    $realBase = realpath($fallbackDir);
                }
            } else {
                $realBase = realpath(base_path($basePath));
            }
            if (!$realBase) return null;
        }

        $cleanSub = str_replace(["\0"], '', $subPath);
        if (preg_match('#(^|[/\\\\])\.\.([/\\\\]|$)#', $cleanSub)) {
            return null;
        }
        $cleanSub = ltrim($cleanSub, '/\\');
        $fullPath = $realBase . ($cleanSub ? DIRECTORY_SEPARATOR . $cleanSub : '');

        // Verify symlink / realpath confinement inside $realBase
        $existingTarget = File::exists($fullPath) ? realpath($fullPath) : realpath(dirname($fullPath));
        if ($existingTarget && !str_starts_with($existingTarget, $realBase)) {
            return null;
        }

        return $fullPath;
    }
}
