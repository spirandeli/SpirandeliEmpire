<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class JeffreyMemory extends Model
{
    protected $table = 'jeffrey_memories';

    protected $fillable = [
        'business_id',
        'category', // context, decision, preference, architecture, issue
        'key',
        'content',
        'metadata',
        'is_active',
    ];

    protected $casts = [
        'metadata' => 'array',
        'is_active' => 'boolean',
    ];

    public function business()
    {
        return $this->belongsTo(Business::class);
    }
}

