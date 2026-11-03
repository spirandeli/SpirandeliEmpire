<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Task extends Model
{
    protected $fillable = [
        'business_id',
        'agent_name',
        'title',
        'type', // content_generation, video_rendering, market_research, etc.
        'status', // pending, in_progress, completed, failed, cancelled
        'payload',
        'result',
        'error_message',
        'estimated_cost_brl',
        'actual_cost_brl',
        'started_at',
        'completed_at',
    ];

    protected $casts = [
        'payload' => 'array',
        'result' => 'array',
        'estimated_cost_brl' => 'decimal:2',
        'actual_cost_brl' => 'decimal:2',
        'started_at' => 'datetime',
        'completed_at' => 'datetime',
    ];

    public function business()
    {
        return $this->belongsTo(Business::class);
    }
}

