<?php

namespace App\Services\Gemini\Tools;

use App\Models\AgentConversation;
use App\Models\Business;
use App\Models\User;

class ToolExecutionContext
{
    public function __construct(
        public readonly User $user,
        public readonly ?Business $business = null,
        public readonly ?AgentConversation $conversation = null,
    ) {
    }
}

