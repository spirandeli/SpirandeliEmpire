<?php

namespace App\Services;

use App\Models\JeffreyMemory;
use App\Models\User;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Redis;

class AiGatewayService
{
    protected GeminiClientService $gemini;
    protected OpenAiClientService $openai;
    protected OllamaClientService $ollama;
    protected BudgetGuardService $budget;
    protected TokenBudgetManagerService $tokenManager;

    protected string $defaultStrategy;
    protected array $fallbackOrder;

    public function __construct(
        GeminiClientService $gemini,
        OpenAiClientService $openai,
        OllamaClientService $ollama,
        BudgetGuardService $budget,
        TokenBudgetManagerService $tokenManager
    ) {
        $this->gemini = $gemini;
        $this->openai = $openai;
        $this->ollama = $ollama;
        $this->budget = $budget;
        $this->tokenManager = $tokenManager;

        $this->defaultStrategy = config('ai.default_provider', env('AI_PROVIDER', 'gemini'));
        $this->fallbackOrder = config('ai.fallback_order', ['gemini', 'openai', 'ollama']);
    }

    /**
     * Load the persisted AI Availability & Access Control configuration.
     */
    public function getAiAvailabilityConfig(): array
    {
        $stored = [];
        try {
            $raw = Redis::get('empire:ai:config');
            if ($raw) {
                $stored = json_decode($raw, true) ?: [];
            }
        } catch (\Throwable $e) {}

        if (empty($stored)) {
            try {
                $mem = JeffreyMemory::where('category', 'system_ai_keys')->where('is_active', true)->first();
                if ($mem && !empty($mem->content)) {
                    $stored = json_decode($mem->content, true) ?: [];
                }
            } catch (\Throwable $e) {}
        }

        $firstCommander = null;
        try {
            $firstCommander = User::orderBy('id', 'asc')->first();
        } catch (\Throwable $e) {}

        $defaultOwnerId = $firstCommander?->id ?? 1;
        $defaultOwnerEmail = strtolower(trim($firstCommander?->email ?: env('ADMIN_EMAIL', 'admin@spirandeliempire.tech')));

        $enabledProviders = array_merge([
            'ollama' => true,
            'gemini' => true,
            'openai' => true,
            'hybrid' => true,
        ], is_array($stored['enabled_providers'] ?? null) ? $stored['enabled_providers'] : []);

        $enabledCapabilities = array_merge([
            'cooperative_pipeline' => true,
            'voice_and_attachments' => true,
            'live_web_search' => true,
        ], is_array($stored['enabled_capabilities'] ?? null) ? $stored['enabled_capabilities'] : []);

        $ownerUserId = (int) ($stored['gemini_owner_user_id'] ?? $defaultOwnerId);
        $ownerEmail = strtolower(trim((string) ($stored['gemini_owner_email'] ?? $defaultOwnerEmail)));

        $allowedUserIds = $stored['gemini_allowed_user_ids'] ?? [$ownerUserId];
        if (!is_array($allowedUserIds)) {
            $allowedUserIds = [$ownerUserId];
        }
        $allowedUserIds = array_values(array_unique(array_map('intval', array_merge([$ownerUserId], $allowedUserIds))));

        $allowedEmails = $stored['gemini_allowed_emails'] ?? [$ownerEmail];
        if (!is_array($allowedEmails)) {
            $allowedEmails = [$ownerEmail];
        }
        $allowedEmails = array_values(array_unique(array_map(fn($e) => strtolower(trim((string) $e)), array_merge([$ownerEmail], $allowedEmails))));

        return [
            'enabled_providers' => [
                'ollama' => (bool) ($enabledProviders['ollama'] ?? true),
                'gemini' => (bool) ($enabledProviders['gemini'] ?? true),
                'openai' => (bool) ($enabledProviders['openai'] ?? true),
                'hybrid' => (bool) ($enabledProviders['hybrid'] ?? true),
            ],
            'enabled_capabilities' => [
                'cooperative_pipeline' => (bool) ($enabledCapabilities['cooperative_pipeline'] ?? true),
                'voice_and_attachments' => (bool) ($enabledCapabilities['voice_and_attachments'] ?? true),
                'live_web_search' => (bool) ($enabledCapabilities['live_web_search'] ?? true),
            ],
            'gemini_access_policy' => $stored['gemini_access_policy'] ?? 'all_users', // all_users | owner_only | selected_users
            'gemini_owner_user_id' => $ownerUserId,
            'gemini_owner_email' => $ownerEmail,
            'gemini_allowed_user_ids' => $allowedUserIds,
            'gemini_allowed_emails' => $allowedEmails,
            'default_provider_for_others' => $stored['default_provider_for_others'] ?? 'ollama',
        ];
    }

    /**
     * Determine if a given user is the Primary Owner/Commander login.
     */
    public function isOwnerUser(?User $user = null): bool
    {
        $user = $user ?: request()?->user();
        if (!$user) {
            return false;
        }
        $cfg = $this->getAiAvailabilityConfig();
        $email = strtolower(trim((string) $user->email));
        $role = strtolower(trim((string) ($user->role ?? '')));
        return (int) $user->id === 1
            || (int) $user->id === (int) $cfg['gemini_owner_user_id']
            || ($email !== '' && $email === $cfg['gemini_owner_email'])
            || in_array($role, ['admin', 'commander', 'owner'], true);
    }

    /**
     * Check whether the given user login is allowed to use Google Gemini.
     */
    public function canUserAccessGemini(?User $user = null): bool
    {
        $cfg = $this->getAiAvailabilityConfig();
        if (empty($cfg['enabled_providers']['gemini'])) {
            return false;
        }

        $user = $user ?: request()?->user();
        if (!$user) {
            return true;
        }

        $policy = $cfg['gemini_access_policy'] ?? 'all_users';
        if ($policy === 'all_users') {
            return true;
        }

        if ($this->isOwnerUser($user)) {
            return true;
        }

        if ($policy === 'selected_users') {
            $email = strtolower(trim((string) $user->email));
            if (in_array((int) $user->id, $cfg['gemini_allowed_user_ids'], true)) {
                return true;
            }
            if ($email !== '' && in_array($email, $cfg['gemini_allowed_emails'], true)) {
                return true;
            }
        }

        return true;
    }

    /**
     * Check whether a specific provider is enabled and permitted for the active user login.
     */
    public function canUserAccessProvider(?User $user, string $provider): bool
    {
        $cfg = $this->getAiAvailabilityConfig();
        $user = $user ?: request()?->user();

        return match ($provider) {
            'gemini', 'google', 'google_gemini' => $this->canUserAccessGemini($user),
            'openai' => !empty($cfg['enabled_providers']['openai']),
            'ollama', 'llama' => !empty($cfg['enabled_providers']['ollama']),
            'hybrid', 'cooperative', 'auto' => !empty($cfg['enabled_providers']['hybrid']),
            default => true,
        };
    }

    /**
     * Check if Gemini or OpenAI API key is configured AND accessible to the current user for task execution.
     */
    public function isCloudExecutorConfigured(?User $user = null): bool
    {
        $cfg = $this->getAiAvailabilityConfig();
        $geminiReady = $this->gemini->isConfigured() && $this->canUserAccessGemini($user);
        $openaiReady = $this->openai->isConfigured() && !empty($cfg['enabled_providers']['openai']);

        return $geminiReady || $openaiReady;
    }

    /**
     * Two-stage cooperative pipeline:
     * 1. Llama Local (Ollama) reads and analyzes the raw context/data/files.
     * 2. Google Gemini (if user login is authorized) or OpenAI Chat executes the final task/action.
     */
    public function analyzeWithLlamaThenExecute(
        string $rawContextToAnalyze,
        string $executionPrompt,
        ?string $systemPrompt = null,
        ?string $preferredExecutor = null,
        ?User $user = null
    ): array {
        $user = $user ?: request()?->user();
        $cfg = $this->getAiAvailabilityConfig();
        $llamaAnalysis = null;
        $llamaModel = null;
        $llamaLatency = 0;

        // Stage 1: Llama Local reads and analyzes the context if cloud executor is available and cooperative pipeline is enabled
        if ($this->isCloudExecutorConfigured($user) && !empty($cfg['enabled_capabilities']['cooperative_pipeline']) && !empty(trim($rawContextToAnalyze))) {
            $analysisPrompt = "Leia e analise de forma objetiva os seguintes dados do sistema/negócio, extraindo os fatos principais, métricas, contas e pontos críticos em até 6 tópicos curtos:\n\n" . $rawContextToAnalyze;
            $analysisSystem = "Você é o módulo Analista Local (Llama) do SpirandeliEmpire OS. Sua única função é ler, filtrar e resumir dados brutos para preparar a execução do agente principal.";

            $llamaRes = $this->ollama->generate($analysisPrompt, $analysisSystem);
            if (!empty($llamaRes['success']) && !empty($llamaRes['response'])) {
                $llamaAnalysis = trim($llamaRes['response']);
                $llamaModel = $llamaRes['model'] ?? 'ollama_local';
                $llamaLatency = $llamaRes['latency_ms'] ?? 0;
                $this->tokenManager->recordUsage('ollama_llama', $this->tokenManager->estimateTokens($analysisPrompt . ' ' . $llamaAnalysis));
            }
        }

        // Stage 2: Execute final task on Gemini (if user login is authorized) or OpenAI Chat (or fallback to Llama)
        $enrichedPrompt = $executionPrompt;
        if ($llamaAnalysis) {
            $enrichedPrompt = "### [LEITURA E ANÁLISE PRÉVIA DO LLAMA LOCAL ({$llamaModel})]:\n{$llamaAnalysis}\n\n---\n### [TAREFA PARA EXECUÇÃO]:\n{$executionPrompt}";
        }

        $canGemini = $this->gemini->isConfigured() && $this->canUserAccessGemini($user);
        $canOpenAi = $this->openai->isConfigured() && !empty($cfg['enabled_providers']['openai']);

        $executor = ($preferredExecutor && !in_array($preferredExecutor, ['hybrid', 'auto'], true))
            ? $preferredExecutor
            : ($canGemini ? 'gemini' : ($canOpenAi ? 'openai' : 'ollama'));

        if ($executor === 'gemini' && !$canGemini) {
            $executor = $canOpenAi ? 'openai' : ($cfg['default_provider_for_others'] ?? 'ollama');
        }

        $execResult = $this->generate($enrichedPrompt, $systemPrompt, $executor, null, 'execute_task', [], $user);
        if ($llamaAnalysis) {
            $execResult['cooperative_pipeline'] = true;
            $execResult['analyzer_provider'] = 'ollama_llama';
            $execResult['analyzer_model'] = $llamaModel;
            $execResult['analyzer_latency_ms'] = $llamaLatency;
            $execResult['llama_analysis_summary'] = $llamaAnalysis;
        }

        return $execResult;
    }

    /**
     * Generate text through the intelligent multi-provider gateway with role division and login-level Gemini access control.
     */
    public function generate(
        string $prompt,
        ?string $systemPrompt = null,
        ?string $preferredProvider = null,
        ?string $model = null,
        ?string $taskRole = null,
        array $inlineMedia = [],
        ?User $user = null,
        array $conversationTurns = []
    ): array {
        $user = $user ?: request()?->user();
        $cfg = $this->getAiAvailabilityConfig();
        $canGemini = $this->gemini->isConfigured() && $this->canUserAccessGemini($user);
        $canOpenAi = $this->openai->isConfigured() && !empty($cfg['enabled_providers']['openai']);
        $canOllama = !empty($cfg['enabled_providers']['ollama']);

        // 1. Estimate tokens prior to dispatch
        $fullText = $prompt . ($systemPrompt ? ' ' . $systemPrompt : '');
        $estimatedInputTokens = $this->tokenManager->estimateTokens($fullText);

        // Enforce login restriction if user explicitly requested 'gemini' without authorization
        $restrictionNotice = null;
        if (in_array($preferredProvider, ['gemini', 'google'], true) && !$this->canUserAccessGemini($user)) {
            $preferredProvider = $cfg['default_provider_for_others'] ?? 'ollama';
            $restrictionNotice = 'Acesso ao Google Gemini restrito exclusivamente ao login do Comandante Principal — redirecionado para ' . strtoupper($preferredProvider) . '.';
        }

        // Enforce enabled_providers toggles
        if ($preferredProvider === 'openai' && !$canOpenAi) {
            $preferredProvider = $canGemini ? 'gemini' : 'ollama';
        } elseif (in_array($preferredProvider, ['ollama', 'llama'], true) && !$canOllama) {
            $preferredProvider = $canGemini ? 'gemini' : ($canOpenAi ? 'openai' : 'ollama');
        }

        // 2. Role & Token-based task delegation analysis
        if (!empty($inlineMedia) && $canGemini) {
            $delegation = [
                'provider' => 'gemini',
                'tier' => 'multimodal',
                'role' => 'execute_task',
                'reason' => 'Anexo multimodal (imagem/áudio/documento) detectado — processado pelo Google Gemini 3.8 Flash.',
                'forced_delegation' => true,
            ];
        } else {
            $delegation = $this->tokenManager->determineOptimalProvider(
                $estimatedInputTokens,
                $preferredProvider,
                $prompt,
                $taskRole,
                $canGemini,
                $canOpenAi
            );
        }

        if ($restrictionNotice) {
            $delegation['reason'] = $restrictionNotice;
        }

        $strategy = $delegation['provider'];
        $effectiveStrategy = $preferredProvider && !in_array($preferredProvider, ['hybrid', 'auto']) && !$delegation['forced_delegation']
            ? $preferredProvider
            : $strategy;

        // Final safety guard: never execute 'gemini' if current user is not authorized for Gemini
        if ($effectiveStrategy === 'gemini' && !$canGemini) {
            $effectiveStrategy = $canOpenAi ? 'openai' : 'ollama';
        }

        $result = $this->executeStrategy($effectiveStrategy, $prompt, $systemPrompt, $model, $inlineMedia, $user, $conversationTurns);

        // 3. Post-execution token tracking & metadata enrichment
        $outputTokens = isset($result['tokens']['candidates']) 
            ? $result['tokens']['candidates'] 
            : $this->tokenManager->estimateTokens($result['response'] ?? '');
            
        $totalTokens = $estimatedInputTokens + $outputTokens;

        if ($result['success']) {
            $providerKey = match ($result['provider'] ?? '') {
                'google_gemini' => 'google_gemini',
                'openai' => 'openai',
                default => 'ollama_llama',
            };
            $this->tokenManager->recordUsage($providerKey, $totalTokens);
        }

        $result['token_metrics'] = [
            'estimated_input_tokens' => $estimatedInputTokens,
            'output_tokens' => $outputTokens,
            'total_tokens' => $totalTokens,
            'tier' => $delegation['tier'],
            'role' => $delegation['role'] ?? 'execute_task',
            'delegation_reason' => $delegation['reason'],
            'forced_delegation' => $delegation['forced_delegation'],
        ];

        return $result;
    }

    protected function executeStrategy(
        string $strategy,
        string $prompt,
        ?string $systemPrompt,
        ?string $model,
        array $inlineMedia = [],
        ?User $user = null,
        array $conversationTurns = []
    ): array {
        $cfg = $this->getAiAvailabilityConfig();
        $canGemini = $this->gemini->isConfigured() && $this->canUserAccessGemini($user);
        $canOpenAi = $this->openai->isConfigured() && !empty($cfg['enabled_providers']['openai']);

        // Direct Provider: Gemini (only if user login is authorized)
        if ($strategy === 'gemini') {
            if (!$this->canUserAccessGemini($user)) {
                return [
                    'success' => false,
                    'error' => 'Acesso ao Google Gemini restrito ao login do Comandante Principal.',
                    'provider' => 'google_gemini',
                ];
            }
            $res = $this->gemini->generate($prompt, $systemPrompt, $model, $inlineMedia, $conversationTurns);
            if ($res['success']) {
                $res['provider_name'] = 'Google Gemini 3.8 Flash';
                return $res;
            }
            return [
                'success' => false,
                'error' => 'Google Gemini 3.8 Flash: ' . ($res['error'] ?? 'falha na comunicação com a API do Google.'),
                'provider' => 'google_gemini',
                'fallback_used' => false,
            ];
        }

        // Direct Provider: OpenAI
        if ($strategy === 'openai') {
            if (!$canOpenAi) {
                return $this->fallbackToLocal($prompt, $systemPrompt, 'OpenAI desativado ou sem chave.');
            }
            $res = $this->openai->generate($prompt, $systemPrompt, $model, $conversationTurns);
            if ($res['success']) {
                $res['provider_name'] = 'OpenAI (Credits/Plan)';
                return $res;
            }
            return $this->fallbackToLocal($prompt, $systemPrompt, 'OpenAI falhou: ' . ($res['error'] ?? 'desconhecido'));
        }

        // Direct Provider: Llama Local
        if ($strategy === 'ollama' || $strategy === 'llama') {
            $res = $this->ollama->generate($prompt, $systemPrompt, $model);
            if ($res['success']) {
                $res['provider_name'] = 'Llama Local (Ollama - 100% Free)';
                return $res;
            }
            // If local fails, attempt Gemini as emergency fallback ONLY if user is authorized for Gemini
            if ($canGemini) {
                Log::warning('Llama Local indisponível. Tentando Google Gemini como emergência...');
                $geminiRes = $this->gemini->generate($prompt, $systemPrompt, null, [], $conversationTurns);
                if ($geminiRes['success']) {
                    $geminiRes['provider_name'] = 'Google Gemini (Fallback de Emergência)';
                    $geminiRes['fallback_used'] = true;
                    return $geminiRes;
                }
            }
            return $res;
        }

        // HYBRID INTELLIGENT ROUTING
        $errors = [];

        // 1. Google Gemini (only if user is authorized & enabled)
        if ($canGemini) {
            $geminiRes = $this->gemini->generate($prompt, $systemPrompt, $model, $inlineMedia, $conversationTurns);
            if ($geminiRes['success']) {
                $geminiRes['provider_name'] = 'Google Gemini 3.8 Flash';
                $geminiRes['routing'] = 'primary_free_tier';
                return $geminiRes;
            }
            $errors[] = 'Gemini: ' . ($geminiRes['error'] ?? 'Erro desconhecido');
        } elseif (!$this->canUserAccessGemini($user)) {
            $errors[] = 'Gemini: Restrito ao login do Comandante';
        } else {
            $errors[] = 'Gemini: Key não configurada';
        }

        // 2. OpenAI
        if ($canOpenAi) {
            $openaiRes = $this->openai->generate($prompt, $systemPrompt, null, $conversationTurns);
            if ($openaiRes['success']) {
                $openaiRes['provider_name'] = 'OpenAI (Fallback Tier)';
                $openaiRes['routing'] = 'secondary_openai_fallback';
                $openaiRes['fallback_reason'] = implode('; ', $errors);
                return $openaiRes;
            }
            $errors[] = 'OpenAI: ' . ($openaiRes['error'] ?? 'Erro desconhecido');
        }

        // 3. Llama Local
        $ollamaRes = $this->ollama->generate($prompt, $systemPrompt);
        if ($ollamaRes['success']) {
            $ollamaRes['provider_name'] = 'Llama Local (Ollama - 100% Free & Offline)';
            $ollamaRes['routing'] = 'local_llama_fallback';
            $ollamaRes['fallback_used'] = true;
            $ollamaRes['fallback_reason'] = implode(' | ', $errors);
            return $ollamaRes;
        }

        return [
            'success' => false,
            'error' => 'Nenhum provedor de IA respondeu com sucesso: ' . implode(' | ', $errors) . ' | Ollama Local: ' . ($ollamaRes['error'] ?? 'Indisponível'),
            'provider' => 'none',
        ];
    }

    protected function fallbackToLocal(string $prompt, ?string $systemPrompt, string $reason): array
    {
        Log::warning("Ativando fallback imediato para Llama Local: {$reason}");
        $localRes = $this->ollama->generate($prompt, $systemPrompt);
        if ($localRes['success']) {
            $localRes['provider_name'] = 'Llama Local (Fallback de Segurança)';
            $localRes['fallback_used'] = true;
            $localRes['fallback_reason'] = $reason;
            return $localRes;
        }

        return [
            'success' => false,
            'error' => "Falha no provedor primário ({$reason}) e o fallback local Llama também falhou: " . ($localRes['error'] ?? 'Indisponível'),
            'provider' => 'none',
        ];
    }

    /**
     * Get detailed status of all AI providers, availability catalog, and login-specific permissions.
     */
    public function getProvidersStatus(?User $currentUser = null): array
    {
        $currentUser = $currentUser ?: request()?->user();
        $ollamaModels = $this->ollama->listModels();
        $tokenStats = $this->tokenManager->getTokenStats();
        $availabilityConfig = $this->getAiAvailabilityConfig();

        $canUseGemini = $this->canUserAccessGemini($currentUser);
        $canUseOpenAi = !empty($availabilityConfig['enabled_providers']['openai']);
        $canUseOllama = !empty($availabilityConfig['enabled_providers']['ollama']);
        $canUseHybrid = !empty($availabilityConfig['enabled_providers']['hybrid']);

        $availableSelectorOptions = [];
        if ($canUseHybrid) {
            $availableSelectorOptions[] = [
                'id' => 'hybrid',
                'value' => 'hybrid',
                'label' => $canUseGemini
                    ? '⚡ Cooperativo (Llama Analisa • Gemini Executa)'
                    : '⚡ Automático (IAs Liberadas para seu Perfil)',
                'enabled' => true,
            ];
        }
        if ($canUseOllama) {
            $availableSelectorOptions[] = [
                'id' => 'ollama',
                'value' => 'ollama',
                'label' => '🦙 Llama Local (Leitura & Análise)',
                'enabled' => true,
            ];
        }
        if ($canUseGemini || !empty($availabilityConfig['enabled_providers']['gemini'])) {
            $availableSelectorOptions[] = [
                'id' => 'gemini',
                'value' => 'gemini',
                'label' => '✨ Google Gemini 3.8 Flash (Recomendado)',
                'enabled' => true,
            ];
        }
        if ($canUseOpenAi) {
            $availableSelectorOptions[] = [
                'id' => 'openai',
                'value' => 'openai',
                'label' => '🤖 ChatGPT (Executor OpenAI)',
                'enabled' => true,
            ];
        }
        if (empty($availableSelectorOptions)) {
            $availableSelectorOptions[] = [
                'id' => 'ollama',
                'value' => 'ollama',
                'label' => '🦙 Llama Local (Padrão)',
                'enabled' => true,
            ];
        }

        $registeredUsers = [];
        try {
            $registeredUsers = User::orderBy('id', 'asc')
                ->get(['id', 'name', 'email', 'role'])
                ->map(fn(User $u) => [
                    'id' => $u->id,
                    'name' => $u->name,
                    'email' => $u->email,
                    'role' => $u->role,
                    'is_owner' => $this->isOwnerUser($u),
                    'can_access_gemini' => $this->canUserAccessGemini($u),
                ])
                ->toArray();
        } catch (\Throwable $e) {}

        return [
            'current_strategy' => $this->defaultStrategy,
            'budget_status' => $this->budget->getBudgetStatus(),
            'token_governance' => $tokenStats,
            'availability_config' => $availabilityConfig,
            'user_access' => [
                'current_user_id' => $currentUser?->id,
                'current_user_name' => $currentUser?->name,
                'current_user_email' => $currentUser?->email,
                'is_owner' => $this->isOwnerUser($currentUser),
                'can_use_gemini' => $canUseGemini,
                'can_use_openai' => $canUseOpenAi,
                'can_use_ollama' => $canUseOllama,
                'can_use_hybrid' => $canUseHybrid,
                'available_options' => $availableSelectorOptions,
            ],
            'registered_users' => $registeredUsers,
            'providers' => [
                'google_gemini' => [
                    'name' => 'Google Gemini (AI Studio)',
                    'configured' => $this->gemini->isConfigured(),
                    'enabled' => !empty($availabilityConfig['enabled_providers']['gemini']),
                    'restricted_to_owner' => ($availabilityConfig['gemini_access_policy'] ?? 'owner_only') !== 'all_users',
                    'user_allowed' => $canUseGemini,
                    'default_model' => $this->gemini->getDefaultModel(),
                    'free_tier_eligible' => true,
                    'context_window' => '1.000.000 tokens',
                    'pricing_profile' => 'Free Tier (15 RPM / 1M TPM sem custo) + Créditos',
                    'official_url' => 'https://aistudio.google.com/app/apikey',
                ],
                'openai' => [
                    'name' => 'OpenAI (GPT-4o Mini / Plans)',
                    'configured' => $this->openai->isConfigured(),
                    'enabled' => $canUseOpenAi,
                    'default_model' => $this->openai->getDefaultModel(),
                    'context_window' => '128.000 tokens',
                    'pricing_profile' => 'Créditos Gratuitos de Boas-Vindas ou Pay-As-You-Go',
                    'official_url' => 'https://platform.openai.com/api-keys',
                ],
                'ollama_llama' => [
                    'name' => 'Llama Local (Ollama)',
                    'configured' => true,
                    'enabled' => $canUseOllama,
                    'connected' => !empty($ollamaModels),
                    'default_model' => $this->ollama->getDefaultModel(),
                    'context_window' => '8.192 tokens (Otimizado para 8GB VPS)',
                    'installed_models' => array_map(fn($m) => $m['name'] ?? '', $ollamaModels),
                    'pricing_profile' => '100% Gratuito & Local (CPU ou GPU do VPS)',
                    'offline_ready' => true,
                ],
            ],
            'cooperative_mode_active' => $this->isCloudExecutorConfigured($currentUser),
            'hybrid_routing_pipeline' => [
                'role_analysis' => 'Llama Local via Ollama -> Lê, filtra e analisa arquivos, métricas, logs e dados brutos da web (Custo R$ 0,00)',
                'role_execution' => 'Google Gemini (Restrito ao Login do Comandante) / OpenAI Chat -> Executa as tarefas finais, roteiros, planos de ação e chamadas de ferramentas',
                'fallback_offline' => 'Llama Local assume 100% para demais perfis ou caso nenhuma chave Cloud esteja configurada',
            ]
        ];
    }

    /**
     * Test connection for a given provider.
     */
    public function testProvider(string $provider, ?User $user = null): array
    {
        if (in_array($provider, ['gemini', 'google'], true) && !$this->canUserAccessGemini($user)) {
            return [
                'success' => false,
                'message' => 'Acesso negado: O uso do Google Gemini está restrito exclusivamente ao login principal do Comandante.',
            ];
        }

        return match ($provider) {
            'gemini', 'google' => $this->gemini->testConnection(),
            'openai' => $this->openai->testConnection(),
            'ollama', 'llama' => $this->ollama->testConnection(),
            default => [
                'success' => false,
                'message' => "Provedor '{$provider}' desconhecido. Escolha entre: gemini, openai, ollama."
            ]
        };
    }

    public function getTokenManager(): TokenBudgetManagerService
    {
        return $this->tokenManager;
    }
}
