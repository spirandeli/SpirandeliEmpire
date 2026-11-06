<?php

namespace App\Services\Webhook\Contracts;

use App\Services\Webhook\DTOs\NormalizedWebhookEvent;
use Illuminate\Http\Request;

interface WebhookPlatformAdapterInterface
{
    /**
     * Verifica se o payload/headers da requisição pertencem a esta plataforma.
     */
    public function matches(Request $request): bool;

    /**
     * Converte a requisição da plataforma em um NormalizedWebhookEvent padronizado.
     */
    public function normalize(Request $request): NormalizedWebhookEvent;

    /**
     * Identificador da plataforma (ex: hotmart, kiwify, stripe, etc.)
     */
    public function getPlatformName(): string;
}

