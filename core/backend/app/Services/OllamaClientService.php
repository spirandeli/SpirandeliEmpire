<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class OllamaClientService
{
    protected string $baseUrl;
    protected string $defaultModel;

    public function __construct()
    {
        $this->baseUrl = config('ai.ollama.base_url', env('OLLAMA_BASE_URL', 'http://ollama:11434'));
        $rawModel = config('ai.ollama.default_model', env('LLAMA_MODEL', env('DEFAULT_TEXT_MODEL', 'qwen2.5:3b')));
        // Prevent legacy 7b/8b/14b defaults from causing OOM HTTP 500 on 8GB VPS
        if (preg_match('/:(7b|8b|13b|14b)/i', (string) $rawModel)) {
            $rawModel = 'qwen2.5:3b';
        }
        $this->defaultModel = $rawModel ?: 'qwen2.5:3b';
    }

    /**
     * Resolve which model to use: always prioritize lightweight 3b/1.5b models on 8GB VPS
     * so Ollama never crashes with HTTP 500 unexpected EOF (OOM).
     */
    protected function resolveAvailableModel(?string $requestedModel = null): string
    {
        $target = $requestedModel ?: $this->defaultModel;
        if (preg_match('/:(7b|8b|13b|14b)/i', $target)) {
            $target = 'qwen2.5:3b';
        }

        $installed = $this->listModels();
        if (empty($installed)) {
            return $target;
        }

        $installedNames = array_values(array_filter(array_map(fn($m) => $m['name'] ?? null, $installed)));

        // Always prefer 3b / 1.5b models first to guarantee zero OOM crashes
        foreach (['qwen2.5:3b', 'llama3.2:3b', 'qwen2.5:1.5b', 'llama3.2:1b'] as $preferred) {
            if (in_array($preferred, $installedNames, true)) {
                if ($target === $preferred || !in_array($target, $installedNames, true) || preg_match('/:(7b|8b|13b|14b)/i', $target)) {
                    return $preferred;
                }
            }
        }

        if (in_array($target, $installedNames, true)) {
            return $target;
        }

        return $installedNames[0] ?? 'qwen2.5:3b';
    }

    /**
     * Generate completion via Ollama local API (Llama, Qwen, etc).
     */
    public function generate(string $prompt, ?string $systemPrompt = null, ?string $model = null): array
    {
        $targetModel = $this->resolveAvailableModel($model);
        $startTime = microtime(true);

        try {
            $messages = [];
            if ($systemPrompt) {
                $messages[] = ['role' => 'system', 'content' => $systemPrompt];
            }
            $messages[] = ['role' => 'user', 'content' => $prompt];

            // Keep context window conservative (2048) on 8GB VPS so Ollama runner doesn't crash with HTTP 500 OOM
            $numCtx = (int) env('OLLAMA_NUM_CTX', 2048);

            $payload = [
                'model' => $targetModel,
                'messages' => $messages,
                'stream' => false,
                'keep_alive' => '30m',
                'options' => [
                    'num_ctx' => $numCtx,
                    'num_predict' => (int) env('OLLAMA_MAX_TOKENS', 350),
                    'temperature' => (float) env('OLLAMA_TEMPERATURE', 0.5),
                ],
            ];

            $timeout = (int) env('OLLAMA_TIMEOUT_SECONDS', config('ai.ollama.timeout_seconds', 120));
            $response = Http::timeout($timeout)->post("{$this->baseUrl}/api/chat", $payload);

            // If /api/chat returned 500 (typically low RAM / context allocation failure on VPS),
            // retry with minimal context (1024) and force qwen2.5:3b via /api/generate
            if ($response->status() >= 500) {
                $errBody = $response->json('error') ?? $response->body();
                Log::warning("Ollama /api/chat 500 on {$targetModel} ({$errBody}). Retrying with qwen2.5:3b & num_ctx=1024...");

                $fallbackModel = 'qwen2.5:3b';
                $compactSystem = "Você é Jeffrey, o agente executivo central do SpirandeliEmpire OS. Responda em português brasileiro de forma clara, técnica e objetiva.";
                $retryPayload = [
                    'model' => $fallbackModel,
                    'prompt' => mb_substr($prompt, -3500),
                    'system' => $compactSystem,
                    'stream' => false,
                    'options' => [
                        'num_ctx' => 1024,
                        'num_predict' => 300,
                    ],
                ];
                $response = Http::timeout($timeout)->post("{$this->baseUrl}/api/generate", $retryPayload);
                if ($response->successful()) {
                    $targetModel = $fallbackModel;
                }
            }

            $latencyMs = round((microtime(true) - $startTime) * 1000);

            if ($response->successful()) {
                $content = $response->json('message.content') ?? $response->json('response');
                return [
                    'success' => true,
                    'response' => $content,
                    'model' => $targetModel,
                    'provider' => 'ollama_llama',
                    'latency_ms' => $latencyMs,
                    'eval_count' => $response->json('eval_count'),
                    'is_local' => true,
                ];
            }

            $ollamaError = $response->json('error') ?: trim(substr($response->body(), 0, 300));

            if ($response->status() === 404 || str_contains(strtolower($ollamaError), 'not found')) {
                return [
                    'success' => false,
                    'error' => "Modelo '{$targetModel}' não encontrado no Ollama. Baixe executando: docker compose exec -it ollama ollama pull qwen2.5:3b",
                    'provider' => 'ollama_llama',
                ];
            }

            return [
                'success' => false,
                'error' => "Ollama HTTP {$response->status()} ({$targetModel}): {$ollamaError}",
                'provider' => 'ollama_llama',
            ];
        } catch (\Exception $e) {
            Log::error('Ollama connection failed: ' . $e->getMessage());
            return [
                'success' => false,
                'error' => 'Could not connect to Ollama: ' . $e->getMessage(),
                'provider' => 'ollama_llama',
            ];
        }
    }

    /**
     * List available models in Ollama.
     */
    public function listModels(): array
    {
        try {
            $response = Http::timeout(5)->get("{$this->baseUrl}/api/tags");
            if ($response->successful()) {
                return $response->json('models') ?? [];
            }
            return [];
        } catch (\Exception $e) {
            return [];
        }
    }

    /**
     * Test local Ollama connection.
     */
    public function testConnection(): array
    {
        try {
            $response = Http::timeout(4)->get("{$this->baseUrl}/api/tags");
            if ($response->successful()) {
                $models = $response->json('models') ?? [];
                $modelNames = array_map(fn($m) => $m['name'] ?? '', $models);
                return [
                    'success' => true,
                    'message' => 'Ollama local operacional! Modelos disponíveis: ' . count($models),
                    'installed_models' => $modelNames,
                    'target_model' => $this->resolveAvailableModel(),
                ];
            }
            return [
                'success' => false,
                'message' => 'Ollama respondeu com status HTTP ' . $response->status(),
            ];
        } catch (\Exception $e) {
            return [
                'success' => false,
                'message' => 'Ollama local inacessível: ' . $e->getMessage(),
            ];
        }
    }

    public function getDefaultModel(): string
    {
        return $this->resolveAvailableModel();
    }
}
