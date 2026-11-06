<?php

namespace App\Services\Webhook\Adapters;

use App\Models\ConversionEvent;
use App\Services\Webhook\Contracts\WebhookPlatformAdapterInterface;
use App\Services\Webhook\DTOs\NormalizedWebhookEvent;
use Carbon\Carbon;
use Illuminate\Http\Request;

class GenericWebhookAdapter implements WebhookPlatformAdapterInterface
{
    public function getPlatformName(): string
    {
        return ConversionEvent::PLATFORM_CUSTOM;
    }

    public function matches(Request $request): bool
    {
        // Fallback default adapter
        return true;
    }

    public function normalize(Request $request): NormalizedWebhookEvent
    {
        $data = $request->all();
        $eventRaw = strtolower((string) ($data['event_type'] ?? $data['event'] ?? $data['status'] ?? 'sale_approved'));

        $eventType = match ($eventRaw) {
            'sale', 'sale_approved', 'approved', 'paid', 'purchase' => ConversionEvent::EVENT_SALE_APPROVED,
            'checkout_abandoned', 'abandoned', 'abandon' => ConversionEvent::EVENT_CHECKOUT_ABANDONED,
            'pix_generated', 'waiting_payment', 'pending' => ConversionEvent::EVENT_PIX_GENERATED,
            'lead', 'subscribed', 'signup' => ConversionEvent::EVENT_LEAD,
            'click', 'traffic' => ConversionEvent::EVENT_CLICK,
            'refund', 'refunded' => ConversionEvent::EVENT_REFUND,
            'subscription_canceled', 'canceled' => ConversionEvent::EVENT_SUBSCRIPTION_CANCELED,
            default => ConversionEvent::EVENT_SALE_APPROVED,
        };

        $transactionId = (string) ($data['external_transaction_id'] ?? $data['transaction_id'] ?? $data['id'] ?? $data['order_id'] ?? null);
        $gross = (float) ($data['gross_amount'] ?? $data['amount'] ?? $data['value'] ?? $data['price'] ?? 0.0);
        $net = (float) ($data['net_amount'] ?? $data['commission'] ?? ($gross > 0 ? $gross * 0.90 : 0.0));

        $trackingCode = $data['tracking_code']
            ?? $data['utm_content']
            ?? $data['src']
            ?? $data['sck']
            ?? $request->input('tracking_code');

        if ($trackingCode && preg_match('/AST-[A-Z0-9]{4,8}/i', (string) $trackingCode, $matches)) {
            $trackingCode = strtoupper($matches[0]);
        }

        $occurredAt = isset($data['occurred_at'])
            ? Carbon::parse($data['occurred_at'])
            : now();

        return new NormalizedWebhookEvent(
            sourcePlatform: (string) ($data['source_platform'] ?? $this->getPlatformName()),
            eventType: $eventType,
            externalTransactionId: $transactionId,
            grossAmount: $gross,
            netAmount: $net,
            trackingCode: $trackingCode,
            customerMetadata: [
                'name' => $data['customer_name'] ?? $data['name'] ?? null,
                'email' => $data['customer_email'] ?? $data['email'] ?? null,
                'phone' => $data['customer_phone'] ?? $data['phone'] ?? null,
            ],
            payloadRaw: $data,
            occurredAt: $occurredAt,
        );
    }
}

