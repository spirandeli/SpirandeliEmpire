<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\ApprovalQueue */
class ApprovalQueueResource extends JsonResource
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
            'task_id' => $this->task_id,
            'approvable_type' => $this->approvable_type,
            'approvable_id' => $this->approvable_id,
            'type' => $this->type,
            'title' => $this->title,
            'summary' => $this->summary,
            'payload' => $this->payload,
            'status' => $this->status->value,
            'is_reviewable' => $this->status->isReviewable(),
            'priority' => $this->priority,
            'agent_confidence' => $this->agent_confidence !== null ? (float) $this->agent_confidence : null,
            'reviewer_feedback' => $this->reviewer_feedback,
            'revision_count' => $this->revision_count,
            'revision_history' => $this->revision_history,
            'reviewed_at' => $this->reviewed_at?->toIso8601String(),
            'scheduled_for' => $this->scheduled_for?->toIso8601String(),
            'expires_at' => $this->expires_at?->toIso8601String(),
            'created_at' => $this->created_at?->toIso8601String(),
            'updated_at' => $this->updated_at?->toIso8601String(),
        ];
    }
}

