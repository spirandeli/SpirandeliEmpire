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
        $this->tokenRoutingEnabled = (bool) config('ai.tokens.routing_enabled', env('TOKEN_ROUTING_ENABLED', true));
        $this->localMaxThreshold = (int) config('ai.tokens.threshold_local_max', env('TOKEN_THRESHOLD_LOCAL_MAX', 800));
        $this->longContextThreshold = (int) config('ai.tokens.threshold_long_context', env('TOKEN_THRESHOLD_LONG_CONTEXT', 3500));
        $this->dailyApiTokenCap = (int) config('ai.tokens.daily_api_token_cap', env('DAILY_API_TOKEN_CAP', 500000));
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
     * Classify whether the request is a Reading/Analysis task (Llama Local) or an Execution task (Gemini / OpenAI Chat).
     */
    public function classifyTaskRole(?string $text, ?string $explicitRole = null): string
    {
        if ($explicitRole && in_array($explicitRole, ['read_analyze', 'execute_task'], true)) {
            return $explicitRole;
        }
        if (empty($text)) {
            return 'execute_task';
        }

        $lower = mb_strtolower($text, 'UTF-8');

        // Explicit execution triggers (creating, generating scripts, running automations, tool calls)
        $isExecution = (bool) preg_match(
            '/\b(executar|execute|criar|crie|gerar|gere|roteiro|produzir|rodar|campanha|escrever|escreva|implementar|forjar|disparar|publicar|renderizar|tarefa)\b/u',
            $lower
        );

        // Reading & Analysis triggers (reading logs/files, summarizing, classifying, inspecting metrics)
        $isReadAnalyze = (bool) preg_match(
            '/\b(ler|leia|analisar|analise|análise|resumir|resuma|resumo|inspecionar|classificar|classifique|triagem|extrair|verificar\s+status|diagnosticar|interpretar)\b/u',
            $lower
        );

        if ($isReadAnalyze && !$isExecution) {
            return 'read_analyze';
        }

        return 'execute_task';
    }

    /**
     * Determine optimal provider based on task role (Llama = Read/Analyze, Gemini/OpenAI = Execute) and token volume.
     */
    public function determineOptimalProvider(
        int $estimatedTokens,
        ?string $preferredProvider = null,
        ?string $promptText = null,
        ?string $taskRole = null,
        bool $geminiConfigured = true,
        bool $openaiConfigured = false
    ): array {
        $resolvedRole = $this->classifyTaskRole($promptText, $taskRole);

        // If a specific provider was explicitly requested and isn't 'hybrid'/'auto', respect unless context exceeds local capacity
        if ($preferredProvider && !in_array($preferredProvider, ['hybrid', 'auto'])) {
            if (in_array($preferredProvider, ['ollama', 'llama']) && $estimatedTokens > 6000) {
                return [
                    'provider' => $geminiConfigured ? 'gemini' : ($openaiConfigured ? 'openai' : 'ollama'),
                    'tier' => 'heavy_context',
                    'role' => $resolvedRole,
                    'reason' => "Prompt com {$estimatedTokens} tokens excede a janela confortável do Llama local na VPS (8GB). Delegado ao Google Gemini/Chat para evitar estouro de RAM.",
                    'forced_delegation' => true,
                ];
            }

            return [
                'provider' => $preferredProvider,
                'tier' => $this->classifyTier($estimatedTokens),
                'role' => $resolvedRole,
                'reason' => "Provedor '{$preferredProvider}' explicitamente selecionado pelo operador.",
                'forced_delegation' => false,
            ];
        }

        // WHEN GEMINI OR OPENAI API KEY IS CONFIGURED:
        // Directive: Google Gemini is the PRIMARY AI of the system.
        // Llama Local (Ollama) is used ONLY when explicitly requested by the operator.
        if ($geminiConfigured || $openaiConfigured) {
            $cloudExecutor = $geminiConfigured ? 'gemini' : 'openai';
            $cloudLabel = $geminiConfigured ? 'Google Gemini 3.8 Flash' : 'OpenAI ChatGPT';

            return [
                'provider' => $cloudExecutor,
                'tier' => $estimatedTokens > $this->longContextThreshold ? 'heavy_context' : 'task_execution',
                'role' => $resolvedRole,
                'reason' => "Motor Principal Ativo: Processamento (~{$estimatedTokens} tokens) executado diretamente pelo {$cloudLabel}.",
                'forced_delegation' => false,
            ];
        }

        // FALLBACK WHEN NO CLOUD API KEY IS CONFIGURED YET
        if ($estimatedTokens <= $this->localMaxThreshold) {
            return [
                'provider' => 'ollama',
                'tier' => 'micro',
                'role' => $resolvedRole,
                'reason' => "Sem chave Cloud ativa — Tarefa (~{$estimatedTokens} tokens) executada no Llama Local (Ollama).",
                'forced_delegation' => false,
            ];
        }

        return [
            'provider' => 'ollama',
            'tier' => $this->classifyTier($estimatedTokens),
            'role' => $resolvedRole,
            'reason' => "Executando localmente no Llama (configure GEMINI_API_KEY ou OPENAI_API_KEY para ativar a divisão Llama Análise + Gemini/Chat Execução).",
            'forced_delegation' => false,
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
                    'primary_target' => 'Google Gemini 3.8 Flash (Janela de 1 Milhão de Tokens)',
                    'advantage' => 'Não estoura os 8GB de RAM da VPS; capacidade de absorver bibliotecas inteiras'
                ]
            ]
        ];
    }
}

