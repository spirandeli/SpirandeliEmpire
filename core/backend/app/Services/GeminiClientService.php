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
        $this->defaultModel = self::normalizeModelName(config('ai.gemini.default_model', env('GEMINI_MODEL', 'gemini-3.8-flash')));

        $rawBaseUrl = trim((string) config('ai.gemini.base_url', env('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta')));
        // Auto-correct invalid hosts like 'https://googleapis.com' to official 'https://generativelanguage.googleapis.com/v1beta'
        if (empty($rawBaseUrl) || ($rawBaseUrl === 'https://googleapis.com') || (str_contains($rawBaseUrl, 'googleapis.com') && !str_contains($rawBaseUrl, 'generativelanguage'))) {
            $rawBaseUrl = 'https://generativelanguage.googleapis.com/v1beta';
        } elseif (!str_contains($rawBaseUrl, '/v1beta') && !str_contains($rawBaseUrl, '/v1')) {
            $rawBaseUrl = rtrim($rawBaseUrl, '/') . '/v1beta';
        }
        $this->baseUrl = rtrim($rawBaseUrl, '/');

        $this->temperature = (float) config('ai.gemini.temperature', env('GEMINI_TEMPERATURE', 0.6));

        // Auto-correct typos like 665536 down to Google's true maximum 65536
        $rawMaxTokens = (int) config('ai.gemini.max_tokens', env('GEMINI_MAX_TOKENS', 65536));
        $this->maxTokens = min(max($rawMaxTokens, 512), 65536);

        $this->freeTierMode = (bool) config('ai.gemini.free_tier_mode', env('GEMINI_FREE_TIER_MODE', true));
    }

    /**
     * Normalize model name, preserving Gemini 3.8 Flash as the primary default.
     */
    public static function normalizeModelName(?string $model): string
    {
        $m = trim((string) $model);
        if (empty($m) || in_array(strtolower($m), ['default', 'gemini', 'gemini-flash'], true)) {
            return 'gemini-3.8-flash';
        }
        return $m;
    }

    protected function resolveApiKey(): ?string
    {
        $envKey = config('ai.gemini.api_key', env('GEMINI_API_KEY'));
        if (!empty($envKey) && strlen(trim($envKey)) > 10) {
            return trim($envKey);
        }

        // Also check root .env file in parent directories if running inside Laravel subdirectory
        $candidatePaths = [
            base_path('.env'),
            base_path('../../.env'),
            dirname(base_path()) . '/.env',
        ];
        foreach ($candidatePaths as $p) {
            if (file_exists($p) && is_readable($p)) {
                $lines = file($p, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
                foreach ($lines as $line) {
                    if (str_starts_with(trim($line), 'GEMINI_API_KEY=')) {
                        $parts = explode('=', $line, 2);
                        $k = trim($parts[1] ?? '', " \t\n\r\0\x0B\"'");
                        if (strlen($k) > 10) {
                            return $k;
                        }
                    }
                }
            }
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

        // Google Gemini 3.8 Flash allows up to 65536 tokens of output. Values > 65536 cause schema validation errors.
        $safeMaxTokens = min(max((int) $this->maxTokens, 512), 65536);

        $payload = [
            'contents' => $contents,
            'generationConfig' => [
                'temperature' => $this->temperature,
                'maxOutputTokens' => $safeMaxTokens,
            ]
        ];

        if (!empty($systemPrompt)) {
            $payload['system_instruction'] = [
                'parts' => [
                    ['text' => $systemPrompt]
                ]
            ];
        }

        // Official Google Gemini models (Gemini 3.8 Flash as primary high-intelligence workhorse)
        $normalizedTarget = self::normalizeModelName($targetModel);
        $candidateModels = [$normalizedTarget];
        foreach (['gemini-3.8-flash', 'gemini-3.5-flash', 'gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-flash'] as $altModel) {
            if (!in_array($altModel, $candidateModels, true)) {
                $candidateModels[] = $altModel;
            }
        }

        $response = null;
        $usedModel = $normalizedTarget;
        $lastError = null;

        foreach ($candidateModels as $modelName) {
            $endpoint = "{$this->baseUrl}/models/{$modelName}:generateContent?key={$this->apiKey}";

            // Allow up to 3 retries with backoff for primary model to ride out temporary demand spikes
            $modelRetries = ($modelName === $normalizedTarget) ? 3 : 1;

            for ($attempt = 1; $attempt <= $modelRetries; $attempt++) {
                try {
                    $attemptResp = Http::timeout(35)
                        ->connectTimeout(8)
                        ->withOptions(['force_ip_resolve' => 'v4'])
                        ->withHeaders(['Content-Type' => 'application/json'])
                        ->post($endpoint, $payload);

                    if ($attemptResp->successful()) {
                        $response = $attemptResp;
                        $usedModel = $modelName;
                        break 2; // Success! Break out of both retry loop and candidate models loop
                    }

                    $response = $attemptResp;
                    $statusCode = $attemptResp->status();
                    $errMsg = $attemptResp->json('error.message') ?? "HTTP {$statusCode}";
                    $lastError = $errMsg;

                    // If 404 or 400 (model name unrecognized on this endpoint tier), immediately try next candidate model!
                    if (in_array($statusCode, [404, 400], true)) {
                        Log::info("Gemini modelo '{$modelName}' indisponível no endpoint ({$statusCode}: {$errMsg}). Tentando próximo modelo suportado...");
                        break;
                    }

                    // If 503 (high demand), 429 (quota/rate limit), 500, 502, 504, retry primary model with backoff!
                    $isHighDemandOrRateLimit = in_array($statusCode, [503, 429, 500, 502, 504], true)
                        || preg_match('/(high demand|temporary|overloaded|resource_exhausted|quota|rate|unavailable)/i', $errMsg);

                    if ($isHighDemandOrRateLimit) {
                        if ($attempt < $modelRetries) {
                            $waitMs = $attempt * 1400000; // 1.4s, 2.8s
                            Log::info("Gemini {$modelName} pico de demanda (HTTP {$statusCode}). Tentativa {$attempt}/{$modelRetries}. Aguardando " . ($waitMs / 1000000) . "s antes de tentar novamente...");
                            usleep($waitMs);
                            continue;
                        } else {
                            Log::warning("Gemini {$modelName} com alta demanda persistente após {$modelRetries} tentativas. Tentando próximo modelo da família...");
                            usleep(400000);
                            break; // Try next candidate model
                        }
                    }

                    break;
                } catch (\Throwable $e) {
                    $cleanMsg = preg_replace('/key=[^&\s]+/i', 'key=***', $e->getMessage());
                    $lastError = $cleanMsg;
                    Log::warning("Gemini attempt on {$modelName} failed: {$cleanMsg}");
                    if ($attempt < $modelRetries) {
                        usleep(1200000);
                        continue;
                    }
                    break;
                }
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
