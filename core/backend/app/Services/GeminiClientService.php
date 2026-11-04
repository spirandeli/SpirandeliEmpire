<?php

namespace App\Services;

use App\Models\JeffreyMemory;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Redis;

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
        $this->apiKey = $this->resolveApiKey();
        $this->defaultModel = config('ai.gemini.default_model', env('GEMINI_MODEL', 'gemini-3.8-flash'));
        $this->baseUrl = config('ai.gemini.base_url', env('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta'));
        $this->temperature = (float) config('ai.gemini.temperature', env('GEMINI_TEMPERATURE', 0.6));
        $this->maxTokens = (int) config('ai.gemini.max_tokens', env('GEMINI_MAX_TOKENS', 4096));
        $this->freeTierMode = (bool) config('ai.gemini.free_tier_mode', env('GEMINI_FREE_TIER_MODE', true));
    }

    protected function resolveApiKey(): ?string
    {
        $envKey = config('ai.gemini.api_key', env('GEMINI_API_KEY'));
        if (!empty($envKey) && strlen(trim($envKey)) > 10) {
            return trim($envKey);
        }
        try {
            $raw = Redis::get('empire:ai:config');
            if ($raw) {
                $cfg = json_decode($raw, true);
                if (!empty($cfg['gemini_api_key']) && strlen(trim($cfg['gemini_api_key'])) > 10) {
                    return trim($cfg['gemini_api_key']);
                }
            }
        } catch (\Exception $e) {}

        try {
            $mem = JeffreyMemory::where('category', 'system_ai_keys')->where('is_active', true)->first();
            if ($mem && !empty($mem->content)) {
                $cfg = json_decode($mem->content, true);
                if (!empty($cfg['gemini_api_key']) && strlen(trim($cfg['gemini_api_key'])) > 10) {
                    return trim($cfg['gemini_api_key']);
                }
            }
        } catch (\Exception $e) {}

        return $envKey;
    }

    /**
     * Check if Gemini API key is configured.
     */
    public function isConfigured(): bool
    {
        return !empty($this->apiKey) && strlen(trim($this->apiKey)) > 10;
    }

    /**
     * Generate completion via Google Gemini REST API (forces IPv4 to prevent Docker IPv6 cURL error 28 timeouts).
     * Supports native multi-turn conversation history with alternating roles.
     */
    public function generate(
        string $prompt,
        ?string $systemPrompt = null,
        ?string $model = null,
        array $inlineMedia = [],
        array $conversationTurns = []
    ): array {
        if (!$this->isConfigured()) {
            return [
                'success' => false,
                'error' => 'Google Gemini API key não configurada no .env (GEMINI_API_KEY).',
                'provider' => 'google_gemini',
            ];
        }

        $targetModel = $model ?: $this->defaultModel;
        $startTime = microtime(true);

        $userParts = [
            ['text' => $prompt]
        ];
        foreach ($inlineMedia as $media) {
            if (!empty($media['mime_type']) && !empty($media['data'])) {
                $userParts[] = [
                    'inline_data' => [
                        'mime_type' => $media['mime_type'],
                        'data' => $media['data'],
                    ],
                ];
            }
        }

        // Build structured multi-turn contents if history turns provided
        $contents = [];
        if (!empty($conversationTurns)) {
            foreach ($conversationTurns as $turn) {
                $role = in_array($turn['role'] ?? 'user', ['model', 'assistant'], true) ? 'model' : 'user';
                $text = trim((string)($turn['text'] ?? $turn['content'] ?? ''));
                if ($text === '') continue;

                // Merge with previous turn if same role to satisfy Gemini API alternating contract
                $lastIdx = count($contents) - 1;
                if ($lastIdx >= 0 && $contents[$lastIdx]['role'] === $role) {
                    $contents[$lastIdx]['parts'][0]['text'] .= "\n\n" . $text;
                } else {
                    $contents[] = [
                        'role' => $role,
                        'parts' => [['text' => $text]],
                    ];
                }
            }

            // Ensure first turn starts with user
            if (!empty($contents) && $contents[0]['role'] === 'model') {
                array_shift($contents);
            }
        }

        // Append active user prompt turn
        $lastIdx = count($contents) - 1;
        if ($lastIdx >= 0 && $contents[$lastIdx]['role'] === 'user') {
            $contents[$lastIdx]['parts'] = array_merge($contents[$lastIdx]['parts'], $userParts);
        } else {
            $contents[] = [
                'role' => 'user',
                'parts' => $userParts,
            ];
        }

        $payload = [
            'contents' => $contents,
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

        $candidateModels = [$targetModel];
        foreach (['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash'] as $altModel) {
            if (!in_array($altModel, $candidateModels, true)) {
                $candidateModels[] = $altModel;
            }
        }

        $response = null;
        $usedModel = $targetModel;
        $lastError = null;

        foreach ($candidateModels as $modelName) {
            $endpoint = "{$this->baseUrl}/models/{$modelName}:generateContent?key={$this->apiKey}";
            try {
                $attemptResp = Http::timeout(22)
                    ->connectTimeout(6)
                    ->withOptions(['force_ip_resolve' => 'v4'])
                    ->withHeaders(['Content-Type' => 'application/json'])
                    ->post($endpoint, $payload);

                if ($attemptResp->successful()) {
                    $response = $attemptResp;
                    $usedModel = $modelName;
                    break;
                }

                $response = $attemptResp;
                $statusCode = $attemptResp->status();
                $errMsg = $attemptResp->json('error.message') ?? "HTTP {$statusCode}";
                $lastError = $errMsg;

                // If 404 or 400 (model tag not recognized on v1beta), try next Flash model
                if (in_array($statusCode, [404, 400], true)) {
                    continue;
                }
                break;
            } catch (\Throwable $e) {
                $cleanMsg = preg_replace('/key=[^&\s]+/i', 'key=***', $e->getMessage());
                $lastError = $cleanMsg;
                Log::warning("Gemini attempt on {$modelName} failed: {$cleanMsg}");
                continue;
            }
        }

        $latencyMs = round((microtime(true) - $startTime) * 1000);

        if ($response && $response->successful()) {
            $data = $response->json();
            $cand = $data['candidates'][0] ?? [];
            $parts = $cand['content']['parts'] ?? [];
            $textChunks = [];
            foreach ($parts as $p) {
                if (!empty($p['text'])) {
                    $textChunks[] = $p['text'];
                }
            }
            $replyText = implode("\n", $textChunks);
            $usage = $data['usageMetadata'] ?? [];

            return [
                'success' => true,
                'response' => $replyText,
                'model' => $usedModel,
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

        $statusCode = $response ? $response->status() : 500;
        $errorMessage = $lastError ?: 'Sem resposta do servidor Google Gemini.';
        $errorMessage = preg_replace('/key=[^&\s]+/i', 'key=***', $errorMessage);

        return [
            'success' => false,
            'status_code' => $statusCode,
            'error' => $errorMessage,
            'provider' => 'google_gemini',
            'quota_exceeded' => in_array($statusCode, [429, 403], true) || str_contains(strtolower($errorMessage), 'quota'),
        ];
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
