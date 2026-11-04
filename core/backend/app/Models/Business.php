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
        'accounts',
        'automation_params',
        'storage_path',
        'budget_limit_brl',
        'current_month_cost_brl',
        'total_revenue_brl',
    ];

    protected $casts = [
        'settings' => 'array',
        'accounts' => 'array',
        'automation_params' => 'array',
        'budget_limit_brl' => 'decimal:2',
        'current_month_cost_brl' => 'decimal:2',
        'total_revenue_brl' => 'decimal:2',
    ];

    protected $appends = [
        'accounts_list',
        'automation_config',
    ];

    public function getAccountsListAttribute(): array
    {
        $raw = $this->attributes['accounts'] ?? null;
        if ($raw) {
            $decoded = is_array($raw) ? $raw : json_decode($raw, true);
            if (is_array($decoded) && !empty($decoded)) {
                return $decoded;
            }
        }
        $settings = $this->settings ?? [];
        return is_array($settings['accounts'] ?? null) ? $settings['accounts'] : [];
    }

    public function getAutomationConfigAttribute(): array
    {
        $raw = $this->attributes['automation_params'] ?? null;
        if ($raw) {
            $decoded = is_array($raw) ? $raw : json_decode($raw, true);
            if (is_array($decoded) && !empty($decoded)) {
                return $decoded;
            }
        }
        $settings = $this->settings ?? [];
        return is_array($settings['automation_params'] ?? null) ? $settings['automation_params'] : [];
    }

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

