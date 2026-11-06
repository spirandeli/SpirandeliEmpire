<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\Business */
class BusinessResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'slug' => $this->slug,
            'type' => $this->type,
            'status' => $this->status->value,
            'niche' => $this->niche,
            'description' => $this->description,
            'canvas' => $this->canvas,
            'brand_rules' => $this->brand_rules,
            'goals' => $this->goals,
            'acquisition_channels' => $this->acquisition_channels,
            'automation_playbook' => $this->automation_playbook,
            'kpis' => $this->kpis,
            'metrics' => $this->metrics,
            'ai_summary' => $this->ai_summary,
            'automation_enabled' => $this->automation_enabled,
            'activated_at' => $this->activated_at?->toIso8601String(),
            'created_at' => $this->created_at?->toIso8601String(),
            'updated_at' => $this->updated_at?->toIso8601String(),
            'tasks_open_count' => $this->whenCounted('tasks_open'),
            'pending_approvals_count' => $this->whenCounted('pending_approvals'),
            'tiktok_products_count' => $this->whenCounted('tiktokProducts'),
            'automations' => BusinessAutomationResource::collection($this->whenLoaded('automations')),
            'tiktok_products' => TikTokProductResource::collection($this->whenLoaded('tiktokProducts')),
        ];
    }
}

