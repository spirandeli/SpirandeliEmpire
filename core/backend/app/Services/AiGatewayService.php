<?php

namespace App\Services;

use Illuminate\Support\Facades\Log;

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

        $this->defaultStrategy = config('ai.default_provider', env('AI_PROVIDER', 'hybrid'));
        $this->fallbackOrder = config('ai.fallback_order', ['gemini', 'openai', 'ollama']);
    }

    /**
     * Generate text through the intelligent multi-provider gateway with token verification & smart delegation.
     */
    public function generate(string $prompt, ?string $systemPrompt = null, ?string $preferredProvider = null, ?string $model = null): array
    {
        // 1. Estimate tokens prior to dispatch
        $fullText = $prompt . ($systemPrompt ? ' ' . $systemPrompt : '');
        $estimatedInputTokens = $this->tokenManager->estimateTokens($fullText);

        // 2. Token-based task delegation analysis
        $delegation = $this->tokenManager->determineOptimalProvider($estimatedInputTokens, $preferredProvider);
        $strategy = $delegation['provider'];

        // If user explicitly asked for a provider, $delegation['forced_delegation'] indicates if safe limits overrode it
        $effectiveStrategy = $preferredProvider && !in_array($preferredProvider, ['hybrid', 'auto']) && !$delegation['forced_delegation']
            ? $preferredProvider
            : $strategy;

        $result = $this->executeStrategy($effectiveStrategy, $prompt, $systemPrompt, $model);

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
            'delegation_reason' => $delegation['reason'],
            'forced_delegation' => $delegation['forced_delegation'],
        ];

        return $result;
    }

    protected function executeStrategy(string $strategy, string $prompt, ?string $systemPrompt, ?string $model): array
    {
        // Direct Provider: Gemini
        if ($strategy === 'gemini') {
            $res = $this->gemini->generate($prompt, $systemPrompt, $model);
            if ($res['success']) {
                $res['provider_name'] = 'Google Gemini (Free/Paid Tier)';
                return $res;
            }
            return $this->fallbackToLocal($prompt, $systemPrompt, 'Google Gemini falhou: ' . ($res['error'] ?? 'desconhecido'));
        }

        // Direct Provider: OpenAI
        if ($strategy === 'openai') {
            $res = $this->openai->generate($prompt, $systemPrompt, $model);
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
            // If local fails, attempt Gemini as emergency fallback
            if ($this->gemini->isConfigured()) {
                Log::warning('Llama Local indisponível. Tentando Google Gemini como emergência...');
                $geminiRes = $this->gemini->generate($prompt, $systemPrompt);
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

        // 1. Google Gemini (free credits & massive context)
        if ($this->gemini->isConfigured()) {
            $geminiRes = $this->gemini->generate($prompt, $systemPrompt);
            if ($geminiRes['success']) {
                $geminiRes['provider_name'] = 'Google Gemini (Free Tier / Cloud)';
                $geminiRes['routing'] = 'primary_free_tier';
                return $geminiRes;
            }
            $errors[] = 'Gemini: ' . ($geminiRes['error'] ?? 'Erro desconhecido');
        } else {
            $errors[] = 'Gemini: Key não configurada';
        }

        // 2. OpenAI
        if ($this->openai->isConfigured()) {
            $openaiRes = $this->openai->generate($prompt, $systemPrompt);
            if ($openaiRes['success']) {
                $openaiRes['provider_name'] = 'OpenAI (Fallback Tier)';
                $openaiRes['routing'] = 'secondary_openai_fallback';
                $openaiRes['fallback_reason'] = implode('; ', $errors);
                return $openaiRes;
            }
            $errors[] = 'OpenAI: ' . ($openaiRes['error'] ?? 'Erro desconhecido');
        } else {
            $errors[] = 'OpenAI: Key não configurada';
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
     * Get detailed status of all AI providers including token governance stats.
     */
    public function getProvidersStatus(): array
    {
        $ollamaModels = $this->ollama->listModels();
        $tokenStats = $this->tokenManager->getTokenStats();

        return [
            'current_strategy' => $this->defaultStrategy,
            'budget_status' => $this->budget->getBudgetStatus(),
            'token_governance' => $tokenStats,
            'providers' => [
                'google_gemini' => [
                    'name' => 'Google Gemini (AI Studio)',
                    'configured' => $this->gemini->isConfigured(),
                    'default_model' => $this->gemini->getDefaultModel(),
                    'free_tier_eligible' => true,
                    'context_window' => '1.000.000 tokens',
                    'pricing_profile' => 'Free Tier (15 RPM / 1M TPM sem custo) + Créditos',
                    'official_url' => 'https://aistudio.google.com/app/apikey',
                ],
                'openai' => [
                    'name' => 'OpenAI (GPT-4o Mini / Plans)',
                    'configured' => $this->openai->isConfigured(),
                    'default_model' => $this->openai->getDefaultModel(),
                    'context_window' => '128.000 tokens',
                    'pricing_profile' => 'Créditos Gratuitos de Boas-Vindas ou Pay-As-You-Go',
                    'official_url' => 'https://platform.openai.com/api-keys',
                ],
                'ollama_llama' => [
                    'name' => 'Llama Local (Ollama)',
                    'configured' => true,
                    'connected' => !empty($ollamaModels),
                    'default_model' => $this->ollama->getDefaultModel(),
                    'context_window' => '8.192 tokens (Otimizado para 8GB VPS)',
                    'installed_models' => array_map(fn($m) => $m['name'] ?? '', $ollamaModels),
                    'pricing_profile' => '100% Gratuito & Local (CPU ou GPU do VPS)',
                    'offline_ready' => true,
                ],
            ],
            'hybrid_routing_pipeline' => [
                'priority_1' => 'Google Gemini (Consome quota gratuita do Google AI Studio)',
                'priority_2' => 'OpenAI GPT (Fallback para créditos OpenAI ou planos)',
                'priority_3' => 'Llama Local via Ollama (Garantia zero-custo e 100% offline)',
            ]
        ];
    }

    /**
     * Test connection for a given provider.
     */
    public function testProvider(string $provider): array
    {
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
