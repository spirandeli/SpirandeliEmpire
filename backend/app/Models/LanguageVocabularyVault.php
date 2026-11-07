<?php

namespace App\Models;

use Carbon\Carbon;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class LanguageVocabularyVault extends Model
{
    use HasFactory;

    protected $table = 'language_vocabulary_vault';

    protected $fillable = [
        'language_profile_id',
        'term_or_phrase',
        'translation',
        'context_example',
        'mastery_level',
        'next_review_date',
    ];

    protected function casts(): array
    {
        return [
            'mastery_level' => 'integer',
            'next_review_date' => 'date',
        ];
    }

    public function profile(): BelongsTo
    {
        return $this->belongsTo(LanguageProfile::class, 'language_profile_id');
    }

    /**
     * Aplica o algoritmo de repetição espaçada (SRS) após revisão.
     */
    public function recordReviewResult(bool $isCorrect): void
    {
        if ($isCorrect) {
            $this->mastery_level = min(5, $this->mastery_level + 1);
            $daysToAdd = match ($this->mastery_level) {
                1 => 1,
                2 => 3,
                3 => 7,
                4 => 14,
                default => 30,
            };
            $this->next_review_date = Carbon::today()->addDays($daysToAdd);
        } else {
            $this->mastery_level = 1;
            $this->next_review_date = Carbon::today()->addDay();
        }

        $this->save();
    }
}
