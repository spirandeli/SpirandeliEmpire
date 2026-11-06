<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\MorphMany;

class TikTokProduct extends Model
{
    use HasFactory;

    protected $table = 'tiktok_products';

    public const STATUS_MINED = 'mined';
    public const STATUS_ANALYZING = 'analyzing';
    public const STATUS_SELECTED = 'selected';
    public const STATUS_CONTENT_READY = 'content_ready';
    public const STATUS_PUBLISHED = 'published';
    public const STATUS_DISCARDED = 'discarded';

    protected $fillable = [
        'business_id', 'external_id', 'source', 'title', 'category', 'shop_name',
        'image_url', 'product_url', 'affiliate_link',
        'price', 'currency', 'commission_rate', 'commission_value',
        'sales_count', 'sales_velocity', 'rating', 'reviews_count',
        'margin_score', 'velocity_score', 'viral_score', 'overall_score',
        'status', 'raw_data', 'ai_analysis', 'mined_at', 'selected_at',
    ];

    protected function casts(): array
    {
        return [
            'price' => 'decimal:2',
            'commission_rate' => 'decimal:2',
            'commission_value' => 'decimal:2',
            'sales_velocity' => 'decimal:2',
            'rating' => 'decimal:2',
            'sales_count' => 'integer',
            'reviews_count' => 'integer',
            'margin_score' => 'integer',
            'velocity_score' => 'integer',
            'viral_score' => 'integer',
            'overall_score' => 'integer',
            'raw_data' => 'array',
            'ai_analysis' => 'array',
            'mined_at' => 'datetime',
            'selected_at' => 'datetime',
        ];
    }

    public function business(): BelongsTo
    {
        return $this->belongsTo(Business::class);
    }

    public function contentAssets(): HasMany
    {
        return $this->hasMany(ContentAsset::class, 'tiktok_product_id');
    }

    public function approvalQueues(): MorphMany
    {
        return $this->morphMany(ApprovalQueue::class, 'approvable');
    }

    public function scopeWithStatus(Builder $query, string $status): Builder
    {
        return $query->where('status', $status);
    }

    /** Candidatos à análise do Gemini: bem pontuados e ainda não trabalhados. */
    public function scopeCandidates(Builder $query, int $minScore = 0): Builder
    {
        return $query->where('status', self::STATUS_MINED)
            ->where('overall_score', '>=', $minScore)
            ->orderByDesc('overall_score');
    }

    /**
     * Score geral ponderado (0-100): margem 35%, velocidade 30%, viralidade 35%.
     * O Gemini pode refinar `viral_score` depois; o overall é recalculado.
     */
    public function recalculateOverallScore(): int
    {
        $this->overall_score = (int) round(
            $this->margin_score * 0.35 + $this->velocity_score * 0.30 + $this->viral_score * 0.35
        );

        return $this->overall_score;
    }
}
