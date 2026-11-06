<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\BusinessAutomation */
class BusinessAutomationResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'business_id' => $this->business_id,
            'type' => $this->type,
            'name' => $this->name,
            'cron_expression' => $this->cron_expression,
            'timezone' => $this->timezone,
            'is_enabled' => $this->is_enabled,
            'config' => $this->config,
            'last_run_at' => $this->last_run_at?->toIso8601String(),
            'next_run_at' => $this->next_run_at?->toIso8601String(),
            'last_status' => $this->last_status,
            'last_error' => $this->last_error,
            'run_count' => $this->run_count,
            'failure_count' => $this->failure_count,
        ];
    }
}

