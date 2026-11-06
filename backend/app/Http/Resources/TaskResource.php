<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\Task */
class TaskResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'business_id' => $this->business_id,
            'business' => $this->whenLoaded('business', fn () => [
                'id' => $this->business->id,
                'name' => $this->business->name,
            ]),
            'parent_id' => $this->parent_id,
            'title' => $this->title,
            'description' => $this->description,
            'assignee' => $this->assignee->value,
            'assignee_label' => $this->assignee->label(),
            'status' => $this->status->value,
            'status_label' => $this->status->label(),
            'priority' => $this->priority,
            'source' => $this->source,
            'position' => $this->position,
            'due_at' => $this->due_at?->toIso8601String(),
            'scheduled_at' => $this->scheduled_at?->toIso8601String(),
            'started_at' => $this->started_at?->toIso8601String(),
            'completed_at' => $this->completed_at?->toIso8601String(),
            'agent_action' => $this->agent_action,
            'payload' => $this->payload,
            'result' => $this->result,
            'failure_reason' => $this->failure_reason,
            'attempts' => $this->attempts,
            'external_calendar_provider' => $this->external_calendar_provider,
            'created_at' => $this->created_at?->toIso8601String(),
            'updated_at' => $this->updated_at?->toIso8601String(),
        ];
    }
}

