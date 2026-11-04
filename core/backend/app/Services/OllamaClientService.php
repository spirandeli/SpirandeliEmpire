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
        $this->defaultModel = config('ai.ollama.default_model', env('LLAMA_MODEL', env('DEFAULT_TEXT_MODEL', 'llama3.2:3b')));
    }

    /**
     * Generate completion via Ollama local API (Llama, Qwen, etc).
     */
    public function generate(string $prompt, ?string $systemPrompt = null, ?string $model = null): array
    {
        $targetModel = $model ?: $this->defaultModel;
        $startTime = microtime(true);

        try {
            // Use /api/chat with proper system/user roles (better instruction-following than /api/generate).
            $messages = [];
            if ($systemPrompt) {
                $messages[] = ['role' => 'system', 'content' => $systemPrompt];
            }
            $messages[] = ['role' => 'user', 'content' => $prompt];

            $payload = [
                'model' => $targetModel,
                'messages' => $messages,
                'stream' => false,
                'options' => [
                    // Ollama defaults to a 2048-token context, which silently truncates Jeffrey's
                    // system prompt (rules + tools + memories + history). Raise it explicitly.
                    'num_ctx' => (int) env('JEFFREY_CONTEXT_WINDOW', 8192),
                    'temperature' => (float) env('OLLAMA_TEMPERATURE', 0.6),
                ],
            ];

            $timeout = (int) env('OLLAMA_TIMEOUT_SECONDS', config('ai.ollama.timeout_seconds', 90));
            $response = Http::timeout($timeout)->post("{$this->baseUrl}/api/chat", $payload);
            $latencyMs = round((microtime(true) - $startTime) * 1000);

            if ($response->successful()) {
                return [
                    'success' => true,
                    'response' => $response->json('message.content'),
                    'model' => $targetModel,
                    'provider' => 'ollama_llama',
                    'latency_ms' => $latencyMs,
                    'eval_count' => $response->json('eval_count'),
                    'is_local' => true,
                ];
            }

            if ($response->status() === 404 || str_contains($response->body(), 'not found')) {
                $installed = $this->listModels();
                if (!empty($installed)) {
                    $firstModel = $installed[0]['name'] ?? null;
                    if ($firstModel && $firstModel !== $targetModel) {
                        Log::info("Modelo {$targetModel} não encontrado. Roteando automaticamente para modelo instalado: {$firstModel}");
                        return $this->generate($prompt, $systemPrompt, $firstModel);
                    }
                }
                return [
                    'success' => false,
                    'error' => "Nenhum modelo compatível no Ollama local. Baixe um modelo executando: docker compose exec -it ollama ollama pull qwen2.5:3b",
                    'provider' => 'ollama_llama',
                ];
            }

            return [
                'success' => false,
                'error' => 'Ollama HTTP error: ' . $response->status(),
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
                    'target_model' => $this->defaultModel,
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
        return $this->defaultModel;
    }
}
