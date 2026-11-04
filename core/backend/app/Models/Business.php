<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Business extends Model
{
    protected $fillable = [
        'name',
        'slug',
        'category',
        'description',
        'status', // active, paused, provisioning, archived
        'template_used',
        'settings',
        'storage_path',
        'budget_limit_brl',
        'current_month_cost_brl',
        'total_revenue_brl',
    ];

    protected $casts = [
        'settings' => 'array',
        'budget_limit_brl' => 'decimal:2',
        'current_month_cost_brl' => 'decimal:2',
        'total_revenue_brl' => 'decimal:2',
    ];

    public function tasks()
    {
        return $this->hasMany(Task::class);
    }

    public function financialRecords()
    {
        return $this->hasMany(FinancialRecord::class);
    }

    public function memories()
    {
        return $this->hasMany(JeffreyMemory::class);
    }

    public function conversations()
    {
        return $this->hasMany(Conversation::class);
    }
}

