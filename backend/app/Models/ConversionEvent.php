<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ConversionEvent extends Model
{
    use HasFactory;

    public const PLATFORM_TIKTOK_SHOP = 'tiktok_shop';
    public const PLATFORM_HOTMART = 'hotmart';
    public const PLATFORM_KIWIFY = 'kiwify';
    public const PLATFORM_STRIPE = 'stripe';
    public const PLATFORM_SHOPIFY = 'shopify';
    public const PLATFORM_CUSTOM = 'custom_webhook';

    public const EVENT_CLICK = 'click';
    public const EVENT_LEAD = 'lead';
    public const EVENT_CHECKOUT_ABANDONED = 'checkout_abandoned';
    public const EVENT_PIX_GENERATED = 'pix_generated';
    public const EVENT_SALE_APPROVED = 'sale_approved';
    public const EVENT_REFUND = 'refund';
    public const EVENT_SUBSCRIPTION_CANCELED = 'subscription_canceled';

    protected $fillable = [
        'business_id',
        'content_asset_id',
        'source_platform',
        'event_type',
        'external_transaction_id',
        'gross_amount',
        'net_amount',
        'customer_metadata',
        'payload_raw',
        'occurred_at',
    ];

    protected function casts(): array
    {
        return [
            'gross_amount' => 'decimal:2',
            'net_amount' => 'decimal:2',
            'customer_metadata' => 'array',
            'payload_raw' => 'array',
            'occurred_at' => 'datetime',
        ];
    }

    public function business(): BelongsTo
    {
        return $this->belongsTo(Business::class);
    }

    public function contentAsset(): BelongsTo
    {
        return $this->belongsTo(ContentAsset::class);
    }

    public function isSale(): bool
    {
        return $this->event_type === self::EVENT_SALE_APPROVED;
    }

    public function isAbandonedCheckout(): bool
    {
        return in_array($this->event_type, [self::EVENT_CHECKOUT_ABANDONED, self::EVENT_PIX_GENERATED], true);
    }
}
