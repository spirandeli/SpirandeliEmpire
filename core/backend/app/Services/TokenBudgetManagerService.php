<?php

namespace App\Services;

use Carbon\Carbon;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Log;

class TokenBudgetManagerService
{
    protected bool $tokenRoutingEnabled;
    protected int $localMaxThreshold;
    protected int $longContextThreshold;
    protected int $dailyApiTokenCap;

    public function __construct()
    {
        $this->tokenRoutingEnabled = (bool) env('TOKEN_ROUTING_ENABLED', config('ai.tokens.routing_enabled', true));
        $this->localMaxThreshold = (int) env('TOKEN_THRESHOLD_LOCAL_MAX', config('ai.tokens.threshold_local_max', 800));
        $this->longContextThreshold = (int) env('TOKEN_THRESHOLD_LONG_CONTEXT', config('ai.tokens.threshold_long_context', 3500));
        $this->dailyApiTokenCap = (int) env('DAILY_API_TOKEN_CAP', config('ai.tokens.daily_api_token_cap', 500000));
    }

    /**
     * Estimate token count from text using calibrated Portuguese/Multilingual heuristic.
     * In Portuguese, ~3.6 characters per token accounts for accents and morphology.
     */
    public function estimateTokens(?string $text): int
    {
        if (empty($text)) {
            return 0;
        }

        $charLength = mb_strlen(trim($text), 'UTF-8');
        // Portuguese heuristic: ~3.6 chars per token, minimum 1 token
        return max(1, (int) ceil($charLength / 3.6));
    }

    /**
     * Determine optimal provider based on token volume and context constraints.
     */
    public function determineOptimalProvider(int $estimatedTokens, ?string $preferredProvider = null): array
    {
        // If a specific provider was explicitly requested and isn't 'hybrid', respect unless context exceeds local capacity
        if ($preferredProvider && !in_array($preferredProvider, ['hybrid', 'auto'])) {
            if (in_array($preferredProvider, ['ollama', 'llama']) && $estimatedTokens > 6000) {
                return [
                    'provider' => 'gemini',
                    'tier' => 'heavy_context',
                    'reason' => "Prompt com {$estimatedTokens} tokens excede a janela confortável do Llama local na VPS (8GB). Delegado ao Google Gemini (janela de 1M tokens) para evitar estouro de RAM.",
                    'forced_delegation' => true,
                ];
            }

            return [
                'provider' => $preferredProvider,
                'tier' => $this->classifyTier($estimatedTokens),
                'reason' => "Provedor '{$preferredProvider}' explicitamente selecionado pelo operador.",
                'forced_delegation' => false,
            ];
        }

        // TIER 1: MICRO & TAREFAS LEVES (< 800 tokens)
        // Ideal for local Llama or fast Gemini Free tier
        if ($estimatedTokens <= $this->localMaxThreshold) {
            return [
                'provider' => 'ollama', // ou 'gemini' se Llama offline
                'tier' => 'micro',
                'reason' => "Tarefa curta (~{$estimatedTokens} tokens). Prioriza Llama Local no VPS para poupar cotas de API, com fallback para Gemini Free.",
                'forced_delegation' => false,
            ];
        }

        // TIER 2: TAREFAS MÉDIAS & ROTEIROS (800 a 3500 tokens)
        // Ideal for Google Gemini Free Tier (15 RPM / 1M TPM)
        if ($estimatedTokens <= $this->longContextThreshold) {
            return [
                'provider' => 'gemini',
                'tier' => 'standard',
                'reason' => "Tarefa de porte médio (~{$estimatedTokens} tokens). Delegada à cota gratuita do Google Gemini 1.5 Flash (alta fluência em PT-BR a R$ 0,00).",
                'forced_delegation' => false,
            ];
        }

        // TIER 3: CONTEXTO MASSIVO & LIVROS KDP (> 3500 tokens até 1M tokens)
        // Must go to Gemini 1.5 Flash due to massive 1M token context window
        return [
            'provider' => 'gemini',
            'tier' => 'heavy_context',
            'reason' => "Contexto extenso (~{$estimatedTokens} tokens). Delegado ao Google Gemini 1.5 Flash para aproveitar a janela de 1 milhão de tokens sem degradar a RAM da VPS.",
            'forced_delegation' => true,
        ];
    }

    /**
     * Classify token tier name.
     */
    public function classifyTier(int $tokens): string
    {
        if ($tokens <= $this->localMaxThreshold) {
            return 'micro';
        }
        if ($tokens <= $this->longContextThreshold) {
            return 'standard';
        }
        return 'heavy_context';
    }

    /**
     * Record consumed tokens for daily and monthly analytics.
     */
    public function recordUsage(string $provider, int $tokens): void
    {
        if ($tokens <= 0) return;

        $today = Carbon::today()->format('Y-m-d');
        $thisMonth = Carbon::today()->format('Y-m');

        // Redis / Cache daily key
        $dailyKey = "ai:tokens:daily:{$today}:{$provider}";
        $monthlyKey = "ai:tokens:month:{$thisMonth}:{$provider}";

        try {
            if (Cache::has($dailyKey)) {
                Cache::increment($dailyKey, $tokens);
            } else {
                Cache::put($dailyKey, $tokens, now()->addDays(7));
            }

            if (Cache::has($monthlyKey)) {
                Cache::increment($monthlyKey, $tokens);
            } else {
                Cache::put($monthlyKey, $tokens, now()->addDays(60));
            }
        } catch (\Exception $e) {
            Log::warning('Falha ao registrar métrica de tokens: ' . $e->getMessage());
        }
    }

    /**
     * Get consolidated token usage statistics.
     */
    public function getTokenStats(): array
    {
        $today = Carbon::today()->format('Y-m-d');
        $thisMonth = Carbon::today()->format('Y-m');

        $providers = ['google_gemini', 'openai', 'ollama_llama'];
        $daily = [];
        $monthly = [];
        $totalDaily = 0;
        $totalMonthly = 0;

        foreach ($providers as $prov) {
            $dVal = (int) Cache::get("ai:tokens:daily:{$today}:{$prov}", 0);
            $mVal = (int) Cache::get("ai:tokens:month:{$thisMonth}:{$prov}", 0);

            $daily[$prov] = $dVal;
            $monthly[$prov] = $mVal;

            $totalDaily += $dVal;
            $totalMonthly += $mVal;
        }

        // Calculate economy in BRL (assuming average paid LLM cost of R$ 0,05 per 1k tokens)
        $freeTokensProcessed = ($monthly['google_gemini'] ?? 0) + ($monthly['ollama_llama'] ?? 0);
        $estimatedSavingsBrl = round(($freeTokensProcessed / 1000) * 0.05, 2);

        return [
            'today' => $today,
            'month' => $thisMonth,
            'daily_usage' => $daily,
            'monthly_usage' => $monthly,
            'total_tokens_today' => $totalDaily,
            'total_tokens_month' => $totalMonthly,
            'daily_cap' => $this->dailyApiTokenCap,
            'daily_cap_remaining' => max(0, $this->dailyApiTokenCap - $totalDaily),
            'estimated_savings_brl' => $estimatedSavingsBrl,
            'thresholds' => [
                'micro_max' => $this->localMaxThreshold,
                'long_context_min' => $this->longContextThreshold,
            ],
            'rules' => [
                [
                    'tier' => 'Micro Tarefas (< ' . $this->localMaxThreshold . ' tokens)',
                    'examples' => 'Classificações, títulos curtos, verificação de status, JSONs simples',
                    'primary_target' => 'Llama Local (Ollama)',
                    'advantage' => 'Economiza 100% das cotas de API; resposta instantânea sem tráfego de rede'
                ],
                [
                    'tier' => 'Médio Porte (' . $this->localMaxThreshold . ' a ' . $this->longContextThreshold . ' tokens)',
                    'examples' => 'Roteiros de YouTube Dark (RISADA.exe), posts, descrições, e-mails',
                    'primary_target' => 'Google Gemini Free Tier / OpenAI Fallback',
                    'advantage' => 'Cota gratuita de 15 RPM / 1M TPM no Google AI Studio (Custo R$ 0,00)'
                ],
                [
                    'tier' => 'Contexto Massivo (> ' . $this->longContextThreshold . ' tokens)',
                    'examples' => 'Capítulos completos de livros KDP, transcrições longas, análise de documentos',
                    'primary_target' => 'Google Gemini 1.5 Flash (Janela de 1 Milhão de Tokens)',
                    'advantage' => 'Não estoura os 8GB de RAM da VPS; capacidade de absorver bibliotecas inteiras'
                ]
            ]
        ];
    }
}

