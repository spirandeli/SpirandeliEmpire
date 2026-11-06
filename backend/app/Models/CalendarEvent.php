<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class CalendarEvent extends Model
{
    public const PROVIDER_GOOGLE = 'google';
    public const PROVIDER_APPLE = 'apple';

    public const KIND_EVENT = 'event';
    public const KIND_REMINDER = 'reminder';
    public const KIND_TASK = 'task';

    protected $fillable = [
        'user_id', 'user_integration_id', 'task_id', 'provider', 'kind', 'external_id', 'calendar_id', 'etag',
        'title', 'description', 'location', 'starts_at', 'ends_at', 'all_day', 'status',
        'is_completed', 'created_by_agent', 'raw', 'synced_at',
    ];

    protected function casts(): array
    {
        return [
            'starts_at' => 'datetime',
            'ends_at' => 'datetime',
            'synced_at' => 'datetime',
            'all_day' => 'boolean',
            'is_completed' => 'boolean',
            'created_by_agent' => 'boolean',
            'raw' => 'array',
        ];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function integration(): BelongsTo
    {
        return $this->belongsTo(UserIntegration::class, 'user_integration_id');
    }

    public function task(): BelongsTo
    {
        return $this->belongsTo(Task::class);
    }

    /** Itens que se sobrepõem ao intervalo [$from, $to] (usado em `get_user_schedule`). */
    public function scopeBetween(Builder $query, $from, $to): Builder
    {
        return $query->where('status', '!=', 'cancelled')
            ->where('starts_at', '<', $to)
            ->where(fn (Builder $q) => $q->where('ends_at', '>', $from)
                ->orWhere(fn (Builder $q2) => $q2->whereNull('ends_at')->where('starts_at', '>=', $from)));
    }

    public function scopeUpcoming(Builder $query): Builder
    {
        return $query->where('status', '!=', 'cancelled')
            ->where('starts_at', '>=', now())
            ->orderBy('starts_at');
    }
}
