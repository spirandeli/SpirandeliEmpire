<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\User */
class UserResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'email' => $this->email,
            'timezone' => $this->timezone,
            'locale' => $this->locale,
            'agent_enabled' => $this->agent_enabled,
            'is_admin' => (bool) $this->is_admin,
            'is_ai_active' => (bool) $this->is_ai_active,
            'monthly_token_limit' => (int) $this->monthly_token_limit,
            'tokens_used_this_month' => (int) $this->tokens_used_this_month,
            'settings' => $this->settings,
            'last_login_at' => $this->last_login_at?->toIso8601String(),
            'created_at' => $this->created_at?->toIso8601String(),
        ];
    }
}

