<?php

namespace App\Services\Webhook\Adapters;

use App\Models\ConversionEvent;
use App\Services\Webhook\Contracts\WebhookPlatformAdapterInterface;
use App\Services\Webhook\DTOs\NormalizedWebhookEvent;
use Carbon\Carbon;
use Illuminate\Http\Request;

class StripeWebhookAdapter implements WebhookPlatformAdapterInterface
{
    public function getPlatformName(): string
    {
        return ConversionEvent::PLATFORM_STRIPE;
    }

    public function matches(Request $request): bool
    {
        $platformHeader = strtolower((string) $request->header('X-Platform', ''));
        if ($platformHeader === 'stripe' || $request->hasHeader('Stripe-Signature')) {
            return true;
        }

        $all = $request->all();
        return isset($all['object']) && $all['object'] === 'event' && isset($all['data']);
    }

    public function normalize(Request $request): NormalizedWebhookEvent
    {
        $data = $request->all();
        $eventTypeRaw = (string) ($data['type'] ?? 'checkout.session.completed');

        $eventType = match ($eventTypeRaw) {
            'checkout.session.completed', 'payment_intent.succeeded', 'invoice.paid' => ConversionEvent::EVENT_SALE_APPROVED,
            'checkout.session.expired' => ConversionEvent::EVENT_CHECKOUT_ABANDONED,
            'charge.refunded' => ConversionEvent::EVENT_REFUND,
            'customer.subscription.deleted' => ConversionEvent::EVENT_SUBSCRIPTION_CANCELED,
            default => ConversionEvent::EVENT_SALE_APPROVED,
        };

        $obj = $data['data']['object'] ?? [];
        $transactionId = (string) ($obj['id'] ?? $data['id'] ?? null);

        // Stripe envia em centavos (ex: 29700 para R$ 297,00)
        $amountCents = (int) ($obj['amount_total'] ?? $obj['amount'] ?? 0);
        $gross = round($amountCents / 100.0, 2);
        $net = round($gross * 0.95, 2); // Estimativa padrão Stripe ~95% líquido

        $metadata = $obj['metadata'] ?? [];
        $trackingCode = $metadata['tracking_code']
            ?? $metadata['utm_content']
            ?? $metadata['src']
            ?? ($obj['client_reference_id'] ?? null)
            ?? $request->input('tracking_code');

        if ($trackingCode && preg_match('/AST-[A-Z0-9]{4,8}/i', (string) $trackingCode, $matches)) {
            $trackingCode = strtoupper($matches[0]);
        }

        $customerDetails = $obj['customer_details'] ?? [];
        $occurredAt = isset($data['created'])
            ? Carbon::createFromTimestamp((int) $data['created'])
            : now();

        return new NormalizedWebhookEvent(
            sourcePlatform: $this->getPlatformName(),
            eventType: $eventType,
            externalTransactionId: $transactionId,
            grossAmount: $gross,
            netAmount: $net,
            trackingCode: $trackingCode,
            customerMetadata: [
                'name' => $customerDetails['name'] ?? null,
                'email' => $customerDetails['email'] ?? ($obj['customer_email'] ?? null),
                'customer_id' => $obj['customer'] ?? null,
            ],
            payloadRaw: $data,
            occurredAt: $occurredAt,
        );
    }
}
