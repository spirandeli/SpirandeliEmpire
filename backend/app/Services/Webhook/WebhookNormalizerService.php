<?php

namespace App\Services\Webhook;

use App\Jobs\HandleFunnelRecoveryJob;
use App\Models\Business;
use App\Models\ContentAsset;
use App\Models\ConversionEvent;
use App\Services\Webhook\Adapters\GenericWebhookAdapter;
use App\Services\Webhook\Adapters\HotmartWebhookAdapter;
use App\Services\Webhook\Adapters\KiwifyWebhookAdapter;
use App\Services\Webhook\Adapters\ShopifyWebhookAdapter;
use App\Services\Webhook\Adapters\StripeWebhookAdapter;
use App\Services\Webhook\Adapters\TikTokShopWebhookAdapter;
use App\Services\Webhook\Contracts\WebhookPlatformAdapterInterface;
use App\Services\Webhook\DTOs\NormalizedWebhookEvent;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;

class WebhookNormalizerService
{
    /** @var WebhookPlatformAdapterInterface[] */
    protected array $adapters;

    public function __construct()
    {
        $this->adapters = [
            new HotmartWebhookAdapter(),
            new KiwifyWebhookAdapter(),
            new StripeWebhookAdapter(),
            new ShopifyWebhookAdapter(),
            new TikTokShopWebhookAdapter(),
            new GenericWebhookAdapter(), // Fallback deve ser o último
        ];
    }

    /**
     * Identifica o adaptador correto para a requisição
     */
    public function resolveAdapter(Request $request): WebhookPlatformAdapterInterface
    {
        foreach ($this->adapters as $adapter) {
            if ($adapter->matches($request)) {
                return $adapter;
            }
        }

        return new GenericWebhookAdapter();
    }

    /**
     * Normaliza e processa a requisição de webhook para um negócio específico
     */
    public function process(Business $business, Request $request): ConversionEvent
    {
        $adapter = $this->resolveAdapter($request);
        $normalized = $adapter->normalize($request);

        return DB::transaction(function () use ($business, $normalized) {
            // Prevenção de duplicidade: se o mesmo evento externo já foi gravado, atualiza
            if ($normalized->externalTransactionId) {
                $existing = ConversionEvent::where('business_id', $business->id)
                    ->where('source_platform', $normalized->sourcePlatform)
                    ->where('external_transaction_id', $normalized->externalTransactionId)
                    ->where('event_type', $normalized->eventType)
                    ->first();

                if ($existing) {
                    $existing->update([
                        'payload_raw' => $normalized->payloadRaw,
                        'customer_metadata' => $normalized->customerMetadata,
                    ]);
                    return $existing;
                }
            }

            // Atribuição de Ativo (ContentAsset) por Tracking Code
            $contentAsset = null;
            if ($normalized->trackingCode) {
                $contentAsset = ContentAsset::where('business_id', $business->id)
                    ->where('tracking_code', $normalized->trackingCode)
                    ->first();

                // Se não encontrar direto, tenta sem prefixo ou com LIKE
                if (!$contentAsset) {
                    $contentAsset = ContentAsset::where('business_id', $business->id)
                        ->where('tracking_code', 'LIKE', '%' . $normalized->trackingCode . '%')
                        ->first();
                }
            }

            // Cria o registro no Ledger Universal
            $conversionEvent = ConversionEvent::create([
                'business_id' => $business->id,
                'content_asset_id' => $contentAsset?->id,
                'source_platform' => $normalized->sourcePlatform,
                'event_type' => $normalized->eventType,
                'external_transaction_id' => $normalized->externalTransactionId,
                'gross_amount' => $normalized->grossAmount,
                'net_amount' => $normalized->netAmount,
                'customer_metadata' => $normalized->customerMetadata,
                'payload_raw' => $normalized->payloadRaw,
                'occurred_at' => $normalized->occurredAt,
            ]);

            // Se atribuído a um ContentAsset, atualiza métricas e recalcula ROI
            if ($contentAsset) {
                $this->updateAssetMetrics($contentAsset, $conversionEvent);
            }

            // Se for abandono de carrinho ou PIX gerado, dispara job de recuperação
            if ($conversionEvent->isAbandonedCheckout()) {
                HandleFunnelRecoveryJob::dispatch($conversionEvent);
            }

            return $conversionEvent;
        });
    }

    /**
     * Atualiza as métricas acumuladas do ativo e dispara o cálculo de ROI
     */
    protected function updateAssetMetrics(ContentAsset $asset, ConversionEvent $event): void
    {
        switch ($event->event_type) {
            case ConversionEvent::EVENT_SALE_APPROVED:
                $asset->total_sales_count += 1;
                $asset->total_revenue_brl += (float) $event->gross_amount;
                break;

            case ConversionEvent::EVENT_CLICK:
                $asset->total_clicks += 1;
                break;

            case ConversionEvent::EVENT_LEAD:
                $asset->total_leads += 1;
                break;

            case ConversionEvent::EVENT_REFUND:
                $asset->total_sales_count = max(0, $asset->total_sales_count - 1);
                $asset->total_revenue_brl = max(0.00, (float) $asset->total_revenue_brl - (float) $event->gross_amount);
                break;
        }

        $asset->saveQuietly();
        $asset->recalculateRoiScore();
    }
}
