<?php

namespace App\Services\Webhook\DTOs;

use Carbon\Carbon;

class NormalizedWebhookEvent
{
    public function __construct(
        public string $sourcePlatform,
        public string $eventType,
        public ?string $externalTransactionId,
        public float $grossAmount,
        public float $netAmount,
        public ?string $trackingCode,
        public array $customerMetadata,
        public array $payloadRaw,
        public Carbon $occurredAt,
    ) {}

    public function toArray(): array
    {
        return [
            'source_platform' => $this->sourcePlatform,
            'event_type' => $this->eventType,
            'external_transaction_id' => $this->externalTransactionId,
            'gross_amount' => $this->grossAmount,
            'net_amount' => $this->netAmount,
            'tracking_code' => $this->trackingCode,
            'customer_metadata' => $this->customerMetadata,
            'payload_raw' => $this->payloadRaw,
            'occurred_at' => $this->occurredAt,
        ];
    }
}
