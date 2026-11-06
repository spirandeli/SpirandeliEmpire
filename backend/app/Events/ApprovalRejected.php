<?php

namespace App\Events;

use App\Models\ApprovalQueue;
use Illuminate\Foundation\Events\Dispatchable;

class ApprovalRejected
{
    use Dispatchable;

    public function __construct(public readonly ApprovalQueue $approval)
    {
    }
}

