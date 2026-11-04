<?php

namespace App\Http\Controllers\Api;

use App\Models\Business;
use App\Models\JeffreyMemory;
use App\Models\Task;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Redis;
use Illuminate\Support\Facades\Schema;
use Illuminate\Support\Str;
use Throwable;

class BusinessController extends Controller
{
    /**
     * Ensure all strategic businesses (especially TikTok Shop Afiliados) exist in the DB
     * with default accounts structure and automation parameters.
     */
    public static function ensureCoreBusinessesExist(): void
    {
        $coreDefinitions = [
            [
                'name' => 'TikTok Shop Afiliados',
                'slug' => 'tiktok-shop-afiliados',
                'category' => 'TikTok Shop & Afiliados',
                'description' => 'Operação principal de vendas e comissões no TikTok Shop: curadoria de produtos virais, geração de roteiros persuasivos de 30s, narração neural XTTS/Piper e vídeos 9:16 com pipeline Anti-Ban (máx. 9 vídeos/dia).',
                'budget_limit_brl' => 60.00,
                'status' => 'active',
                'template_used' => 'affiliate-tiktok-shop',
                'storage_path' => 'businesses/tiktok-shop-afiliados',
                'default_accounts' => [
                    [
                        'id' => 'acc_tiktok_main',
                        'platform' => 'TikTok Shop Creator',
                        'handle' => '@seu_perfil_tiktok',
                        'account_id' => 'TT-AFFILIATE-BR-01',
                        'email_or_login' => 'tiktok@spirandeliempire.tech',
                        'affiliate_showcase_url' => 'https://www.tiktok.com/@seu_perfil_tiktok',
                        'webhook_or_integration' => 'http://n8n:5678/webhook/tiktok-shop',
                        'status' => 'connected',
                        'notes' => 'Conta principal de afiliado TikTok Shop. Sempre incluir #parceria e CTA para o carrinho laranja.',
                    ],
                ],
                'default_automation' => [
                    'auto_enabled' => true,
                    'frequency' => '3x_day',
                    'assigned_agent' => 'Research Agent',
                    'niche' => 'Gadgets Úteis, Beleza & Cuidados Pessoais, Casa Inteligente e Achadinhos Virais',
                    'target_audience' => 'Jovens e adultos brasileiros (18-45 anos) compradores por impulso no TikTok',
                    'daily_deliverables_goal' => 9,
                    'min_commission_percent' => 12,
                    'price_range_brl' => 'R$ 29,90 a R$ 149,90',
                    'tone_of_voice' => 'Dinâmico, direto, brasileiro natural, gancho forte nos primeiros 2 segundos',
                    'cta_template' => 'Clica no carrinho laranja aqui embaixo antes que acabe o estoque promocional! #parceria',
                    'pipeline_mode' => 'research_and_script',
                    'custom_prompt_rules' => 'Identificar produtos com alta prova social no TikTok Shop, entregar gancho visual de 2s + roteiro de 30s + descrição com hashtags virais.',
                ],
            ],
            [
                'name' => 'RISADA.exe',
                'slug' => 'risada-exe',
                'category' => 'YouTube Dark (Histórias Bíblicas)',
                'description' => 'Canal de histórias bíblicas com ilustrações originais, voz brasileira masculina e fidelidade teológica rigorosa.',
                'budget_limit_brl' => 50.00,
                'status' => 'active',
                'template_used' => 'youtube-dark-bible',
                'storage_path' => 'businesses/risada-exe',
                'default_accounts' => [
                    [
                        'id' => 'acc_yt_risada',
                        'platform' => 'YouTube Channel',
                        'handle' => '@RISADA.exe',
                        'account_id' => 'UC-RISADA-EXE',
                        'email_or_login' => 'risada@spirandeliempire.tech',
                        'affiliate_showcase_url' => 'https://youtube.com/@RISADA.exe',
                        'webhook_or_integration' => '',
                        'status' => 'connected',
                        'notes' => 'Canal Dark Bíblico. Jamais inventar versículos; citar referências bíblicas reais.',
                    ],
                ],
                'default_automation' => [
                    'auto_enabled' => false,
                    'frequency' => 'daily',
                    'assigned_agent' => 'Content Creator',
                    'niche' => 'Histórias Bíblicas, Curiosidades do Antigo e Novo Testamento, Superação e Fé',
                    'target_audience' => 'Público cristão e interessados em história bíblica no YouTube Shorts e vídeos longos',
                    'daily_deliverables_goal' => 3,
                    'min_commission_percent' => 0,
                    'price_range_brl' => 'Monetização AdSense + Produtos Digitais',
                    'tone_of_voice' => 'Narrativo, solene, envolvente e fiel às Escrituras',
                    'cta_template' => 'Inscreva-se no canal e deixe seu Amém nos comentários!',
                    'pipeline_mode' => 'script_and_voice',
                    'custom_prompt_rules' => 'Validar todas as referências bíblicas (livro, capítulo e versículo) sem alucinar.',
                ],
            ],
            [
                'name' => 'KDP Factory',
                'slug' => 'kdp-factory',
                'category' => 'Amazon KDP Publishing',
                'description' => 'Pipeline de produção de eBooks, devocionais e planos de leitura bíblica para Amazon KDP.',
                'budget_limit_brl' => 40.00,
                'status' => 'active',
                'template_used' => 'amazon-kdp-publishing',
                'storage_path' => 'businesses/kdp-factory',
                'default_accounts' => [
                    [
                        'id' => 'acc_kdp_main',
                        'platform' => 'Amazon KDP Author Central',
                        'handle' => 'Spirandeli Publishing',
                        'account_id' => 'KDP-BR-US-01',
                        'email_or_login' => 'kdp@spirandeliempire.tech',
                        'affiliate_showcase_url' => 'https://kdp.amazon.com',
                        'webhook_or_integration' => '',
                        'status' => 'connected',
                        'notes' => 'Conta de publicação de livros digitais e físicos sob demanda na Amazon.',
                    ],
                ],
                'default_automation' => [
                    'auto_enabled' => false,
                    'frequency' => 'weekly',
                    'assigned_agent' => 'Content Creator',
                    'niche' => 'Devocionais Cristãos, Estudos Bíblicos Temáticos e Desenvolvimento Pessoal',
                    'target_audience' => 'Leitores de Kindle Brasil e EUA',
                    'daily_deliverables_goal' => 1,
                    'min_commission_percent' => 70,
                    'price_range_brl' => 'R$ 19,90 a R$ 39,90 (Royalties 70%)',
                    'tone_of_voice' => 'Profundo, estruturado em capítulos práticos e inspirador',
                    'cta_template' => 'Avalie este livro na Amazon para ajudar mais leitores!',
                    'pipeline_mode' => 'research_and_script',
                    'custom_prompt_rules' => 'Estruturar sumário completo, introdução cativante e capítulos densos prontos para diagramação.',
                ],
            ],
            [
                'name' => 'Digital Products Factory',
                'slug' => 'digital-products',
                'category' => 'Digital Goods & PDFs',
                'description' => 'Estudos bíblicos em PDF, cronologias, planners devocionais e apostilas de alta conversão.',
                'budget_limit_brl' => 30.00,
                'status' => 'active',
                'template_used' => 'digital-products-pdf',
                'storage_path' => 'businesses/digital-products',
                'default_accounts' => [
                    [
                        'id' => 'acc_kiwify_hotmart',
                        'platform' => 'Kiwify / Hotmart',
                        'handle' => 'Spirandeli Digital',
                        'account_id' => 'INFOPROD-01',
                        'email_or_login' => 'vendas@spirandeliempire.tech',
                        'affiliate_showcase_url' => '',
                        'webhook_or_integration' => '',
                        'status' => 'connected',
                        'notes' => 'Checkout de infoprodutos, apostilas e planners em PDF.',
                    ],
                ],
                'default_automation' => [
                    'auto_enabled' => false,
                    'frequency' => 'weekly',
                    'assigned_agent' => 'Business Analyst',
                    'niche' => 'Planners Devocionais, Guias Práticos em PDF e Checklists',
                    'target_audience' => 'Compradores de produtos low-ticket (R$ 19 a R$ 67)',
                    'daily_deliverables_goal' => 2,
                    'min_commission_percent' => 85,
                    'price_range_brl' => 'R$ 19,90 a R$ 67,00',
                    'tone_of_voice' => 'Prático, didático e focado em transformação rápida',
                    'cta_template' => 'Baixe seu material completo pelo link da bio!',
                    'pipeline_mode' => 'research_and_script',
                    'custom_prompt_rules' => 'Criar estrutura de produto + copy de página de vendas + sequência de 3 criativos.',
                ],
            ],
            [
                'name' => 'Printable Factory',
                'slug' => 'printable-factory',
                'category' => 'Printables & Artes',
                'description' => 'Quadros decorativos, cartões e artes em altíssima resolução para impressão física e venda.',
                'budget_limit_brl' => 20.00,
                'status' => 'active',
                'template_used' => 'printable-art',
                'storage_path' => 'businesses/printable-factory',
                'default_accounts' => [
                    [
                        'id' => 'acc_etsy_elo7',
                        'platform' => 'Etsy / Shopee Digital',
                        'handle' => '@SpirandeliPrints',
                        'account_id' => 'PRINTS-01',
                        'email_or_login' => 'prints@spirandeliempire.tech',
                        'affiliate_showcase_url' => '',
                        'webhook_or_integration' => '',
                        'status' => 'connected',
                        'notes' => 'Loja de arquivos digitais imprimíveis.',
                    ],
                ],
                'default_automation' => [
                    'auto_enabled' => false,
                    'frequency' => 'weekly',
                    'assigned_agent' => 'Content Creator',
                    'niche' => 'Artes Cristãs Minimalistas, Planners de Parede e Atividades Infantis',
                    'target_audience' => 'Famílias, professores e decoração home office',
                    'daily_deliverables_goal' => 2,
                    'min_commission_percent' => 80,
                    'price_range_brl' => 'R$ 14,90 a R$ 49,90',
                    'tone_of_voice' => 'Criativo, estético e descritivo',
                    'cta_template' => 'Arquivo digital pronto para imprimir em casa ou gráfica!',
                    'pipeline_mode' => 'research_and_script',
                    'custom_prompt_rules' => 'Gerar prompts detalhados de ilustração + títulos SEO + descrição persuasiva.',
                ],
            ],
        ];

        $hasAccountsCol = Schema::hasColumn('businesses', 'accounts');
        $hasAutomationCol = Schema::hasColumn('businesses', 'automation_params');

        foreach ($coreDefinitions as $def) {
            $biz = Business::where('slug', $def['slug'])->first();
            if (!$biz) {
                $settingsPayload = [
                    'accounts' => $def['default_accounts'],
                    'automation_params' => $def['default_automation'],
                ];
                $createData = [
                    'name' => $def['name'],
                    'slug' => $def['slug'],
                    'category' => $def['category'],
                    'description' => $def['description'],
                    'budget_limit_brl' => $def['budget_limit_brl'],
                    'status' => $def['status'],
                    'template_used' => $def['template_used'],
                    'storage_path' => $def['storage_path'],
                    'settings' => $settingsPayload,
                ];
                if ($hasAccountsCol) {
                    $createData['accounts'] = $def['default_accounts'];
                }
                if ($hasAutomationCol) {
                    $createData['automation_params'] = $def['default_automation'];
                }
                $biz = Business::create($createData);
            } else {
                // Ensure existing seeded business has default accounts & automation_params if empty
                $settings = is_array($biz->settings) ? $biz->settings : [];
                $changed = false;

                if ($biz->slug === 'tiktok-shop-afiliados' && $biz->status === 'provisioning') {
                    $biz->status = 'active';
                    $changed = true;
                }
                if (empty($settings['accounts']) && empty($biz->accounts_list)) {
                    $settings['accounts'] = $def['default_accounts'];
                    if ($hasAccountsCol) {
                        $biz->accounts = $def['default_accounts'];
                    }
                    $changed = true;
                }
                if (empty($settings['automation_params']) && empty($biz->automation_config)) {
                    $settings['automation_params'] = $def['default_automation'];
                    if ($hasAutomationCol) {
                        $biz->automation_params = $def['default_automation'];
                    }
                    $changed = true;
                }
                if ($changed) {
                    $biz->settings = $settings;
                    $biz->save();
                }
            }
        }
    }

    /**
     * List all businesses with tasks, financial records, accounts and automation config.
     */
    public function index(): JsonResponse
    {
        self::ensureCoreBusinessesExist();

        // Order with tiktok-shop-afiliados first as primary operation
        $businesses = Business::withCount(['tasks', 'financialRecords', 'memories'])
            ->orderByRaw("CASE WHEN slug = 'tiktok-shop-afiliados' THEN 0 ELSE 1 END")
            ->orderBy('id', 'asc')
            ->get();

        return response()->json([
            'success' => true,
            'businesses' => $businesses,
        ]);
    }

    /**
     * Show single business details with tasks and memories.
     */
    public function show(int $id): JsonResponse
    {
        $business = Business::with([
            'tasks' => fn($q) => $q->latest()->limit(20),
            'financialRecords' => fn($q) => $q->latest()->limit(20),
            'memories' => fn($q) => $q->where('is_active', true),
        ])->findOrFail($id);

        return response()->json([
            'success' => true,
            'business' => $business,
        ]);
    }

    /**
     * Update business details, accounts and automation parameters.
     */
    public function update(Request $request, int $id): JsonResponse
    {
        $business = Business::findOrFail($id);

        $validated = $request->validate([
            'name' => 'nullable|string|max:255',
            'category' => 'nullable|string|max:255',
            'description' => 'nullable|string',
            'budget_limit_brl' => 'nullable|numeric|min:0|max:200',
            'status' => 'nullable|in:active,paused,provisioning,archived',
            'accounts' => 'nullable|array',
            'automation_params' => 'nullable|array',
        ]);

        if (isset($validated['name'])) $business->name = $validated['name'];
        if (isset($validated['category'])) $business->category = $validated['category'];
        if (array_key_exists('description', $validated)) $business->description = $validated['description'];
        if (isset($validated['budget_limit_brl'])) $business->budget_limit_brl = $validated['budget_limit_brl'];
        if (isset($validated['status'])) $business->status = $validated['status'];

        $settings = is_array($business->settings) ? $business->settings : [];
        if (isset($validated['accounts'])) {
            $settings['accounts'] = $validated['accounts'];
            if (Schema::hasColumn('businesses', 'accounts')) {
                $business->accounts = $validated['accounts'];
            }
        }
        if (isset($validated['automation_params'])) {
            $settings['automation_params'] = $validated['automation_params'];
            if (Schema::hasColumn('businesses', 'automation_params')) {
                $business->automation_params = $validated['automation_params'];
            }
        }
        $business->settings = $settings;
        $business->save();

        $this->syncBusinessMemoryForJeffrey($business);

        return response()->json([
            'success' => true,
            'message' => "Negócio {$business->name} atualizado e sincronizado com o agente Jeffrey!",
            'business' => $business->fresh()->loadCount(['tasks', 'financialRecords', 'memories']),
        ]);
    }

    /**
     * Save or update the accounts linked to a business.
     */
    public function saveAccounts(Request $request, int $id): JsonResponse
    {
        $business = Business::findOrFail($id);
        $request->validate([
            'accounts' => 'Present|array',
        ]);

        $accounts = $request->input('accounts', []);
        $settings = is_array($business->settings) ? $business->settings : [];
        $settings['accounts'] = $accounts;
        $business->settings = $settings;

        if (Schema::hasColumn('businesses', 'accounts')) {
            $business->accounts = $accounts;
        }
        $business->save();

        $this->syncBusinessMemoryForJeffrey($business);

        return response()->json([
            'success' => true,
            'message' => "Contas do negócio {$business->name} salvas com sucesso!",
            'business' => $business->fresh(),
        ]);
    }

    /**
     * Save or update the automation parameters for a business.
     */
    public function saveAutomationParams(Request $request, int $id): JsonResponse
    {
        $business = Business::findOrFail($id);
        $request->validate([
            'automation_params' => 'required|array',
        ]);

        $current = $business->automation_config;
        $merged = array_merge($current, $request->input('automation_params', []));

        $settings = is_array($business->settings) ? $business->settings : [];
        $settings['automation_params'] = $merged;
        $business->settings = $settings;

        if (Schema::hasColumn('businesses', 'automation_params')) {
            $business->automation_params = $merged;
        }
        $business->save();

        $this->syncBusinessMemoryForJeffrey($business);

        return response()->json([
            'success' => true,
            'message' => "Parâmetros de automação de {$business->name} salvos com sucesso!",
            'business' => $business->fresh(),
        ]);
    }

    /**
     * Trigger an immediate automated agent execution cycle for this business using its saved parameters & accounts.
     */
    public function runAgentAutomation(Request $request, int $id): JsonResponse
    {
        $business = Business::findOrFail($id);
        $params = $business->automation_config;
        $accounts = $business->accounts_list;

        $customInstruction = trim((string) $request->input('custom_objective', ''));
        $agentName = $request->input('agent_name') ?: ($params['assigned_agent'] ?? 'Research Agent');
        $provider = $request->input('provider', 'hybrid');

        $accountsText = "Nenhuma conta cadastrada.";
        if (!empty($accounts)) {
            $accLines = [];
            foreach ($accounts as $acc) {
                $plat = $acc['platform'] ?? 'Conta';
                $handle = $acc['handle'] ?? '';
                $accId = $acc['account_id'] ?? '';
                $url = $acc['affiliate_showcase_url'] ?? '';
                $notes = $acc['notes'] ?? '';
                $accLines[] = "- {$plat}: {$handle} (ID: {$accId}) | Link/Vitrine: {$url} | Obs: {$notes}";
            }
            $accountsText = implode("\n", $accLines);
        }

        $niche = $params['niche'] ?? $business->category;
        $audience = $params['target_audience'] ?? 'Público brasileiro';
        $goalCount = $params['daily_deliverables_goal'] ?? 5;
        $minComm = $params['min_commission_percent'] ?? 10;
        $priceRange = $params['price_range_brl'] ?? 'Variado';
        $tone = $params['tone_of_voice'] ?? 'Direto e persuasivo';
        $cta = $params['cta_template'] ?? 'Link na bio!';
        $rules = $params['custom_prompt_rules'] ?? '';

        $objectiveTitle = $customInstruction
            ? "[{$business->name}] {$customInstruction}"
            : "[{$business->name}] Ciclo Automatizado: {$niche}";
        $objectiveTitle = mb_substr($objectiveTitle, 0, 140);

        $fullAgentPrompt = <<<PROMPT
Execute o ciclo de gestão e produção automatizada para o negócio **{$business->name}** ({$business->category}).

### 1. CONTAS VINCULADAS DO NEGÓCIO (PARA GESTÃO E CTAs):
{$accountsText}

### 2. PARÂMETROS OPERACIONAIS DO NEGÓCIO:
- **Nicho / Foco:** {$niche}
- **Público-Alvo:** {$audience}
- **Meta Diária de Entregas:** {$goalCount}
- **Comissão Mínima Alvo:** {$minComm}%
- **Faixa de Preço Ideal:** {$priceRange}
- **Tom de Voz:** {$tone}
- **CTA Obrigatório:** {$cta}
- **Regras Específicas do Agente:** {$rules}
PROMPT;

        if ($customInstruction) {
            $fullAgentPrompt .= "\n\n### 3. ORDEM ESPECÍFICA DESTA EXECUÇÃO:\n{$customInstruction}\n";
        } else {
            $fullAgentPrompt .= "\n\n### 3. ENTREGÁVEIS EXIGIDOS AGORA:\n"
                . "1. **Pesquisa em Tempo Real:** Levante oportunidades/produtos/temas quentes alinhados ao nicho ({$niche}) e faixa de preço ({$priceRange}).\n"
                . "2. **Roteiros / Conteúdos Prontos:** Crie os roteiros/copies prontos para gravação/publicação nas contas acima ({$accountsText}), aplicando gancho nos primeiros 2 segundos e o CTA configurado (`{$cta}`).\n"
                . "3. **Plano de Publicação & Hashtags:** Horários sugeridos, legendas e checklist de conversão.";
        }

        $taskType = ($params['pipeline_mode'] ?? '') === 'tiktok_video_pipeline'
            ? 'tiktok_video_pipeline'
            : 'research_and_execution';

        $task = Task::create([
            'business_id' => $business->id,
            'agent_name' => $agentName,
            'title' => $objectiveTitle,
            'type' => $taskType,
            'status' => 'pending',
            'payload' => [
                'prompt' => $fullAgentPrompt,
                'provider' => $provider,
                'business_slug' => $business->slug,
                'automation_params' => $params,
                'accounts' => $accounts,
            ],
            'estimated_cost_brl' => 0.00,
        ]);

        // Update last_automated_run_at
        $params['last_automated_run_at'] = now()->toIso8601String();
        $settings = is_array($business->settings) ? $business->settings : [];
        $settings['automation_params'] = $params;
        $business->settings = $settings;
        if (Schema::hasColumn('businesses', 'automation_params')) {
            $business->automation_params = $params;
        }
        $business->save();

        try {
            Redis::lpush('empire:jeffrey:tasks', json_encode([
                'id' => (string) $task->id,
                'title' => $task->title,
                'type' => $task->type,
                'agent_name' => $task->agent_name,
                'business_id' => $business->id,
                'payload' => array_merge($task->payload ?? [], [
                    'task_id' => $task->id,
                ]),
                'created_at' => now()->toIso8601String(),
            ]));
        } catch (Throwable $e) {
            Log::warning("Redis push deferred for business automation task #{$task->id}: " . $e->getMessage());
        }

        return response()->json([
            'success' => true,
            'message' => "Ciclo automatizado de {$business->name} iniciado pelo {$agentName} (Tarefa #{$task->id})!",
            'task' => $task,
            'business' => $business->fresh(),
        ], 201);
    }

    /**
     * Synchronize business accounts and parameters into JeffreyMemory so Jeffrey always knows them in chat & worker.
     */
    protected function syncBusinessMemoryForJeffrey(Business $business): void
    {
        try {
            $accounts = $business->accounts_list;
            $params = $business->automation_config;

            $accSummary = collect($accounts)->map(function ($a) {
                return ($a['platform'] ?? 'Conta') . ': ' . ($a['handle'] ?? '') . ' (' . ($a['affiliate_showcase_url'] ?? $a['account_id'] ?? '') . ')';
            })->implode(' | ');

            $content = sprintf(
                "Negócio [%s - #%s] (%s) | Status: %s | Teto: R$ %s | Contas: [%s] | Nicho: %s | Meta/dia: %s | CTA: %s | Regras: %s",
                $business->name,
                $business->slug,
                $business->category,
                $business->status,
                $business->budget_limit_brl,
                $accSummary ?: 'Sem contas',
                $params['niche'] ?? '-',
                $params['daily_deliverables_goal'] ?? '-',
                $params['cta_template'] ?? '-',
                $params['custom_prompt_rules'] ?? '-'
            );

            JeffreyMemory::updateOrCreate(
                ['key' => "business_config_{$business->slug}"],
                [
                    'business_id' => $business->id,
                    'category' => 'context',
                    'content' => $content,
                    'metadata' => [
                        'accounts' => $accounts,
                        'automation_params' => $params,
                    ],
                    'is_active' => true,
                ]
            );
        } catch (Throwable $e) {
            Log::warning("Could not sync business memory for {$business->slug}: " . $e->getMessage());
        }
    }

    /**
     * Store and provision new business (used by Business Factory).
     */
    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'category' => 'required|string|max:255',
            'description' => 'nullable|string',
            'template_used' => 'nullable|string',
            'budget_limit_brl' => 'nullable|numeric|min:0|max:200',
            'accounts' => 'nullable|array',
            'automation_params' => 'nullable|array',
        ]);

        $slug = Str::slug($validated['name']);
        if ($slug === '') {
            $slug = 'negocio-' . Str::lower(Str::random(6));
        }

        $originalSlug = $slug;
        $counter = 1;
        while (Business::where('slug', $slug)->exists()) {
            $slug = "{$originalSlug}-{$counter}";
            $counter++;
        }

        $storagePath = "businesses/{$slug}";
        $fullPath = storage_path($storagePath);

        $directoriesCreated = false;
        $fsError = null;
        try {
            foreach (['assets', 'output', 'scripts', 'logs'] as $dir) {
                if (!File::isDirectory("{$fullPath}/{$dir}")) {
                    File::makeDirectory("{$fullPath}/{$dir}", 0775, true);
                }
            }

            $readmeContent = "# {$validated['name']}\n\n"
                . "> **Categoria:** {$validated['category']}\n"
                . "> **Criado em:** " . date('Y-m-d H:i:s') . "\n\n"
                . "## Proposta de Valor\n"
                . ($validated['description'] ?? 'Negócio digital provisionado pelo SpirandeliEmpire OS Business Factory.') . "\n\n"
                . "## Diretrizes Operacionais\n"
                . "- Orçamento Máximo Alocado: R$ " . ($validated['budget_limit_brl'] ?? '50.00') . "/mês\n"
                . "- Isolamento de armazenamento garantido em `{$storagePath}`\n";

            File::put($fullPath . '/README.md', $readmeContent);
            $directoriesCreated = true;
        } catch (Throwable $e) {
            $fsError = $e->getMessage();
            Log::warning("Business Factory: falha ao criar diretórios em {$fullPath}: {$fsError}");
        }

        $defaultAccounts = $validated['accounts'] ?? [];
        $defaultAutomation = array_merge([
            'auto_enabled' => true,
            'frequency' => 'daily',
            'assigned_agent' => 'Research Agent',
            'niche' => $validated['category'],
            'target_audience' => 'Público brasileiro',
            'daily_deliverables_goal' => 5,
            'min_commission_percent' => 10,
            'price_range_brl' => 'R$ 29,90 a R$ 149,90',
            'tone_of_voice' => 'Dinâmico, persuasivo e direto',
            'cta_template' => 'Link na bio / Clique no carrinho!',
            'pipeline_mode' => 'research_and_script',
            'custom_prompt_rules' => $validated['description'] ?? '',
        ], $validated['automation_params'] ?? []);

        try {
            $business = DB::transaction(function () use ($validated, $slug, $storagePath, $directoriesCreated, $fsError, $defaultAccounts, $defaultAutomation) {
                $createPayload = [
                    'name' => $validated['name'],
                    'slug' => $slug,
                    'category' => $validated['category'],
                    'description' => $validated['description'] ?? null,
                    'template_used' => $validated['template_used'] ?? 'custom',
                    'storage_path' => $storagePath,
                    'budget_limit_brl' => $validated['budget_limit_brl'] ?? 50.00,
                    'status' => 'active',
                    'settings' => [
                        'accounts' => $defaultAccounts,
                        'automation_params' => $defaultAutomation,
                    ],
                ];
                if (Schema::hasColumn('businesses', 'accounts')) {
                    $createPayload['accounts'] = $defaultAccounts;
                }
                if (Schema::hasColumn('businesses', 'automation_params')) {
                    $createPayload['automation_params'] = $defaultAutomation;
                }

                $business = Business::create($createPayload);

                Task::create([
                    'business_id' => $business->id,
                    'agent_name' => 'Business Agent',
                    'title' => "Estruturação inicial de {$business->name}",
                    'type' => 'provisioning',
                    'status' => $directoriesCreated ? 'completed' : 'failed',
                    'payload' => ['category' => $business->category, 'storage' => $storagePath],
                    'result' => ['directories_created' => $directoriesCreated, 'readme' => $directoriesCreated, 'error' => $fsError],
                    'completed_at' => now(),
                ]);

                return $business;
            });

            $this->syncBusinessMemoryForJeffrey($business);
        } catch (Throwable $e) {
            Log::error('Business Factory: falha ao persistir negócio', [
                'slug' => $slug,
                'exception' => get_class($e),
                'message' => $e->getMessage(),
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Falha ao registrar o negócio no banco de dados.',
                'error' => config('app.debug') ? $e->getMessage() : 'Veja storage/logs/laravel.log para detalhes.',
            ], 500);
        }

        return response()->json([
            'success' => true,
            'business' => $business->fresh(),
            'message' => $directoriesCreated
                ? "Negócio {$business->name} provisionado com sucesso!"
                : "Negócio {$business->name} registrado, mas a estrutura de pastas não pôde ser criada (verifique permissões de storage/).",
        ], 201);
    }

    /**
     * Update business status (active, paused, archived).
     */
    public function updateStatus(Request $request, int $id): JsonResponse
    {
        $business = Business::findOrFail($id);
        $request->validate(['status' => 'required|in:active,paused,provisioning,archived']);

        $business->status = $request->input('status');
        $business->save();

        $this->syncBusinessMemoryForJeffrey($business);

        return response()->json([
            'success' => true,
            'business' => $business,
        ]);
    }

    /**
     * Delete/archive business.
     */
    public function destroy(int $id): JsonResponse
    {
        $business = Business::findOrFail($id);
        $business->delete();

        return response()->json([
            'success' => true,
            'message' => "Negócio {$business->name} removido do sistema.",
        ]);
    }
}
