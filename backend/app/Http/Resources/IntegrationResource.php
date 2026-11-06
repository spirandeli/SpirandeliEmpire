<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/**
 * Representação segura: NUNCA expõe `credentials` nem o hash do webhook token.
 *
 * @mixin \App\Models\UserIntegration
 */
class IntegrationResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'provider' => $this->provider,
            'label' => $this->label,
            'status' => $this->status,
            'connected' => $this->isConnected(),
            'meta' => $this->meta,
            'scopes' => $this->scopes,
            'token_prefix' => $this->token_prefix,
            'expires_at' => $this->expires_at?->toIso8601String(),
            'last_synced_at' => $this->last_synced_at?->toIso8601String(),
            'last_used_at' => $this->last_used_at?->toIso8601String(),
            'last_error' => $this->last_error,
            'created_at' => $this->created_at?->toIso8601String(),
            'updated_at' => $this->updated_at?->toIso8601String(),
        ];
    }
}

