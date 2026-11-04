<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class GeminiClientService
{
    protected ?string $apiKey;
    protected string $defaultModel;
    protected string $baseUrl;
    protected float $temperature;
    protected int $maxTokens;
    protected bool $freeTierMode;

    public function __construct()
    {
        $this->apiKey = config('ai.gemini.api_key', env('GEMINI_API_KEY'));
        $this->defaultModel = config('ai.gemini.default_model', env('GEMINI_MODEL', 'gemini-1.5-flash'));
        $this->baseUrl = config('ai.gemini.base_url', env('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta'));
        $this->temperature = (float) config('ai.gemini.temperature', env('GEMINI_TEMPERATURE', 0.7));
        $this->maxTokens = (int) config('ai.gemini.max_tokens', env('GEMINI_MAX_TOKENS', 4096));
        $this->freeTierMode = (bool) config('ai.gemini.free_tier_mode', env('GEMINI_FREE_TIER_MODE', true));
    }

    /**
     * Check if Gemini API key is configured.
     */
    public function isConfigured(): bool
    {
        return !empty($this->apiKey) && strlen(trim($this->apiKey)) > 10;
    }

    /**
     * Generate completion via Google Gemini REST API.
     */
    public function generate(string $prompt, ?string $systemPrompt = null, ?string $model = null): array
    {
        if (!$this->isConfigured()) {
            return [
                'success' => false,
                'error' => 'Google Gemini API key não configurada no .env (GEMINI_API_KEY).',
                'provider' => 'google_gemini',
            ];
        }

        $targetModel = $model ?: $this->defaultModel;
        $startTime = microtime(true);

        try {
            $payload = [
                'contents' => [
                    [
                        'role' => 'user',
                        'parts' => [
                            ['text' => $prompt]
                        ]
                    ]
                ],
                'generationConfig' => [
                    'temperature' => $this->temperature,
                    'maxOutputTokens' => $this->maxTokens,
                ]
            ];

            if (!empty($systemPrompt)) {
                $payload['system_instruction'] = [
                    'parts' => [
                        ['text' => $systemPrompt]
                    ]
                ];
            }

            $endpoint = "{$this->baseUrl}/models/{$targetModel}:generateContent?key={$this->apiKey}";

            $response = Http::timeout(45)
                ->withHeaders(['Content-Type' => 'application/json'])
                ->post($endpoint, $payload);

            $latencyMs = round((microtime(true) - $startTime) * 1000);

            if ($response->successful()) {
                $data = $response->json();
                $replyText = $data['candidates'][0]['content']['parts'][0]['text'] ?? '';
                $usage = $data['usageMetadata'] ?? [];

                return [
                    'success' => true,
                    'response' => $replyText,
                    'model' => $targetModel,
                    'provider' => 'google_gemini',
                    'latency_ms' => $latencyMs,
                    'tokens' => [
                        'prompt' => $usage['promptTokenCount'] ?? 0,
                        'candidates' => $usage['candidatesTokenCount'] ?? 0,
                        'total' => $usage['totalTokenCount'] ?? 0,
                    ],
                    'is_free_tier' => $this->freeTierMode,
                ];
            }

            $statusCode = $response->status();
            $errorJson = $response->json();
            $errorMessage = $errorJson['error']['message'] ?? "Google API HTTP error {$statusCode}";

            Log::warning("Gemini API error [{$statusCode}]: {$errorMessage}");

            return [
                'success' => false,
                'status_code' => $statusCode,
                'error' => $errorMessage,
                'provider' => 'google_gemini',
                'quota_exceeded' => in_array($statusCode, [429, 403]) || str_contains(strtolower($errorMessage), 'quota'),
            ];
        } catch (\Exception $e) {
            Log::error('Gemini connection exception: ' . $e->getMessage());
            return [
                'success' => false,
                'error' => 'Falha de conexão com Google Gemini: ' . $e->getMessage(),
                'provider' => 'google_gemini',
            ];
        }
    }

    /**
     * Test connection and credentials with a tiny ping.
     */
    public function testConnection(): array
    {
        if (!$this->isConfigured()) {
            return [
                'success' => false,
                'message' => 'API Key não configurada. Defina GEMINI_API_KEY no arquivo .env.',
            ];
        }

        $result = $this->generate('Responda apenas "OK" em uma única palavra.', null, $this->defaultModel);
        if ($result['success']) {
            return [
                'success' => true,
                'message' => 'Google Gemini conectado com sucesso! Latência: ' . $result['latency_ms'] . 'ms',
                'model' => $result['model'],
                'free_tier' => $this->freeTierMode,
            ];
        }

        return [
            'success' => false,
            'message' => 'Erro ao conectar com Google Gemini: ' . ($result['error'] ?? 'Desconhecido'),
        ];
    }

    public function getDefaultModel(): string
    {
        return $this->defaultModel;
    }
}

