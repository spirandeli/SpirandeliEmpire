<?php

namespace App\Services\Webhook\Adapters;

use App\Models\ConversionEvent;
use App\Services\Webhook\Contracts\WebhookPlatformAdapterInterface;
use App\Services\Webhook\DTOs\NormalizedWebhookEvent;
use Carbon\Carbon;
use Illuminate\Http\Request;

class TikTokShopWebhookAdapter implements WebhookPlatformAdapterInterface
{
    public function getPlatformName(): string
    {
        return ConversionEvent::PLATFORM_TIKTOK_SHOP;
    }

    public function matches(Request $request): bool
    {
        $platformHeader = strtolower((string) $request->header('X-Platform', ''));
        if ($platformHeader === 'tiktok_shop' || $platformHeader === 'tiktok') {
            return true;
        }

        $all = $request->all();
        return isset($all['shop_id']) || (isset($all['type']) && isset($all['data']['order_id'])) || (isset($all['event']) && str_contains(strtolower((string) $all['event']), 'tiktok'));
    }

    public function normalize(Request $request): NormalizedWebhookEvent
    {
        $data = $request->all();
        $orderData = $data['data'] ?? $data['order'] ?? $data;
        $statusRaw = strtoupper((string) ($orderData['order_status'] ?? $data['order_status'] ?? 'PAID'));

        $eventType = match ($statusRaw) {
            'PAID', 'AWAITING_SHIPMENT', 'SHIPPED', 'COMPLETED' => ConversionEvent::EVENT_SALE_APPROVED,
            'UNPAID', 'AWAITING_PAYMENT' => ConversionEvent::EVENT_CHECKOUT_ABANDONED,
            'CANCELLED', 'REFUNDED' => ConversionEvent::EVENT_REFUND,
            default => ConversionEvent::EVENT_SALE_APPROVED,
        };

        $transactionId = (string) ($orderData['order_id'] ?? $data['order_id'] ?? $data['id'] ?? null);
        $payment = $orderData['payment'] ?? [];
        $gross = (float) ($payment['total_amount'] ?? $orderData['total_amount'] ?? $data['gross_amount'] ?? 0.0);
        $commission = (float) ($orderData['affiliate_commission'] ?? $payment['affiliate_commission'] ?? ($gross * 0.20)); // comissão média tiktok ~20%

        $trackingCode = $orderData['buyer_message']
            ?? $orderData['traffic_source']
            ?? $request->input('tracking_code')
            ?? $request->input('utm_content');

        if ($trackingCode && preg_match('/AST-[A-Z0-9]{4,8}/i', (string) $trackingCode, $matches)) {
            $trackingCode = strtoupper($matches[0]);
        }

        $occurredAt = isset($orderData['create_time'])
            ? Carbon::createFromTimestamp((int) $orderData['create_time'])
            : now();

        return new NormalizedWebhookEvent(
            sourcePlatform: $this->getPlatformName(),
            eventType: $eventType,
            externalTransactionId: $transactionId,
            grossAmount: $gross,
            netAmount: $commission,
            trackingCode: $trackingCode,
            customerMetadata: [
                'buyer_uid' => $orderData['buyer_uid'] ?? null,
                'shipping_country' => $orderData['recipient_address']['region_code'] ?? 'BR',
            ],
            payloadRaw: $data,
            occurredAt: $occurredAt,
        );
    }
}
