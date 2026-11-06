<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\AgentLog */
class AgentLogResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'business_id' => $this->business_id,
            'task_id' => $this->task_id,
            'level' => $this->level->value,
            'event' => $this->event,
            'message' => $this->message,
            'context' => $this->context,
            'duration_ms' => $this->duration_ms,
            'created_at' => $this->created_at?->toIso8601String(),
        ];
    }
}

