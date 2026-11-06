<?php

namespace App\Models;

use App\Enums\BusinessStatus;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Support\Str;

class Business extends Model
{
    use HasFactory, SoftDeletes;

    public const TYPE_TIKTOK_SHOP_AFFILIATE = 'tiktok_shop_affiliate';

    public const ARCHETYPE_AFFILIATE_TIKTOK = 'affiliate_tiktok';
    public const ARCHETYPE_INFOPRODUCT = 'infoproduct';
    public const ARCHETYPE_SAAS = 'saas';
    public const ARCHETYPE_ECOMMERCE = 'ecommerce';
    public const ARCHETYPE_CONTENT_MEDIA = 'content_media';
    public const ARCHETYPE_SERVICE_AGENCY = 'service_agency';

    protected $fillable = [
        'user_id', 'name', 'slug', 'type', 'status', 'niche', 'description',
        'archetype', 'north_star_metric', 'target_kpi_value', 'webhook_secret_token',
        'canvas', 'brand_rules', 'goals', 'acquisition_channels', 'automation_playbook',
        'kpis', 'metrics', 'ai_summary', 'automation_enabled', 'activated_at',
    ];

    protected function casts(): array
    {
        return [
            'status' => BusinessStatus::class,
            'target_kpi_value' => 'decimal:2',
            'canvas' => 'array',
            'brand_rules' => 'array',
            'goals' => 'array',
            'acquisition_channels' => 'array',
            'automation_playbook' => 'array',
            'kpis' => 'array',
            'metrics' => 'array',
            'automation_enabled' => 'boolean',
            'activated_at' => 'datetime',
        ];
    }

    protected static function booted(): void
    {
        static::creating(function (Business $business) {
            if (empty($business->slug)) {
                $business->slug = static::uniqueSlugFor($business->user_id, $business->name);
            }

            if (empty($business->webhook_secret_token)) {
                $business->webhook_secret_token = 'whsec_' . Str::random(36);
            }

            if (empty($business->archetype)) {
                $business->archetype = self::ARCHETYPE_AFFILIATE_TIKTOK;
            }
        });
    }

    public static function uniqueSlugFor(int $userId, string $name): string
    {
        $base = Str::slug($name) ?: 'negocio';
        $slug = $base;
        $i = 2;

        while (static::withTrashed()->where('user_id', $userId)->where('slug', $slug)->exists()) {
            $slug = "{$base}-{$i}";
            $i++;
        }

        return $slug;
    }

    // --- Relacionamentos -------------------------------------------------------

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function automations(): HasMany
    {
        return $this->hasMany(BusinessAutomation::class);
    }

    public function tasks(): HasMany
    {
        return $this->hasMany(Task::class);
    }

    public function approvalQueues(): HasMany
    {
        return $this->hasMany(ApprovalQueue::class);
    }

    public function tiktokProducts(): HasMany
    {
        return $this->hasMany(TikTokProduct::class);
    }

    public function products(): HasMany
    {
        return $this->tiktokProducts();
    }

    public function contentAssets(): HasMany
    {
        return $this->hasMany(ContentAsset::class);
    }

    public function conversations(): HasMany
    {
        return $this->hasMany(AgentConversation::class);
    }

    public function agentLogs(): HasMany
    {
        return $this->hasMany(AgentLog::class);
    }

    public function conversionEvents(): HasMany
    {
        return $this->hasMany(ConversionEvent::class);
    }

    public function optimizationCycles(): HasMany
    {
        return $this->hasMany(OptimizationCycle::class);
    }

    public function agentLearnings(): HasMany
    {
        return $this->hasMany(AgentLearning::class);
    }

    // --- Scopes ------------------------------------------------------------------

    public function scopeActive(Builder $query): Builder
    {
        return $query->where('status', BusinessStatus::Active->value);
    }

    /** Negócios que o scheduler pode operar sozinho. */
    public function scopeAutonomous(Builder $query): Builder
    {
        return $query->active()->where('automation_enabled', true);
    }

    public function scopeOfType(Builder $query, string $type): Builder
    {
        return $query->where('type', $type);
    }

    public function scopeOfArchetype(Builder $query, string $archetype): Builder
    {
        return $query->where('archetype', $archetype);
    }

    public function isTikTokShopAffiliate(): bool
    {
        return $this->type === self::TYPE_TIKTOK_SHOP_AFFILIATE || $this->archetype === self::ARCHETYPE_AFFILIATE_TIKTOK;
    }

    public function getRouteKeyName(): string
    {
        return 'id';
    }
}
