<?php

namespace App\Models;

use App\Enums\ApprovalStatus;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\MorphTo;

class ApprovalQueue extends Model
{
    use HasFactory;

    public const TYPE_TIKTOK_CONTENT_PACKAGE = 'tiktok_content_package';
    public const TYPE_BUSINESS_PLAN = 'business_plan';
    public const TYPE_STRATEGY_CHANGE = 'strategy_change';
    public const TYPE_CALENDAR_ACTION = 'calendar_action';
    public const TYPE_GENERIC = 'generic';

    protected $fillable = [
        'business_id', 'user_id', 'task_id', 'approvable_type', 'approvable_id',
        'type', 'title', 'summary', 'payload', 'status', 'priority', 'agent_confidence',
        'reviewer_feedback', 'revision_count', 'revision_history',
        'reviewed_at', 'scheduled_for', 'expires_at',
    ];

    protected function casts(): array
    {
        return [
            'payload' => 'array',
            'revision_history' => 'array',
            'status' => ApprovalStatus::class,
            'agent_confidence' => 'decimal:3',
            'revision_count' => 'integer',
            'reviewed_at' => 'datetime',
            'scheduled_for' => 'datetime',
            'expires_at' => 'datetime',
        ];
    }

    public function business(): BelongsTo
    {
        return $this->belongsTo(Business::class);
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function task(): BelongsTo
    {
        return $this->belongsTo(Task::class);
    }

    public function approvable(): MorphTo
    {
        return $this->morphTo();
    }

    public function contentAssets(): HasMany
    {
        return $this->hasMany(ContentAsset::class);
    }

    // --- Scopes ------------------------------------------------------------------

    /** Inbox de Supervisão: itens aguardando decisão humana. */
    public function scopeAwaitingReview(Builder $query): Builder
    {
        return $query->whereIn('status', [
            ApprovalStatus::Pending->value,
            ApprovalStatus::RevisionRequested->value,
        ]);
    }

    public function scopeWithStatus(Builder $query, ApprovalStatus $status): Builder
    {
        return $query->where('status', $status->value);
    }

    public function scopeExpired(Builder $query): Builder
    {
        return $query->awaitingReview()->whereNotNull('expires_at')->where('expires_at', '<', now());
    }

    public function isReviewable(): bool
    {
        return $this->status->isReviewable();
    }

    /** Registra um pedido de ajuste no histórico (a transição em si é feita pelo Service). */
    public function appendRevisionEntry(string $feedback, ?string $section = null): void
    {
        $history = $this->revision_history ?? [];
        $history[] = [
            'at' => now()->toIso8601String(),
            'feedback' => $feedback,
            'section' => $section,
            'previous_payload_hash' => hash('sha256', json_encode($this->payload)),
        ];

        $this->revision_history = $history;
        $this->revision_count = count($history);
        $this->reviewer_feedback = $feedback;
    }
}
