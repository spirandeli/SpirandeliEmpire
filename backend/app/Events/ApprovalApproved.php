<?php

namespace App\Events;

use App\Models\ApprovalQueue;
use Illuminate\Foundation\Events\Dispatchable;

/** Usuário aprovou (e opcionalmente agendou) o pacote. Fase 4 escuta para criar o lembrete de postagem. */
class ApprovalApproved
{
    use Dispatchable;

    public function __construct(public readonly ApprovalQueue $approval)
    {
    }
}

