<?php

namespace App\Http\Controllers\Api;

use App\Models\JeffreyMemory;
use App\Services\AiGatewayService;
use App\Services\TokenBudgetManagerService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Redis;

class AiEngineController extends Controller
{
    /**
     * Get consolidated status of all AI engines, cooperative role division, token governance, and user-level access permissions.
     */
    public function status(Request $request, AiGatewayService $aiGateway): JsonResponse
    {
        $status = $aiGateway->getProvidersStatus($request->user());

        return response()->json(array_merge($status, [
            'tts_engine' => 'Piper (Local CPU pt_BR-faber-medium)',
            'video_engine' => 'FFmpeg + Anti-Ban Pipeline',
            'gpu_mode' => env('GPU_EXECUTION_MODE', 'cpu_only'),
            'gpu_remote_enabled' => (bool) env('GPU_REMOTE_ENABLED', false),
        ]));
    }

    /**
     * Load existing dynamic AI config from Redis / PostgreSQL.
     */
    protected function loadStoredAiConfig(): array
    {
        $existingConfig = [];
        try {
            $raw = Redis::get('empire:ai:config');
            if ($raw) {
                $existingConfig = json_decode($raw, true) ?: [];
            }
        } catch (\Throwable $e) {}

        if (empty($existingConfig)) {
            try {
                $mem = JeffreyMemory::where('category', 'system_ai_keys')->where('is_active', true)->first();
                if ($mem && !empty($mem->content)) {
                    $existingConfig = json_decode($mem->content, true) ?: [];
                }
            } catch (\Throwable $e) {}
        }

        return is_array($existingConfig) ? $existingConfig : [];
    }

    /**
     * Save dynamic AI config to Redis and PostgreSQL.
     */
    protected function persistAiConfig(array $config): void
    {
        $config['updated_at'] = now()->toIso8601String();

        try {
            Redis::set('empire:ai:config', json_encode($config));
        } catch (\Throwable $e) {}

        try {
            JeffreyMemory::updateOrCreate(
                ['category' => 'system_ai_keys', 'business_id' => null],
                [
                    'key' => 'global_ai_config',
                    'content' => json_encode($config),
                    'is_active' => true,
                ]
            );
        } catch (\Throwable $e) {}
    }

    /**
     * Save Gemini and/or OpenAI API keys dynamically (restricted to the primary Commander login).
     */
    public function configureKeys(Request $request, AiGatewayService $aiGateway): JsonResponse
    {
        $user = $request->user();
        if ($user && !$aiGateway->isOwnerUser($user)) {
            return response()->json([
                'success' => false,
                'message' => 'Acesso negado: Somente o login principal do Comandante pode alterar as chaves de API.',
            ], 403);
        }

        $validated = $request->validate([
            'gemini_api_key' => 'nullable|string|max:255',
            'openai_api_key' => 'nullable|string|max:255',
        ]);

        $existingConfig = $this->loadStoredAiConfig();

        if (array_key_exists('gemini_api_key', $validated) && $validated['gemini_api_key'] !== null && trim($validated['gemini_api_key']) !== '') {
            $existingConfig['gemini_api_key'] = trim($validated['gemini_api_key']);
        }
        if (array_key_exists('openai_api_key', $validated) && $validated['openai_api_key'] !== null && trim($validated['openai_api_key']) !== '') {
            $existingConfig['openai_api_key'] = trim($validated['openai_api_key']);
        }
        $existingConfig['cooperative_mode'] = 'llama_analyze_cloud_execute';

        // Bind Gemini owner to the Commander's login automatically when saving key
        if ($user) {
            $existingConfig['gemini_owner_user_id'] = (int) $user->id;
            $existingConfig['gemini_owner_email'] = strtolower(trim((string) $user->email));
            if (empty($existingConfig['gemini_access_policy'])) {
                $existingConfig['gemini_access_policy'] = 'owner_only';
            }
        }

        $this->persistAiConfig($existingConfig);

        // Best-effort update of .env if writable
        try {
            $envPath = base_path('.env');
            if (File::exists($envPath) && File::isWritable($envPath)) {
                $envContent = File::get($envPath);
                if (!empty($existingConfig['gemini_api_key'])) {
                    if (preg_match('/^GEMINI_API_KEY=/m', $envContent)) {
                        $envContent = preg_replace('/^GEMINI_API_KEY=.*$/m', 'GEMINI_API_KEY=' . $existingConfig['gemini_api_key'], $envContent);
                    } else {
                        $envContent .= "\nGEMINI_API_KEY=" . $existingConfig['gemini_api_key'];
                    }
                }
                if (!empty($existingConfig['openai_api_key'])) {
                    if (preg_match('/^OPENAI_API_KEY=/m', $envContent)) {
                        $envContent = preg_replace('/^OPENAI_API_KEY=.*$/m', 'OPENAI_API_KEY=' . $existingConfig['openai_api_key'], $envContent);
                    } else {
                        $envContent .= "\nOPENAI_API_KEY=" . $existingConfig['openai_api_key'];
                    }
                }
                File::put($envPath, $envContent);
            }
        } catch (\Throwable $e) {}

        $freshGateway = app(AiGatewayService::class);

        return response()->json([
            'success' => true,
            'message' => 'Chaves salvas e vinculadas ao seu login de Comandante! Modo Cooperativo ativo.',
            'status' => $freshGateway->getProvidersStatus($user),
        ]);
    }

    /**
     * Configure which AI types/models are enabled in the Empire OS and restrict Gemini access to the Commander's login.
     */
    public function configureAvailability(Request $request, AiGatewayService $aiGateway): JsonResponse
    {
        $user = $request->user();
        if ($user && !$aiGateway->isOwnerUser($user)) {
            return response()->json([
                'success' => false,
                'message' => 'Acesso negado: Somente o login principal do Comandante pode gerenciar a disponibilidade de IAs.',
            ], 403);
        }

        $validated = $request->validate([
            'enabled_providers' => 'required|array',
            'enabled_providers.ollama' => 'required|boolean',
            'enabled_providers.gemini' => 'required|boolean',
            'enabled_providers.openai' => 'required|boolean',
            'enabled_providers.hybrid' => 'required|boolean',
            'enabled_capabilities' => 'nullable|array',
            'enabled_capabilities.cooperative_pipeline' => 'nullable|boolean',
            'enabled_capabilities.voice_and_attachments' => 'nullable|boolean',
            'enabled_capabilities.live_web_search' => 'nullable|boolean',
            'gemini_access_policy' => 'required|string|in:owner_only,selected_users,all_users',
            'gemini_owner_email' => 'nullable|email',
            'gemini_allowed_user_ids' => 'nullable|array',
            'default_provider_for_others' => 'nullable|string|in:ollama,openai',
        ]);

        // Ensure at least one base provider (ollama, gemini, or openai) remains enabled
        if (
            empty($validated['enabled_providers']['ollama']) &&
            empty($validated['enabled_providers']['gemini']) &&
            empty($validated['enabled_providers']['openai'])
        ) {
            $validated['enabled_providers']['ollama'] = true;
        }

        $existingConfig = $this->loadStoredAiConfig();

        $ownerUserId = $user ? (int) $user->id : (int) ($existingConfig['gemini_owner_user_id'] ?? 1);
        $ownerEmail = strtolower(trim((string) ($validated['gemini_owner_email'] ?? ($user?->email ?: ($existingConfig['gemini_owner_email'] ?? env('ADMIN_EMAIL', 'admin@spirandeliempire.tech'))))));

        $allowedIds = array_map('intval', $validated['gemini_allowed_user_ids'] ?? [$ownerUserId]);
        if (!in_array($ownerUserId, $allowedIds, true)) {
            $allowedIds[] = $ownerUserId;
        }

        $existingConfig['enabled_providers'] = [
            'ollama' => (bool) $validated['enabled_providers']['ollama'],
            'gemini' => (bool) $validated['enabled_providers']['gemini'],
            'openai' => (bool) $validated['enabled_providers']['openai'],
            'hybrid' => (bool) $validated['enabled_providers']['hybrid'],
        ];
        $existingConfig['enabled_capabilities'] = [
            'cooperative_pipeline' => (bool) ($validated['enabled_capabilities']['cooperative_pipeline'] ?? true),
            'voice_and_attachments' => (bool) ($validated['enabled_capabilities']['voice_and_attachments'] ?? true),
            'live_web_search' => (bool) ($validated['enabled_capabilities']['live_web_search'] ?? true),
        ];
        $existingConfig['gemini_access_policy'] = $validated['gemini_access_policy'];
        $existingConfig['gemini_owner_user_id'] = $ownerUserId;
        $existingConfig['gemini_owner_email'] = $ownerEmail;
        $existingConfig['gemini_allowed_user_ids'] = array_values(array_unique($allowedIds));
        $existingConfig['default_provider_for_others'] = $validated['default_provider_for_others'] ?? 'ollama';

        $this->persistAiConfig($existingConfig);

        $freshGateway = app(AiGatewayService::class);

        return response()->json([
            'success' => true,
            'message' => 'Configuração de disponibilidade de IAs e controle de acesso ao Gemini salva com sucesso!',
            'status' => $freshGateway->getProvidersStatus($user),
        ]);
    }

    /**
     * Test connection to a specific provider (gemini, openai, ollama).
     */
    public function testProvider(Request $request, AiGatewayService $aiGateway): JsonResponse
    {
        $request->validate([
            'provider' => 'required|string|in:gemini,google,openai,ollama,llama',
        ]);

        $result = $aiGateway->testProvider($request->input('provider'), $request->user());

        return response()->json($result);
    }

    /**
     * Direct test completion across any provider with role, token measurement, and login access check.
     */
    public function complete(Request $request, AiGatewayService $aiGateway): JsonResponse
    {
        $request->validate([
            'prompt' => 'required|string',
            'provider' => 'nullable|string|in:hybrid,gemini,openai,ollama,llama,cooperative',
            'model' => 'nullable|string',
        ]);

        $user = $request->user();
        $provider = $request->input('provider');
        if ($provider === 'cooperative') {
            $result = $aiGateway->analyzeWithLlamaThenExecute(
                $request->input('prompt'),
                $request->input('prompt'),
                'Você é o motor cooperativo do SpirandeliEmpire OS. Use a análise prévia do Llama para executar a resposta final com precisão.',
                null,
                $user
            );
            return response()->json($result);
        }

        $result = $aiGateway->generate(
            $request->input('prompt'),
            'Você é um assistente de validação do SpirandeliEmpire OS. Responda de forma concisa.',
            $provider,
            $request->input('model'),
            null,
            [],
            $user
        );

        return response()->json($result);
    }

    /**
     * Estimate token size and calculate optimal task delegation (Llama Read/Analyze vs Gemini/Chat Execute).
     */
    public function estimateTokens(Request $request, TokenBudgetManagerService $tokenManager, AiGatewayService $aiGateway): JsonResponse
    {
        $request->validate([
            'text' => 'required|string',
            'preferred_provider' => 'nullable|string',
            'role' => 'nullable|string|in:read_analyze,execute_task',
        ]);

        $text = $request->input('text');
        $estimatedTokens = $tokenManager->estimateTokens($text);
        $charLength = mb_strlen($text, 'UTF-8');
        $wordCount = count(preg_split('/\s+/u', trim($text), -1, PREG_SPLIT_NO_EMPTY));
        $status = $aiGateway->getProvidersStatus($request->user());
        $geminiAllowedAndConfigured = (bool) (($status['providers']['google_gemini']['configured'] ?? false) && ($status['user_access']['can_use_gemini'] ?? false));
        $openaiAllowedAndConfigured = (bool) (($status['providers']['openai']['configured'] ?? false) && ($status['user_access']['can_use_openai'] ?? false));

        $delegation = $tokenManager->determineOptimalProvider(
            $estimatedTokens,
            $request->input('preferred_provider'),
            $text,
            $request->input('role'),
            $geminiAllowedAndConfigured,
            $openaiAllowedAndConfigured
        );

        return response()->json([
            'char_length' => $charLength,
            'word_count' => $wordCount,
            'estimated_tokens' => $estimatedTokens,
            'tier' => $delegation['tier'],
            'role' => $delegation['role'] ?? 'execute_task',
            'recommended_provider' => $delegation['provider'],
            'delegation_reason' => $delegation['reason'],
            'forced_delegation' => $delegation['forced_delegation'],
        ]);
    }
}
