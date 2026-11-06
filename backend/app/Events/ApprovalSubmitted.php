<?php

namespace App\Events;

use App\Models\ApprovalQueue;
use Illuminate\Foundation\Events\Dispatchable;

/** Pacote do agente entrou na Inbox de Supervisão. */
class ApprovalSubmitted
{
    use Dispatchable;

    public function __construct(public readonly ApprovalQueue $approval)
    {
    }
}

