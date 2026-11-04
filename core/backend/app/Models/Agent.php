<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Agent extends Model
{
    protected $fillable = [
        'name',
        'slug',
        'role',
        'description',
        'model',
        'system_prompt',
        'authorized_tools',
        'authorized_projects',
        'is_active',
    ];

    protected $casts = [
        'authorized_tools' => 'array',
        'authorized_projects' => 'array',
        'is_active' => 'boolean',
    ];
}
