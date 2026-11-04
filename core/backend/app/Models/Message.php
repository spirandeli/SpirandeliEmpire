<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Message extends Model
{
    protected $fillable = [
        'conversation_id',
        'role', // user, assistant, system, tool
        'content',
        'provider',
        'model',
        'latency_ms',
        'tokens',
        'tool_calls',
        'tool_results',
        'error_message',
        'fallback_used',
        'fallback_reason',
    ];

    protected $casts = [
        'latency_ms' => 'integer',
        'tokens' => 'array',
        'tool_calls' => 'array',
        'tool_results' => 'array',
        'fallback_used' => 'boolean',
    ];

    protected $appends = [
        'attachments',
    ];

    public function getAttachmentsAttribute(): array
    {
        if (is_array($this->tokens) && isset($this->tokens['attachments']) && is_array($this->tokens['attachments'])) {
            return $this->tokens['attachments'];
        }
        return [];
    }

    public function conversation()
    {
        return $this->belongsTo(Conversation::class);
    }
}
