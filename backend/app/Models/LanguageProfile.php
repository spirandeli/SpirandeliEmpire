<?php

namespace App\Models;

use Carbon\Carbon;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class LanguageProfile extends Model
{
    use HasFactory;

    protected $fillable = [
        'user_id',
        'target_language',
        'learning_focus',
        'cefr_level',
        'study_days',
        'preferred_time',
        'daily_duration_minutes',
        'streak_days',
        'last_activity_date',
        'calendar_sync_ids',
        'weaknesses_diagnosis',
        'is_active',
    ];

    protected function casts(): array
    {
        return [
            'study_days' => 'array',
            'daily_duration_minutes' => 'integer',
            'streak_days' => 'integer',
            'last_activity_date' => 'date',
            'calendar_sync_ids' => 'array',
            'weaknesses_diagnosis' => 'array',
            'is_active' => 'boolean',
        ];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function sessions(): HasMany
    {
        return $this->hasMany(LanguageDailySession::class);
    }

    public function vocabularyVault(): HasMany
    {
        return $this->hasMany(LanguageVocabularyVault::class);
    }

    /**
     * Registra conclusão de atividade hoje e computa a ofensiva (streak).
     */
    public function recordCompletionToday(): void
    {
        $today = Carbon::today();
        $lastActivity = $this->last_activity_date ? Carbon::parse($this->last_activity_date) : null;

        if (! $lastActivity) {
            $this->streak_days = 1;
        } elseif ($lastActivity->isToday()) {
            // Já praticou hoje, mantém a ofensiva
        } elseif ($lastActivity->isYesterday()) {
            // Dia consecutivo: soma +1
            $this->streak_days += 1;
        } else {
            // Quebrou a sequência
            $this->streak_days = 1;
        }

        $this->last_activity_date = $today;
        $this->save();
    }
}
