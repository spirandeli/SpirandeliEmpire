<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\AgentConversation */
class AgentConversationResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'uuid' => $this->uuid,
            'business_id' => $this->business_id,
            'business' => $this->whenLoaded('business', fn () => [
                'id' => $this->business->id,
                'name' => $this->business->name,
                'type' => $this->business->type,
            ]),
            'title' => $this->title,
            'context_type' => $this->context_type,
            'status' => $this->status,
            'model' => $this->model,
            'prompt_tokens' => $this->prompt_tokens,
            'completion_tokens' => $this->completion_tokens,
            'messages_count' => $this->messages_count,
            'last_message_at' => $this->last_message_at?->toIso8601String(),
            'created_at' => $this->created_at?->toIso8601String(),
            'messages' => AgentMessageResource::collection($this->whenLoaded('messages')),
        ];
    }
}

