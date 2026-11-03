<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ApprovalRequest extends Model
{
    protected $fillable = [
        'title',
        'description',
        'agent_name',
        'business_id',
        'action_payload',
        'financial_impact_brl',
        'status', // pending, approved, rejected
        'reviewed_by',
        'reviewed_at',
        'rejection_reason',
    ];

    protected $casts = [
        'action_payload' => 'array',
        'financial_impact_brl' => 'decimal:2',
        'reviewed_at' => 'datetime',
    ];

    public function business()
    {
        return $this->belongsTo(Business::class);
    }
}

