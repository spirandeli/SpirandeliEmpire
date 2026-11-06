<?php

namespace App\Services\Webhook\Adapters;

use App\Models\ConversionEvent;
use App\Services\Webhook\Contracts\WebhookPlatformAdapterInterface;
use App\Services\Webhook\DTOs\NormalizedWebhookEvent;
use Carbon\Carbon;
use Illuminate\Http\Request;

class HotmartWebhookAdapter implements WebhookPlatformAdapterInterface
{
    public function getPlatformName(): string
    {
        return ConversionEvent::PLATFORM_HOTMART;
    }

    public function matches(Request $request): bool
    {
        $platformHeader = strtolower((string) $request->header('X-Platform', ''));
        if ($platformHeader === 'hotmart') {
            return true;
        }

        $all = $request->all();
        return isset($all['hottok']) || (isset($all['event']) && str_starts_with((string) $all['event'], 'PURCHASE_'));
    }

    public function normalize(Request $request): NormalizedWebhookEvent
    {
        $data = $request->all();
        $eventRaw = (string) ($data['event'] ?? 'PURCHASE_APPROVED');

        $eventType = match ($eventRaw) {
            'PURCHASE_APPROVED', 'PURCHASE_COMPLETE' => ConversionEvent::EVENT_SALE_APPROVED,
            'PURCHASE_OUT_OF_SHOPPING_CART' => ConversionEvent::EVENT_CHECKOUT_ABANDONED,
            'PURCHASE_BILLET_PRINTED', 'PURCHASE_WAITING_PAYMENT' => ConversionEvent::EVENT_PIX_GENERATED,
            'PURCHASE_REFUNDED', 'PURCHASE_CHARGEBACK' => ConversionEvent::EVENT_REFUND,
            'PURCHASE_CANCELED' => ConversionEvent::EVENT_SUBSCRIPTION_CANCELED,
            default => ConversionEvent::EVENT_SALE_APPROVED,
        };

        $purchase = $data['data']['purchase'] ?? $data['purchase'] ?? [];
        $buyer = $data['data']['buyer'] ?? $data['buyer'] ?? [];
        $transactionId = $purchase['transaction'] ?? $data['id'] ?? (string) ($data['transaction'] ?? null);

        $gross = (float) ($purchase['price']['value'] ?? $purchase['original_offer_price']['value'] ?? $data['price'] ?? 0.0);
        $commissions = $purchase['commission'] ?? [];
        $net = (float) ($commissions['value'] ?? ($gross > 0 ? $gross * 0.90 : 0.0));

        // Extrai tracking_code de UTMs ou SRC/SCK da Hotmart
        $tracking = $purchase['tracking'] ?? $data['tracking'] ?? [];
        $trackingCode = $tracking['source']
            ?? $tracking['source_sck']
            ?? $tracking['external_code']
            ?? $request->input('tracking_code')
            ?? $request->input('utm_content')
            ?? $request->input('src')
            ?? $request->input('sck');

        if ($trackingCode && preg_match('/AST-[A-Z0-9]{4,8}/i', (string) $trackingCode, $matches)) {
            $trackingCode = strtoupper($matches[0]);
        }

        $occurredAt = isset($purchase['order_date'])
            ? Carbon::createFromTimestampMs((int) $purchase['order_date'])
            : now();

        return new NormalizedWebhookEvent(
            sourcePlatform: $this->getPlatformName(),
            eventType: $eventType,
            externalTransactionId: $transactionId,
            grossAmount: $gross,
            netAmount: $net,
            trackingCode: $trackingCode,
            customerMetadata: [
                'name' => $buyer['name'] ?? null,
                'email' => $buyer['email'] ?? null,
                'checkout_phone' => $buyer['checkout_phone'] ?? null,
            ],
            payloadRaw: $data,
            occurredAt: $occurredAt,
        );
    }
}

