<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class AgentDecision extends Model
{
    protected $fillable = [
        'agent_name',
        'business_id',
        'action_type',
        'justification',
        'input_payload',
        'output_payload',
        'estimated_cost_brl',
        'status', // proposed, approved, executed, rejected
    ];

    protected $casts = [
        'input_payload' => 'array',
        'output_payload' => 'array',
        'estimated_cost_brl' => 'decimal:2',
    ];

    public function business()
    {
        return $this->belongsTo(Business::class);
    }
}

