<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class FinancialRecord extends Model
{
    protected $fillable = [
        'business_id',
        'type', // revenue, infrastructure_expense, ai_cost, platform_fee, other_expense
        'category',
        'description',
        'amount_brl',
        'is_confirmed',
        'recorded_at',
    ];

    protected $casts = [
        'amount_brl' => 'decimal:2',
        'is_confirmed' => 'boolean',
        'recorded_at' => 'datetime',
    ];

    public function business()
    {
        return $this->belongsTo(Business::class);
    }
}

