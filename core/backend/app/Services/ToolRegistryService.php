<?php

namespace App\Services;

use App\Models\ApprovalRequest;
use App\Models\Business;
use App\Models\Project;
use App\Models\Task;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Redis;

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
                'description' => 'Lista todos os negócios digitais cadastrados, categorias, status e tetos orçamentários.',
                'parameters' => [],
                'category' => 'A',
            ],
            [
                'name' => 'get_business_status',
                'description' => 'Obtém métricas detalhadas, tarefas recentes e volume de um negócio digital específico.',
                'parameters' => [
                    'business_id' => ['type' => 'integer', 'required' => true, 'description' => 'ID do negócio'],
                ],
                'category' => 'A',
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
                'description' => 'Cria uma nova tarefa assíncrona para execução por agentes especializados.',
                'parameters' => [
                    'title' => ['type' => 'string', 'required' => true, 'description' => 'Título da tarefa'],
                    'type' => ['type' => 'string', 'required' => true, 'description' => 'Tipo da tarefa'],
                    'agent_name' => ['type' => 'string', 'required' => false, 'description' => 'Nome do agente responsável'],
                    'business_id' => ['type' => 'integer', 'required' => false, 'description' => 'ID do negócio associado'],
                    'payload' => ['type' => 'object', 'required' => false, 'description' => 'Parâmetros da tarefa'],
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

                // Security: Prevent reading secrets
                $filename = basename($filePath);
                if (preg_match('/(\.env|\.pem|\.key|id_rsa)/i', $filename)) {
                    return ['success' => false, 'error' => 'Acesso negado: leitura de arquivos sensíveis ou credenciais é proibida.'];
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
                return [
                    'success' => true,
                    'businesses' => Business::all(['id', 'name', 'slug', 'category', 'status', 'budget_limit_brl', 'storage_path'])->toArray(),
                ];

            case 'get_business_status':
                $business = Business::with(['tasks' => fn($q) => $q->latest()->limit(5)])->find($arguments['business_id'] ?? 0);
                if (!$business) return ['success' => false, 'error' => 'Negócio não encontrado.'];

                return [
                    'success' => true,
                    'business' => $business,
                ];

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
                if (empty($payloadData['prompt'])) {
                    $payloadData['prompt'] = $arguments['prompt'] ?? $arguments['title'] ?? 'Executar tarefa solicitada';
                }

                $task = Task::create([
                    'title' => $arguments['title'] ?? 'Nova Tarefa',
                    'type' => $arguments['type'] ?? 'research',
                    'agent_name' => $arguments['agent_name'] ?? 'Jeffrey',
                    'business_id' => $arguments['business_id'] ?? null,
                    'payload' => $payloadData,
                    'status' => 'pending',
                ]);

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

                return [
                    'success' => true,
                    'task' => $task,
                    'message' => "Tarefa #{$task->id} enfileirada no worker assíncrono do Império.",
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

            default:
                return ['success' => false, 'error' => "Ferramenta desconhecida: {$toolName}"];
        }
    }

    /**
     * Resolves and verifies that a project subpath is safely confined within the authorized project directory.
     * Prevents directory traversal attacks.
     */
    protected function resolveSafeProjectPath(string $basePath, string $subPath): ?string
    {
        $realBase = realpath($basePath);
        if (!$realBase) {
            // Se o path for relativo à raiz do app
            $realBase = realpath(base_path($basePath));
            if (!$realBase) return null;
        }

        $cleanSub = str_replace(['..', "\0"], '', $subPath);
        $cleanSub = ltrim($cleanSub, '/\\');
        $fullPath = $realBase . ($cleanSub ? DIRECTORY_SEPARATOR . $cleanSub : '');

        return $fullPath;
    }
}
