<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\AgentMessage */
class AgentMessageResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'role' => $this->role->value,
            'content' => $this->content,
            'tool_name' => $this->tool_name,
            'tool_args' => $this->tool_args,
            'tool_result' => $this->tool_result,
            'tool_failed' => $this->tool_failed,
            'prompt_tokens' => $this->prompt_tokens,
            'completion_tokens' => $this->completion_tokens,
            'finish_reason' => $this->finish_reason,
            'latency_ms' => $this->latency_ms,
            'created_at' => $this->created_at?->toIso8601String(),
        ];
    }
}

