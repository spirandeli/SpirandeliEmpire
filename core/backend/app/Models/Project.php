<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class Project extends Model
{
    protected $fillable = [
        'name',
        'slug',
        'description',
        'path',
        'git_repo',
        'git_branch',
        'status', // active, paused, archived
        'stack',
        'settings',
    ];

    protected $casts = [
        'settings' => 'array',
    ];

    public function conversations()
    {
        return $this->hasMany(Conversation::class);
    }
}
