<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class SystemMetric extends Model
{
    protected $fillable = [
        'cpu_usage_percent',
        'ram_usage_percent',
        'disk_usage_percent',
        'active_containers_count',
        'active_queues_count',
        'gpu_status',
        'metadata',
        'recorded_at',
    ];

    protected $casts = [
        'cpu_usage_percent' => 'float',
        'ram_usage_percent' => 'float',
        'disk_usage_percent' => 'float',
        'metadata' => 'array',
        'recorded_at' => 'datetime',
    ];
}

