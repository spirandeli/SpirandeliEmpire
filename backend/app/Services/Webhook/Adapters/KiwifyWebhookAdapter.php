<?php

namespace App\Services\Webhook\Adapters;

use App\Models\ConversionEvent;
use App\Services\Webhook\Contracts\WebhookPlatformAdapterInterface;
use App\Services\Webhook\DTOs\NormalizedWebhookEvent;
use Carbon\Carbon;
use Illuminate\Http\Request;

class KiwifyWebhookAdapter implements WebhookPlatformAdapterInterface
{
    public function getPlatformName(): string
    {
        return ConversionEvent::PLATFORM_KIWIFY;
    }

    public function matches(Request $request): bool
    {
        $platformHeader = strtolower((string) $request->header('X-Platform', ''));
        if ($platformHeader === 'kiwify' || $request->hasHeader('X-Kiwify-Signature')) {
            return true;
        }

        $all = $request->all();
        return isset($all['order_id']) && (isset($all['order_status']) || isset($all['TrackingParameters']));
    }

    public function normalize(Request $request): NormalizedWebhookEvent
    {
        $data = $request->all();
        $statusRaw = strtolower((string) ($data['order_status'] ?? 'paid'));
        $paymentMethod = strtolower((string) ($data['payment_method'] ?? ''));

        $eventType = match ($statusRaw) {
            'paid' => ConversionEvent::EVENT_SALE_APPROVED,
            'waiting_payment' => ($paymentMethod === 'pix' || $paymentMethod === 'billet')
                ? ConversionEvent::EVENT_PIX_GENERATED
                : ConversionEvent::EVENT_CHECKOUT_ABANDONED,
            'refunded', 'chargedback' => ConversionEvent::EVENT_REFUND,
            'canceled' => ConversionEvent::EVENT_SUBSCRIPTION_CANCELED,
            default => ConversionEvent::EVENT_SALE_APPROVED,
        };

        $customer = $data['Customer'] ?? $data['customer'] ?? [];
        $commissions = $data['Commissions'] ?? $data['commissions'] ?? [];
        $transactionId = (string) ($data['order_id'] ?? $data['id'] ?? null);

        // Kiwify pode enviar valores em centavos ou decimais (ex: 19700 centavos ou 197.00)
        $chargeAmount = (float) ($commissions['charge_amount'] ?? $data['order_ref'] ?? $data['amount'] ?? 0.0);
        if ($chargeAmount > 1000 && !str_contains((string) $chargeAmount, '.')) {
            $chargeAmount = $chargeAmount / 100.0;
        }

        $myCommission = (float) ($commissions['my_commission'] ?? ($chargeAmount > 0 ? $chargeAmount * 0.90 : 0.0));
        if ($myCommission > 1000 && !str_contains((string) $myCommission, '.')) {
            $myCommission = $myCommission / 100.0;
        }

        // TrackingParameters da Kiwify
        $trackingParams = $data['TrackingParameters'] ?? $data['tracking_parameters'] ?? [];
        $trackingCode = $trackingParams['src']
            ?? $trackingParams['sck']
            ?? $trackingParams['utm_content']
            ?? $trackingParams['utm_source']
            ?? $request->input('tracking_code')
            ?? $request->input('utm_content');

        if ($trackingCode && preg_match('/AST-[A-Z0-9]{4,8}/i', (string) $trackingCode, $matches)) {
            $trackingCode = strtoupper($matches[0]);
        }

        $occurredAt = isset($data['created_at'])
            ? Carbon::parse($data['created_at'])
            : now();

        return new NormalizedWebhookEvent(
            sourcePlatform: $this->getPlatformName(),
            eventType: $eventType,
            externalTransactionId: $transactionId,
            grossAmount: $chargeAmount,
            netAmount: $myCommission,
            trackingCode: $trackingCode,
            customerMetadata: [
                'name' => $customer['full_name'] ?? $customer['name'] ?? null,
                'email' => $customer['email'] ?? null,
                'mobile' => $customer['mobile'] ?? null,
            ],
            payloadRaw: $data,
            occurredAt: $occurredAt,
        );
    }
}
