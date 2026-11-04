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
     * Get consolidated status of all AI engines, cooperative role division, and token governance.
     */
    public function status(AiGatewayService $aiGateway): JsonResponse
    {
        $status = $aiGateway->getProvidersStatus();

        return response()->json(array_merge($status, [
            'tts_engine' => 'Piper (Local CPU pt_BR-faber-medium)',
            'video_engine' => 'FFmpeg + Anti-Ban Pipeline',
            'gpu_mode' => env('GPU_EXECUTION_MODE', 'cpu_only'),
            'gpu_remote_enabled' => (bool) env('GPU_REMOTE_ENABLED', false),
        ]));
    }

    /**
     * Save Gemini and/or OpenAI API keys dynamically so both PHP Backend and Python Worker
     * immediately activate the cooperative mode (Llama = Read & Analyze, Gemini/Chat = Execute Tasks).
     */
    public function configureKeys(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'gemini_api_key' => 'nullable|string|max:255',
            'openai_api_key' => 'nullable|string|max:255',
        ]);

        $existingConfig = [];
        try {
            $raw = Redis::get('empire:ai:config');
            if ($raw) {
                $existingConfig = json_decode($raw, true) ?: [];
            }
        } catch (\Exception $e) {}

        if (empty($existingConfig)) {
            $mem = JeffreyMemory::where('category', 'system_ai_keys')->where('is_active', true)->first();
            if ($mem && !empty($mem->content)) {
                $existingConfig = json_decode($mem->content, true) ?: [];
            }
        }

        if (array_key_exists('gemini_api_key', $validated) && $validated['gemini_api_key'] !== null) {
            $existingConfig['gemini_api_key'] = trim($validated['gemini_api_key']);
        }
        if (array_key_exists('openai_api_key', $validated) && $validated['openai_api_key'] !== null) {
            $existingConfig['openai_api_key'] = trim($validated['openai_api_key']);
        }
        $existingConfig['cooperative_mode'] = 'llama_analyze_cloud_execute';
        $existingConfig['updated_at'] = now()->toIso8601String();

        // 1. Save to Redis for instant Python Worker + Laravel pickup
        try {
            Redis::set('empire:ai:config', json_encode($existingConfig));
        } catch (\Exception $e) {}

        // 2. Persist in PostgreSQL JeffreyMemory so it survives Redis flushes
        try {
            JeffreyMemory::updateOrCreate(
                ['category' => 'system_ai_keys', 'business_id' => null],
                [
                    'content' => json_encode($existingConfig),
                    'is_active' => true,
                ]
            );
        } catch (\Exception $e) {}

        // 3. Best-effort update of .env if writable
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
        } catch (\Exception $e) {}

        $aiGateway = app(AiGatewayService::class);

        return response()->json([
            'success' => true,
            'message' => 'Chaves configuradas! Modo Cooperativo ativo: Llama Local para Ler/Analisar e Gemini/Chat para Executar Tarefas.',
            'status' => $aiGateway->getProvidersStatus(),
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

        $result = $aiGateway->testProvider($request->input('provider'));

        return response()->json($result);
    }

    /**
     * Direct test completion across any provider with role & token measurement.
     */
    public function complete(Request $request, AiGatewayService $aiGateway): JsonResponse
    {
        $request->validate([
            'prompt' => 'required|string',
            'provider' => 'nullable|string|in:hybrid,gemini,openai,ollama,llama,cooperative',
            'model' => 'nullable|string',
        ]);

        $provider = $request->input('provider');
        if ($provider === 'cooperative') {
            $result = $aiGateway->analyzeWithLlamaThenExecute(
                $request->input('prompt'),
                $request->input('prompt'),
                'Você é o motor cooperativo do SpirandeliEmpire OS. Use a análise prévia do Llama para executar a resposta final com precisão.'
            );
            return response()->json($result);
        }

        $result = $aiGateway->generate(
            $request->input('prompt'),
            'Você é um assistente de validação do SpirandeliEmpire OS. Responda de forma concisa.',
            $provider,
            $request->input('model')
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
        $status = $aiGateway->getProvidersStatus();
        $geminiConfigured = (bool) ($status['providers']['google_gemini']['configured'] ?? false);
        $openaiConfigured = (bool) ($status['providers']['openai']['configured'] ?? false);

        $delegation = $tokenManager->determineOptimalProvider(
            $estimatedTokens,
            $request->input('preferred_provider'),
            $text,
            $request->input('role'),
            $geminiConfigured,
            $openaiConfigured
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
