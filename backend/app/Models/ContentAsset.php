<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class ContentAsset extends Model
{
    use HasFactory;

    public const TYPE_HOOK = 'hook';
    public const TYPE_VIDEO_SCRIPT = 'video_script';
    public const TYPE_VISUAL_PROMPT = 'visual_prompt';
    public const TYPE_CAPTION = 'caption';
    public const TYPE_HASHTAGS = 'hashtags';
    public const TYPE_CTA = 'cta';
    public const TYPE_THUMBNAIL_PROMPT = 'thumbnail_prompt';

    protected $fillable = [
        'business_id', 'tiktok_product_id', 'approval_queue_id', 'parent_id',
        'type', 'platform', 'title', 'body', 'content', 'version', 'is_selected',
        'status', 'scheduled_at', 'published_at', 'external_url', 'metadata',
    ];

    protected function casts(): array
    {
        return [
            'content' => 'array',
            'metadata' => 'array',
            'version' => 'integer',
            'is_selected' => 'boolean',
            'scheduled_at' => 'datetime',
            'published_at' => 'datetime',
        ];
    }

    public function business(): BelongsTo
    {
        return $this->belongsTo(Business::class);
    }

    public function product(): BelongsTo
    {
        return $this->belongsTo(TikTokProduct::class, 'tiktok_product_id');
    }

    public function approvalQueue(): BelongsTo
    {
        return $this->belongsTo(ApprovalQueue::class);
    }

    public function parent(): BelongsTo
    {
        return $this->belongsTo(self::class, 'parent_id');
    }

    public function revisions(): HasMany
    {
        return $this->hasMany(self::class, 'parent_id');
    }

    /** Apenas versões vigentes (ignora as substituídas por revisões). */
    public function scopeCurrent(Builder $query): Builder
    {
        return $query->where('status', '!=', 'superseded');
    }

    public function scopeOfType(Builder $query, string $type): Builder
    {
        return $query->where('type', $type);
    }

    /**
     * Cria a nova versão deste asset (revisão pedida pelo usuário) e marca a atual como substituída.
     */
    public function createRevision(array $attributes): self
    {
        $this->forceFill(['status' => 'superseded', 'is_selected' => false])->save();

        return static::create(array_merge(
            $this->only([
                'business_id', 'tiktok_product_id', 'approval_queue_id', 'type', 'platform', 'title',
            ]),
            $attributes,
            [
                'parent_id' => $this->id,
                'version' => $this->version + 1,
                'status' => $attributes['status'] ?? 'pending_approval',
            ]
        ));
    }
}
