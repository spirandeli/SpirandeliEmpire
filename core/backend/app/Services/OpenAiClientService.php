<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class OpenAiClientService
{
    protected ?string $apiKey;
    protected string $defaultModel;
    protected string $baseUrl;
    protected float $temperature;
    protected int $maxTokens;

    public function __construct()
    {
        $this->apiKey = env('OPENAI_API_KEY', config('ai.openai.api_key'));
        $this->defaultModel = env('OPENAI_MODEL', config('ai.openai.default_model', 'gpt-4o-mini'));
        $this->baseUrl = env('OPENAI_BASE_URL', config('ai.openai.base_url', 'https://api.openai.com/v1'));
        $this->temperature = (float) env('OPENAI_TEMPERATURE', config('ai.openai.temperature', 0.7));
        $this->maxTokens = (int) env('OPENAI_MAX_TOKENS', config('ai.openai.max_tokens', 4096));
    }

    /**
     * Check if OpenAI API key is configured.
     */
    public function isConfigured(): bool
    {
        return !empty($this->apiKey) && strlen(trim($this->apiKey)) > 10;
    }

    /**
     * Generate completion via OpenAI Chat Completions API.
     */
    public function generate(string $prompt, ?string $systemPrompt = null, ?string $model = null): array
    {
        if (!$this->isConfigured()) {
            return [
                'success' => false,
                'error' => 'OpenAI API key não configurada no .env (OPENAI_API_KEY).',
                'provider' => 'openai',
            ];
        }

        $targetModel = $model ?: $this->defaultModel;
        $startTime = microtime(true);

        try {
            $messages = [];
            if (!empty($systemPrompt)) {
                $messages[] = [
                    'role' => 'system',
                    'content' => $systemPrompt,
                ];
            }
            $messages[] = [
                'role' => 'user',
                'content' => $prompt,
            ];

            $payload = [
                'model' => $targetModel,
                'messages' => $messages,
                'temperature' => $this->temperature,
                'max_tokens' => $this->maxTokens,
            ];

            $response = Http::timeout(45)
                ->withToken($this->apiKey)
                ->post("{$this->baseUrl}/chat/completions", $payload);

            $latencyMs = round((microtime(true) - $startTime) * 1000);

            if ($response->successful()) {
                $data = $response->json();
                $replyText = $data['choices'][0]['message']['content'] ?? '';
                $usage = $data['usage'] ?? [];

                return [
                    'success' => true,
                    'response' => $replyText,
                    'model' => $targetModel,
                    'provider' => 'openai',
                    'latency_ms' => $latencyMs,
                    'tokens' => [
                        'prompt' => $usage['prompt_tokens'] ?? 0,
                        'candidates' => $usage['completion_tokens'] ?? 0,
                        'total' => $usage['total_tokens'] ?? 0,
                    ],
                ];
            }

            $statusCode = $response->status();
            $errorJson = $response->json();
            $errorMessage = $errorJson['error']['message'] ?? "OpenAI HTTP error {$statusCode}";

            Log::warning("OpenAI API error [{$statusCode}]: {$errorMessage}");

            return [
                'success' => false,
                'status_code' => $statusCode,
                'error' => $errorMessage,
                'provider' => 'openai',
                'quota_exceeded' => in_array($statusCode, [429]) || str_contains(strtolower($errorMessage), 'quota') || str_contains(strtolower($errorMessage), 'billing'),
            ];
        } catch (\Exception $e) {
            Log::error('OpenAI connection exception: ' . $e->getMessage());
            return [
                'success' => false,
                'error' => 'Falha de conexão com OpenAI: ' . $e->getMessage(),
                'provider' => 'openai',
            ];
        }
    }

    /**
     * Test connection and credentials.
     */
    public function testConnection(): array
    {
        if (!$this->isConfigured()) {
            return [
                'success' => false,
                'message' => 'API Key não configurada. Defina OPENAI_API_KEY no arquivo .env.',
            ];
        }

        $result = $this->generate('Responda apenas "OK" em uma única palavra.', null, $this->defaultModel);
        if ($result['success']) {
            return [
                'success' => true,
                'message' => 'OpenAI conectada com sucesso! Latência: ' . $result['latency_ms'] . 'ms',
                'model' => $result['model'],
            ];
        }

        return [
            'success' => false,
            'message' => 'Erro ao conectar com OpenAI: ' . ($result['error'] ?? 'Desconhecido'),
        ];
    }

    public function getDefaultModel(): string
    {
        return $this->defaultModel;
    }
}

