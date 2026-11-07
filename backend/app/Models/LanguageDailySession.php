<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class LanguageDailySession extends Model
{
    use HasFactory;

    protected $fillable = [
        'language_profile_id',
        'scheduled_date',
        'status',
        'lesson_payload',
        'user_answers',
        'ai_feedback',
        'score',
        'time_spent_seconds',
        'completed_at',
    ];

    protected function casts(): array
    {
        return [
            'scheduled_date' => 'date',
            'lesson_payload' => 'array',
            'user_answers' => 'array',
            'ai_feedback' => 'array',
            'score' => 'integer',
            'time_spent_seconds' => 'integer',
            'completed_at' => 'datetime',
        ];
    }

    public function profile(): BelongsTo
    {
        return $this->belongsTo(LanguageProfile::class, 'language_profile_id');
    }
}
