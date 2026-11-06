<?php

namespace App\Services\Webhook\Adapters;

use App\Models\ConversionEvent;
use App\Services\Webhook\Contracts\WebhookPlatformAdapterInterface;
use App\Services\Webhook\DTOs\NormalizedWebhookEvent;
use Carbon\Carbon;
use Illuminate\Http\Request;

class ShopifyWebhookAdapter implements WebhookPlatformAdapterInterface
{
    public function getPlatformName(): string
    {
        return ConversionEvent::PLATFORM_SHOPIFY;
    }

    public function matches(Request $request): bool
    {
        $platformHeader = strtolower((string) $request->header('X-Platform', ''));
        return $platformHeader === 'shopify' || $request->hasHeader('X-Shopify-Topic') || $request->hasHeader('X-Shopify-Hmac-Sha256');
    }

    public function normalize(Request $request): NormalizedWebhookEvent
    {
        $data = $request->all();
        $topic = strtolower((string) $request->header('X-Shopify-Topic', 'orders/paid'));
        $financialStatus = strtolower((string) ($data['financial_status'] ?? 'paid'));

        $eventType = match (true) {
            str_contains($topic, 'checkouts') => ConversionEvent::EVENT_CHECKOUT_ABANDONED,
            str_contains($topic, 'refunds') || $financialStatus === 'refunded' => ConversionEvent::EVENT_REFUND,
            str_contains($topic, 'cancelled') => ConversionEvent::EVENT_SUBSCRIPTION_CANCELED,
            default => ConversionEvent::EVENT_SALE_APPROVED,
        };

        $transactionId = (string) ($data['id'] ?? $data['order_number'] ?? null);
        $gross = (float) ($data['total_price'] ?? $data['current_total_price'] ?? $data['total_price_usd'] ?? 0.0);
        $net = round($gross * 0.92, 2); // Estimativa de taxa líquida

        $customer = $data['customer'] ?? [];
        $noteAttributes = $data['note_attributes'] ?? [];
        $trackingCode = null;

        if (is_array($noteAttributes)) {
            foreach ($noteAttributes as $attr) {
                if (isset($attr['name']) && in_array(strtolower($attr['name']), ['tracking_code', 'utm_content', 'src'], true)) {
                    $trackingCode = $attr['value'] ?? null;
                    break;
                }
            }
        }

        if (!$trackingCode) {
            $trackingCode = $data['landing_site_ref'] ?? $request->input('tracking_code') ?? $request->input('utm_content');
        }

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
            grossAmount: $gross,
            netAmount: $net,
            trackingCode: $trackingCode,
            customerMetadata: [
                'name' => trim(($customer['first_name'] ?? '') . ' ' . ($customer['last_name'] ?? '')),
                'email' => $customer['email'] ?? ($data['email'] ?? null),
                'phone' => $customer['phone'] ?? ($data['phone'] ?? null),
            ],
            payloadRaw: $data,
            occurredAt: $occurredAt,
        );
    }
}
