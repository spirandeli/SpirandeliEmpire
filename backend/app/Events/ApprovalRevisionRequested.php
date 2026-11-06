<?php

namespace App\Events;

use App\Models\ApprovalQueue;
use Illuminate\Foundation\Events\Dispatchable;

/**
 * Usuário pediu ajuste. A Fase 3 registra o listener que enfileira o Gemini
 * (queue `agent`) para reescrever apenas a seção indicada em `$section`.
 */
class ApprovalRevisionRequested
{
    use Dispatchable;

    public function __construct(
        public readonly ApprovalQueue $approval,
        public readonly string $feedback,
        public readonly ?string $section = null,
    ) {
    }
}

