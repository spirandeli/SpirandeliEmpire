<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Str;

class AgentConversation extends Model
{
    public const CONTEXT_INCUBATOR = 'incubator';
    public const CONTEXT_BUSINESS_CHAT = 'business_chat';
    public const CONTEXT_AUTONOMOUS_RUN = 'autonomous_run';

    protected $fillable = [
        'uuid', 'user_id', 'business_id', 'title', 'context_type', 'status', 'model',
        'context', 'prompt_tokens', 'completion_tokens', 'messages_count', 'last_message_at',
    ];

    protected function casts(): array
    {
        return [
            'context' => 'array',
            'prompt_tokens' => 'integer',
            'completion_tokens' => 'integer',
            'messages_count' => 'integer',
            'last_message_at' => 'datetime',
        ];
    }

    protected static function booted(): void
    {
        static::creating(function (AgentConversation $conversation) {
            $conversation->uuid ??= (string) Str::uuid();
            $conversation->model ??= config('services.gemini.model', 'gemini-3.8');
        });
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function business(): BelongsTo
    {
        return $this->belongsTo(Business::class);
    }

    public function messages(): HasMany
    {
        return $this->hasMany(AgentMessage::class)->orderBy('id');
    }

    public function logs(): HasMany
    {
        return $this->hasMany(AgentLog::class);
    }

    public function scopeActive(Builder $query): Builder
    {
        return $query->where('status', 'active');
    }

    public function scopeOfContext(Builder $query, string $context): Builder
    {
        return $query->where('context_type', $context);
    }

    /** Contabiliza uso de tokens e atualiza metadados após cada mensagem. */
    public function registerUsage(int $promptTokens = 0, int $completionTokens = 0): void
    {
        $this->increment('messages_count');
        $this->forceFill([
            'prompt_tokens' => $this->prompt_tokens + $promptTokens,
            'completion_tokens' => $this->completion_tokens + $completionTokens,
            'last_message_at' => now(),
        ])->save();
    }
}
