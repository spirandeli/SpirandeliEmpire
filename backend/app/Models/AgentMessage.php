<?php

namespace App\Models;

use App\Enums\AgentMessageRole;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AgentMessage extends Model
{
    protected $fillable = [
        'agent_conversation_id', 'role', 'content', 'parts',
        'tool_name', 'tool_args', 'tool_result', 'tool_failed',
        'prompt_tokens', 'completion_tokens', 'finish_reason', 'latency_ms',
    ];

    protected function casts(): array
    {
        return [
            'role' => AgentMessageRole::class,
            // Payloads dinâmicos do Gemini (functionCall / functionResponse / text parts)
            'parts' => 'array',
            'tool_args' => 'array',
            'tool_result' => 'array',
            'tool_failed' => 'boolean',
            'prompt_tokens' => 'integer',
            'completion_tokens' => 'integer',
            'latency_ms' => 'integer',
        ];
    }

    public function conversation(): BelongsTo
    {
        return $this->belongsTo(AgentConversation::class, 'agent_conversation_id');
    }

    public function isToolMessage(): bool
    {
        return $this->role === AgentMessageRole::Tool;
    }

    /**
     * Converte para o formato `contents[]` da API Gemini.
     * Se `parts` foi salvo, é reaproveitado fielmente (inclui thought signatures e functionCalls).
     *
     * @return array{role: string, parts: array<int, array<string, mixed>>}
     */
    public function toGeminiContent(): array
    {
        $parts = $this->parts ?: [['text' => (string) $this->content]];

        return [
            'role' => $this->role->toGeminiRole(),
            'parts' => $parts,
        ];
    }
}
