<?php

namespace App\Jobs;

use App\Models\LanguageDailySession;
use App\Models\LanguageProfile;
use App\Services\GeminiLanguageService;
use Carbon\Carbon;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;

class GenerateDailyLanguageLessonJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(
        public LanguageProfile $profile,
        public ?string $targetDate = null
    ) {
    }

    public function handle(GeminiLanguageService $languageService): ?LanguageDailySession
    {
        $date = $this->targetDate ? Carbon::parse($this->targetDate) : Carbon::today();
        $dateString = $date->toDateString();

        // Se o usuário ainda não fez o placement test (nível UNSET), não gera lição diária ainda
        if ($this->profile->cefr_level === 'UNSET') {
            return null;
        }

        // Verifica se a sessão do dia já foi gerada
        $existingSession = $this->profile->sessions()
            ->whereDate('scheduled_date', $dateString)
            ->first();

        if ($existingSession && in_array($existingSession->status, ['ready', 'in_progress', 'completed'], true)) {
            return $existingSession;
        }

        try {
            // Busca palavras do cofre que precisam de revisão espaçada hoje
            $dueVocabulary = $this->profile->vocabularyVault()
                ->where('next_review_date', '<=', $dateString)
                ->orderBy('mastery_level', 'asc')
                ->take(5)
                ->get();

            // Se o cofre tiver poucas palavras, busca as mais recentes para reforço
            if ($dueVocabulary->isEmpty()) {
                $dueVocabulary = $this->profile->vocabularyVault()
                    ->latest()
                    ->take(3)
                    ->get();
            }

            $lessonPayload = $languageService->generateDailyLesson($this->profile, $dueVocabulary);

            $session = $existingSession ?? new LanguageDailySession();
            $session->language_profile_id = $this->profile->id;
            $session->scheduled_date = $dateString;
            $session->status = 'ready';
            $session->lesson_payload = $lessonPayload;
            $session->save();

            return $session;
        } catch (\Throwable $e) {
            Log::error('Erro ao gerar lição diária de idiomas via Gemini 3.8 Flash', [
                'profile_id' => $this->profile->id,
                'error' => $e->getMessage(),
            ]);

            return null;
        }
    }
}
