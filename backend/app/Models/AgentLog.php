<?php

namespace App\Models;

use App\Enums\LogLevel;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AgentLog extends Model
{
    /** Tabela append-only: sem `updated_at`. */
    public const UPDATED_AT = null;

    protected $fillable = [
        'user_id', 'business_id', 'task_id', 'agent_conversation_id', 'business_automation_id',
        'level', 'event', 'message', 'context', 'duration_ms',
    ];

    protected function casts(): array
    {
        return [
            'level' => LogLevel::class,
            'context' => 'array',
            'duration_ms' => 'integer',
            'created_at' => 'datetime',
        ];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function business(): BelongsTo
    {
        return $this->belongsTo(Business::class);
    }

    public function task(): BelongsTo
    {
        return $this->belongsTo(Task::class);
    }

    public function conversation(): BelongsTo
    {
        return $this->belongsTo(AgentConversation::class, 'agent_conversation_id');
    }

    public function automation(): BelongsTo
    {
        return $this->belongsTo(BusinessAutomation::class, 'business_automation_id');
    }

    /** Helper de escrita usado por Services e Jobs. */
    public static function record(
        int $userId,
        string $event,
        string $message,
        LogLevel $level = LogLevel::Info,
        array $context = [],
        array $refs = [],
        ?int $durationMs = null,
    ): self {
        return static::create(array_merge([
            'user_id' => $userId,
            'event' => $event,
            'message' => mb_substr($message, 0, 1000),
            'level' => $level,
            'context' => $context ?: null,
            'duration_ms' => $durationMs,
        ], array_intersect_key($refs, array_flip([
            'business_id', 'task_id', 'agent_conversation_id', 'business_automation_id',
        ]))));
    }

    /** Polling incremental do console em tempo real: logs com id > $lastId. */
    public function scopeAfter(Builder $query, int $lastId): Builder
    {
        return $query->where('id', '>', $lastId)->orderBy('id');
    }
}
