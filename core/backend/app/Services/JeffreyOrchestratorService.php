<?php

namespace App\Services;

use App\Models\AgentDecision;
use App\Models\ApprovalRequest;
use App\Models\JeffreyMemory;
use App\Models\Task;

class JeffreyOrchestratorService
{
    protected AiGatewayService $aiGateway;
    protected BudgetGuardService $budget;

    public function __construct(AiGatewayService $aiGateway, BudgetGuardService $budget)
    {
        $this->aiGateway = $aiGateway;
        $this->budget = $budget;
    }

    /**
     * Process message from user to Jeffrey with memories, safety guardrails and multi-provider AI (Gemini, OpenAI, Llama).
     */
    public function talk(string $message, ?int $businessId = null, ?string $provider = null): array
    {
        // 1. Gather active memories & guidelines
        $memories = JeffreyMemory::where('is_active', true)
            ->where(function ($q) use ($businessId) {
                $q->whereNull('business_id');
                if ($businessId) {
                    $q->orWhere('business_id', $businessId);
                }
            })
            ->pluck('content')
            ->implode("\n- ");

        // 2. Budget verification
        $budgetStatus = $this->budget->getBudgetStatus();

        // 3. System prompt construction
        $systemPrompt = <<<PROMPT
Você é Jeffrey, o agente administrativo central e orquestrador do SpirandeliEmpire OS.
Sua missão: Planejar, estruturar e coordenar múltiplos negócios digitais independentes sob a supervisão do proprietário.

DIRETRIZES FUNDAMENTAIS:
1. Respeite sempre o limite orçamentário mensal de R$ 200,00.
2. Status atual do orçamento: R$ {$budgetStatus['current_spent_brl']} gastos de R$ {$budgetStatus['monthly_limit_brl']}.
3. Priorize planos gratuitos e créditos de IA (Google Gemini Free Tier, OpenAI créditos) combinados com Llama local via Ollama.
4. Jamais invente versículos ou dados inverídicos. Fidelidade total nas histórias bíblicas (RISADA.exe) e KDP.
5. Operações críticas, despesas e publicações exigem autorização explícita do proprietário.

MEMÓRIA OPERACIONAL ATIVA:
- {$memories}

Responda com postura executiva, clara, estratégica e em português brasileiro.
PROMPT;

        // 4. Query AI Gateway (Google Gemini -> OpenAI -> Llama Local)
        $response = $this->aiGateway->generate($message, $systemPrompt, $provider);

        if (!$response['success']) {
            return [
                'reply' => "Olá, Comandante. Os motores de inferência (Google Gemini, OpenAI e Llama local) relataram problemas ou limites de cota no momento. SpirandeliEmpire OS continua operacional. Detalhes: " . ($response['error'] ?? 'Erro desconhecido'),
                'agent' => 'Jeffrey',
                'budget_status' => $budgetStatus,
                'provider' => 'none',
                'model' => 'offline',
            ];
        }

        // 5. Audit decision with provider metadata
        $this->auditDecision(
            'Jeffrey',
            $businessId,
            'chat_interaction',
            'Interação executiva via ' . ($response['provider_name'] ?? 'AI Gateway'),
            [
                'message' => $message,
                'provider' => $response['provider'] ?? 'unknown',
                'model' => $response['model'] ?? 'unknown',
                'latency_ms' => $response['latency_ms'] ?? 0,
                'fallback_used' => $response['fallback_used'] ?? false,
            ]
        );

        return [
            'reply' => $response['response'],
            'agent' => 'Jeffrey',
            'model' => $response['model'] ?? 'unknown',
            'provider' => $response['provider'] ?? 'unknown',
            'provider_name' => $response['provider_name'] ?? 'AI Gateway',
            'latency_ms' => $response['latency_ms'] ?? 0,
            'tokens' => $response['tokens'] ?? null,
            'token_metrics' => $response['token_metrics'] ?? null,
            'fallback_used' => $response['fallback_used'] ?? false,
            'fallback_reason' => $response['fallback_reason'] ?? null,
            'routing' => $response['routing'] ?? null,
            'budget_status' => $budgetStatus,
        ];
    }

    /**
     * Audit log for agent decisions.
     */
    public function auditDecision(string $agentName, ?int $businessId, string $actionType, string $justification, array $payload = []): AgentDecision
    {
        return AgentDecision::create([
            'agent_name' => $agentName,
            'business_id' => $businessId,
            'action_type' => $actionType,
            'justification' => $justification,
            'input_payload' => $payload,
            'status' => 'executed',
        ]);
    }
}
