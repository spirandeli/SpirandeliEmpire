<?php

namespace App\Services\Gemini;

use App\Exceptions\GeminiApiException;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

/**
 * Cliente REST oficial da API do Gemini (v1beta) para geração de conteúdo
 * com suporte a Function Calling, System Instructions e Structured Outputs.
 */
class GeminiClient
{
    public function __construct(
        private readonly string $apiKey,
        private readonly string $model = 'gemini-3.8',
        private readonly string $baseUrl = 'https://generativelanguage.googleapis.com/v1beta',
        private readonly int $timeout = 120,
    ) {
    }

    /**
     * Envia uma requisição de geração de conteúdo para o modelo Gemini.
     *
     * @param  array<int, array{role: string, parts: array<int, mixed>}>  $contents
     * @param  array<string, mixed>|null  $systemInstruction
     * @param  array<int, array<string, mixed>>|null  $tools
     * @param  array<string, mixed>|null  $generationConfig
     * @return array<string, mixed>
     *
     * @throws GeminiApiException
     */
    public function generateContent(
        array $contents,
        ?array $systemInstruction = null,
        ?array $tools = null,
        ?array $generationConfig = null,
    ): array {
        $endpoint = sprintf(
            '%s/models/%s:generateContent',
            rtrim($this->baseUrl, '/'),
            $this->model
        );

        $payload = ['contents' => $contents];

        if (! empty($systemInstruction)) {
            $payload['systemInstruction'] = $systemInstruction;
        }

        if (! empty($tools)) {
            $payload['tools'] = $tools;
            $payload['toolConfig'] = [
                'functionCallingConfig' => [
                    'mode' => 'AUTO',
                ],
            ];
        }

        if (! empty($generationConfig)) {
            $payload['generationConfig'] = $generationConfig;
        } else {
            $payload['generationConfig'] = [
                'temperature' => 0.4,
                'topP' => 0.95,
                'maxOutputTokens' => 8192,
            ];
        }

        try {
            $response = Http::withHeaders([
                'x-goog-api-key' => $this->apiKey,
                'Content-Type' => 'application/json',
            ])
                ->timeout($this->timeout)
                ->retry(
                    times: 3,
                    sleepMilliseconds: 1000,
                    when: function ($exception) {
                        if ($exception instanceof ConnectionException) {
                            return true;
                        }
                        // Trata erros transitórios de rate limit (429) ou instabilidade temporária (500, 502, 503, 504)
                        if (method_exists($exception, 'response') && $exception->response) {
                            $status = $exception->response->status();
                            return in_array($status, [429, 500, 502, 503, 504], true);
                        }
                        return false;
                    },
                    throw: false
                )
                ->post($endpoint, $payload);
        } catch (\Throwable $e) {
            Log::error('Erro de conexão ao chamar API do Gemini', [
                'error' => $e->getMessage(),
                'model' => $this->model,
            ]);
            throw new GeminiApiException('Falha de conexão com a API do Gemini: ' . $e->getMessage(), 0, $e);
        }

        if (! $response->successful()) {
            $this->handleErrorResponse($response);
        }

        return $response->json();
    }

    private function handleErrorResponse(Response $response): void
    {
        $status = $response->status();
        $error = $response->json('error', []);
        $message = $error['message'] ?? $response->body();
        $statusText = $error['status'] ?? 'ERROR';

        Log::error('API do Gemini retornou erro', [
            'status' => $status,
            'status_text' => $statusText,
            'message' => $message,
            'model' => $this->model,
        ]);

        $customMessage = match ($status) {
            400 => "Requisição inválida para o Gemini: {$message}",
            401, 403 => "Chave de API do Gemini não autorizada ou sem permissão.",
            404 => "Modelo {$this->model} não encontrado na API do Gemini.",
            429 => "Limite de cota/taxa excedido na API do Gemini. Tente novamente em instantes.",
            500, 503 => "Serviço do Gemini temporariamente instável ({$statusText}).",
            default => "Erro na API do Gemini ({$status}): {$message}",
        };

        throw new GeminiApiException($customMessage, $status);
    }
}

