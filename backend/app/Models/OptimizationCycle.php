<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class OptimizationCycle extends Model
{
    use HasFactory;

    protected $fillable = [
        'business_id',
        'period_start',
        'period_end',
        'winning_assets_summary',
        'losing_assets_summary',
        'ai_diagnosis',
        'actions_taken',
    ];

    protected function casts(): array
    {
        return [
            'period_start' => 'datetime',
            'period_end' => 'datetime',
            'winning_assets_summary' => 'array',
            'losing_assets_summary' => 'array',
            'actions_taken' => 'array',
        ];
    }

    public function business(): BelongsTo
    {
        return $this->belongsTo(Business::class);
    }
}

