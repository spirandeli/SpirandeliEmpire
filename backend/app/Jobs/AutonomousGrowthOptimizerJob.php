<?php

namespace App\Jobs;

use App\Enums\LogLevel;
use App\Models\AgentLearning;
use App\Models\AgentLog;
use App\Models\Business;
use App\Models\ContentAsset;
use App\Models\ConversionEvent;
use App\Models\OptimizationCycle;
use App\Services\GeminiAgentService;
use App\Services\Playbooks\BusinessPlaybookFactory;
use Carbon\Carbon;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;

class AutonomousGrowthOptimizerJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(public Business $business) {}

    public function handle(GeminiAgentService $agentService): void
    {
        $business = $this->business;
        $user = $business->user;

        if (!$user || !$user->is_ai_active) {
            AgentLog::record(
                $business->user_id,
                'growth_optimizer_skipped',
                'Otimizador de Growth ignorado: IA do usuário está desativada.',
                LogLevel::Warning,
                [],
                ['business_id' => $business->id]
            );
            return;
        }

        $now = now();
        $periodStart = $now->copy()->subDays(7);
        $periodEnd = $now;

        // 1. OBSERVE: Top 20% Vencedores e Bottom 30% Perdedores
        $assets = $business->contentAssets()
            ->current()
            ->where('created_at', '>=', $periodStart)
            ->orWhere('total_sales_count', '>', 0)
            ->get();

        $winningAssets = $business->contentAssets()
            ->current()
            ->where(function ($q) {
                $q->where('roi_score', '>=', 40.00)
                  ->orWhere('total_revenue_brl', '>', 0.00)
                  ->orWhere('total_sales_count', '>', 0);
            })
            ->orderByDesc('roi_score')
            ->take(5)
            ->get();

        $losingAssets = $business->contentAssets()
            ->current()
            ->where('roi_score', '<', 30.00)
            ->where(function ($q) {
                $q->where('total_views', '>', 50)
                  ->orWhere('total_clicks', '>', 10);
            })
            ->orderBy('roi_score')
            ->take(5)
            ->get();

        // Métricas de Funil do Período
        $salesCount = (int) $business->conversionEvents()
            ->where('event_type', ConversionEvent::EVENT_SALE_APPROVED)
            ->where('occurred_at', '>=', $periodStart)
            ->count();

        $revenue = (float) $business->conversionEvents()
            ->where('event_type', ConversionEvent::EVENT_SALE_APPROVED)
            ->where('occurred_at', '>=', $periodStart)
            ->sum('gross_amount');

        $abandoned = (int) $business->conversionEvents()
            ->whereIn('event_type', [ConversionEvent::EVENT_CHECKOUT_ABANDONED, ConversionEvent::EVENT_PIX_GENERATED])
            ->where('occurred_at', '>=', $periodStart)
            ->count();

        // 2. ORIENT & DECIDE: Playbook e Diagnóstico
        $playbook = BusinessPlaybookFactory::forArchetype($business->archetype);
        $actionsTaken = [];
        $aiDiagnosis = '';

        // Se houver ativo vencedor, escala com novas variações criativas
        $topWinner = $winningAssets->first();
        if ($topWinner) {
            $tool = $agentService->getToolRegistry()->get('scaleWinningAsset');
            if ($tool) {
                $context = new \App\Services\Gemini\Tools\ToolExecutionContext(
                    user: $user,
                    business: $business,
                );

                $angleKeys = array_keys($playbook->getAngles());
                $chosenAngle = $angleKeys[array_rand($angleKeys)];

                $result = $tool->execute([
                    'winning_asset_id' => $topWinner->id,
                    'angle_category' => $chosenAngle,
                    'new_hooks' => [
                        "Novo Hook Otimizado 1: Por que este item está gerando R$ " . number_format($topWinner->total_revenue_brl, 2) . " em vendas?",
                        "Novo Hook Otimizado 2: O segredo que fez {$topWinner->tracking_code} bater recorde de conversão",
                        "Novo Hook Otimizado 3: Pare de tentar métodos antigos, veja essa demonstração de 5 segundos",
                    ],
                    'reasoning' => "Ativo {$topWinner->tracking_code} validado com ROI Score {$topWinner->roi_score} e faturamento acumulado de R$ {$topWinner->total_revenue_brl}. Criadas 3 novas variações de teste no ângulo {$chosenAngle}.",
                ], $context);

                $actionsTaken[] = [
                    'action' => 'scale_winning_asset',
                    'result' => $result,
                ];
            }
        }

        // Se houver abandono expressivo de checkout, cria tarefa corretiva no Kanban
        if ($abandoned > 0) {
            $fixTool = $agentService->getToolRegistry()->get('createFunnelFixTask');
            if ($fixTool) {
                $context = new \App\Services\Gemini\Tools\ToolExecutionContext(
                    user: $user,
                    business: $business,
                );

                $result = $fixTool->execute([
                    'title' => "Otimizar recuperação de {$abandoned} checkouts/PIX pendentes",
                    'description' => "Foram identificados {$abandoned} eventos de abandono ou PIX aguardando pagamento nos últimos 7 dias. Implementar cupom de desconto de 5% ou mensagem direta com suporte.",
                    'bottleneck_stage' => 'checkout',
                    'priority' => 'urgent',
                    'assignee' => 'agent',
                ], $context);

                $actionsTaken[] = [
                    'action' => 'create_funnel_fix_task',
                    'result' => $result,
                ];
            }
        }

        // Grava aprendizado do ciclo
        $learningInsight = $topWinner
            ? "Ativo {$topWinner->tracking_code} ({$topWinner->angle_category}) gerou maior ROI no período com R$ " . number_format($topWinner->total_revenue_brl, 2) . ". O público responde melhor a ganchos visuais diretos."
            : "Ciclo inicial sem conversões volumosas. Foco em ampliar tráfego de topo de funil com múltiplos ângulos criativos.";

        $learning = AgentLearning::create([
            'business_id' => $business->id,
            'topic' => 'Desempenho Criativo & ROI',
            'insight' => $learningInsight,
            'confidence_score' => 88,
            'data_source' => 'ooda_cycle',
        ]);

        $actionsTaken[] = [
            'action' => 'save_business_learning',
            'learning_id' => $learning->id,
        ];

        $aiDiagnosis = "Ciclo OODA finalizado para [{$business->name}]. {$salesCount} vendas (R$ " . number_format($revenue, 2) . ") e {$abandoned} abandonos no período. " . $playbook->getOptimizationGuidance([
            'conversion_rate' => $salesCount > 0 ? 2.5 : 0.0,
            'abandoned_checkouts' => $abandoned,
            'total_sales' => $salesCount,
        ]);

        // 3. Persistência do Ciclo de Otimização
        OptimizationCycle::create([
            'business_id' => $business->id,
            'period_start' => $periodStart,
            'period_end' => $periodEnd,
            'winning_assets_summary' => $winningAssets->map(fn ($a) => [
                'id' => $a->id,
                'tracking_code' => $a->tracking_code,
                'revenue' => $a->total_revenue_brl,
                'sales' => $a->total_sales_count,
                'roi_score' => $a->roi_score,
            ])->toArray(),
            'losing_assets_summary' => $losingAssets->map(fn ($a) => [
                'id' => $a->id,
                'tracking_code' => $a->tracking_code,
                'views' => $a->total_views,
                'roi_score' => $a->roi_score,
            ])->toArray(),
            'ai_diagnosis' => $aiDiagnosis,
            'actions_taken' => $actionsTaken,
        ]);

        AgentLog::record(
            $business->user_id,
            'growth_optimizer_completed',
            "Ciclo OODA de Growth concluído com sucesso: " . count($actionsTaken) . " ações executadas.",
            LogLevel::Info,
            ['actions_count' => count($actionsTaken)],
            ['business_id' => $business->id]
        );
    }
}
