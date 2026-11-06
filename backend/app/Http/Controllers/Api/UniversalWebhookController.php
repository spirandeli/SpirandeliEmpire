<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Jobs\AutonomousGrowthOptimizerJob;
use App\Models\Business;
use App\Models\ContentAsset;
use App\Models\ConversionEvent;
use App\Services\Webhook\WebhookNormalizerService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class UniversalWebhookController extends Controller
{
    public function __construct(
        protected WebhookNormalizerService $normalizer
    ) {}

    /**
     * Endpoint público para recepção segura de webhooks externos
     */
    public function handle(Request $request, string $secret_token): JsonResponse
    {
        $business = Business::where('webhook_secret_token', $secret_token)->first();

        if (!$business) {
            return response()->json([
                'error' => 'Webhook secret token inválido ou não cadastrado.',
            ], 404);
        }

        $conversionEvent = $this->normalizer->process($business, $request);

        return response()->json([
            'status' => 'success',
            'message' => 'Evento processado e registrado com sucesso.',
            'event_id' => $conversionEvent->id,
            'source_platform' => $conversionEvent->source_platform,
            'event_type' => $conversionEvent->event_type,
            'gross_amount' => (float) $conversionEvent->gross_amount,
            'attributed_asset_id' => $conversionEvent->content_asset_id,
            'tracking_code' => $conversionEvent->contentAsset?->tracking_code,
        ], 200);
    }

    /**
     * Simula um evento de conversão/venda a partir do painel de controle
     */
    public function simulate(Request $request, Business $business): JsonResponse
    {
        // Garante que o usuário logado é dono do negócio
        if ($request->user() && $business->user_id !== $request->user()->id) {
            return response()->json(['error' => 'Não autorizado.'], 403);
        }

        $conversionEvent = $this->normalizer->process($business, $request);

        return response()->json([
            'status' => 'success',
            'message' => 'Simulação processada com sucesso!',
            'event' => $conversionEvent->load('contentAsset'),
        ], 201);
    }

    /**
     * Dispara manualmente o ciclo OODA de auto-otimização para o negócio
     */
    public function optimizeNow(Request $request, Business $business): JsonResponse
    {
        if ($request->user() && $business->user_id !== $request->user()->id) {
            return response()->json(['error' => 'Não autorizado.'], 403);
        }

        // Executa ou despacha o ciclo OODA
        AutonomousGrowthOptimizerJob::dispatch($business);

        return response()->json([
            'status' => 'success',
            'message' => 'Ciclo de auto-otimização OODA disparado em background pelo Gemini 3.8!',
        ], 202);
    }

    /**
     * Retorna o raio-x completo de métricas de crescimento e funil do negócio
     */
    public function metrics(Request $request, Business $business): JsonResponse
    {
        if ($request->user() && $business->user_id !== $request->user()->id) {
            return response()->json(['error' => 'Não autorizado.'], 403);
        }

        // Agregações de Funil
        $totalViews = (int) $business->contentAssets()->sum('total_views');
        $totalClicks = (int) $business->contentAssets()->sum('total_clicks');
        $totalLeads = (int) $business->contentAssets()->sum('total_leads');

        $totalSales = (int) $business->conversionEvents()
            ->where('event_type', ConversionEvent::EVENT_SALE_APPROVED)
            ->count();

        $totalRevenue = (float) $business->conversionEvents()
            ->where('event_type', ConversionEvent::EVENT_SALE_APPROVED)
            ->sum('gross_amount');

        $abandonedCheckouts = (int) $business->conversionEvents()
            ->whereIn('event_type', [ConversionEvent::EVENT_CHECKOUT_ABANDONED, ConversionEvent::EVENT_PIX_GENERATED])
            ->count();

        $conversionRate = $totalClicks > 0
            ? round(($totalSales / $totalClicks) * 100, 2)
            : ($totalViews > 0 ? round(($totalSales / $totalViews) * 100, 2) : 0.0);

        // Leaderboard de Ativos
        $winningAssets = $business->contentAssets()
            ->current()
            ->where('roi_score', '>', 0)
            ->orderByDesc('roi_score')
            ->take(10)
            ->get();

        $losingAssets = $business->contentAssets()
            ->current()
            ->where('roi_score', '<=', 30)
            ->where('total_views', '>', 50)
            ->orderBy('roi_score')
            ->take(5)
            ->get();

        // Conversões Recentes
        $recentConversions = $business->conversionEvents()
            ->with('contentAsset:id,tracking_code,title,type')
            ->latest('occurred_at')
            ->take(15)
            ->get();

        // Aprendizados do Agente
        $learnings = $business->agentLearnings()
            ->latest()
            ->take(8)
            ->get();

        // Últimos Ciclos OODA
        $cycles = $business->optimizationCycles()
            ->latest()
            ->take(5)
            ->get();

        $webhookUrl = url("/api/webhooks/in/{$business->webhook_secret_token}");

        return response()->json([
            'business' => [
                'id' => $business->id,
                'name' => $business->name,
                'archetype' => $business->archetype,
                'north_star_metric' => $business->north_star_metric,
                'target_kpi_value' => (float) $business->target_kpi_value,
                'webhook_secret_token' => $business->webhook_secret_token,
                'webhook_url' => $webhookUrl,
            ],
            'funnel' => [
                'total_views' => $totalViews,
                'total_clicks' => $totalClicks,
                'total_leads' => $totalLeads,
                'abandoned_checkouts' => $abandonedCheckouts,
                'total_sales' => $totalSales,
                'total_revenue' => $totalRevenue,
                'conversion_rate' => $conversionRate,
            ],
            'winning_assets' => $winningAssets,
            'losing_assets' => $losingAssets,
            'recent_conversions' => $recentConversions,
            'learnings' => $learnings,
            'optimization_cycles' => $cycles,
        ]);
    }
}
