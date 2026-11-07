<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Jobs\ScheduleLanguageRoutineJob;
use App\Models\AiUsageLog;
use App\Models\LanguageDailySession;
use App\Models\LanguageProfile;
use App\Models\LanguageVocabularyVault;
use App\Services\GeminiLanguageService;
use Carbon\Carbon;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class LanguageAcademyController extends Controller
{
    public function __construct(
        private readonly GeminiLanguageService $languageService
    ) {
    }

    /**
     * Retorna o perfil ativo do usuário e métricas essenciais.
     */
    public function getProfile(Request $request): JsonResponse
    {
        $user = $request->user();
        $profile = $user->activeLanguageProfile();

        if (! $profile) {
            return response()->json([
                'profile' => null,
                'has_profile' => false,
            ]);
        }

        $profile->loadCount('vocabularyVault');

        // Métricas de tokens do Gemini 3.8 Flash
        $flashUsage = AiUsageLog::query()
            ->where('user_id', $user->id)
            ->where('model', GeminiLanguageService::MODEL)
            ->where('context', 'like', 'language_academy%')
            ->selectRaw('COUNT(*) as total_calls, SUM(total_tokens) as total_tokens, SUM(estimated_cost_usd) as total_cost_usd')
            ->first();

        // Quantidade de termos a revisar hoje
        $dueVaultCount = $profile->vocabularyVault()
            ->where('next_review_date', '<=', Carbon::today())
            ->count();

        return response()->json([
            'profile' => $profile,
            'has_profile' => true,
            'stats' => [
                'due_reviews_count' => $dueVaultCount,
                'total_vault_words' => $profile->vocabulary_vault_count,
                'streak_days' => $profile->streak_days,
                'flash_tokens_used' => (int) ($flashUsage->total_tokens ?? 0),
                'flash_cost_usd' => (float) ($flashUsage->total_cost_usd ?? 0.0),
                'flash_calls_count' => (int) ($flashUsage->total_calls ?? 0),
            ],
        ]);
    }

    /**
     * Onboarding: Cria o primeiro perfil ou novo idioma e dispara agendamento de agenda.
     */
    public function storeProfile(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'target_language' => ['required', 'string', 'max:50'],
            'learning_focus' => ['required', 'string', 'max:100'],
            'study_days' => ['required', 'array', 'min:1'],
            'study_days.*' => ['string'],
            'preferred_time' => ['required', 'string', 'regex:/^\d{2}:\d{2}$/'],
            'daily_duration_minutes' => ['nullable', 'integer', 'min:5', 'max:60'],
        ]);

        $user = $request->user();

        // Desativa perfis anteriores para ativar o novo
        $user->languageProfiles()->update(['is_active' => false]);

        $profile = $user->languageProfiles()->create([
            'target_language' => $validated['target_language'],
            'learning_focus' => $validated['learning_focus'],
            'cefr_level' => 'UNSET',
            'study_days' => $validated['study_days'],
            'preferred_time' => $validated['preferred_time'],
            'daily_duration_minutes' => $validated['daily_duration_minutes'] ?? 15,
            'streak_days' => 0,
            'is_active' => true,
        ]);

        // Dispara sincronização com Google & Apple em background
        ScheduleLanguageRoutineJob::dispatch($profile);

        return response()->json([
            'message' => 'Perfil de aprendizado criado com sucesso!',
            'profile' => $profile,
        ], 201);
    }

    /**
     * Atualiza dias e horário de estudo e ressincroniza Google e Apple Calendar.
     */
    public function updateSchedule(Request $request, LanguageProfile $profile): JsonResponse
    {
        $this->authorizeProfile($request, $profile);

        $validated = $request->validate([
            'study_days' => ['required', 'array', 'min:1'],
            'preferred_time' => ['required', 'string', 'regex:/^\d{2}:\d{2}$/'],
        ]);

        $profile->update([
            'study_days' => $validated['study_days'],
            'preferred_time' => $validated['preferred_time'],
        ]);

        // Reagenda eventos nos calendários
        ScheduleLanguageRoutineJob::dispatch($profile);

        return response()->json([
            'message' => 'Agenda e notificações atualizadas com sucesso!',
            'profile' => $profile->fresh(),
        ]);
    }

    /**
     * Gera ou busca o Teste de Nivelamento Diagnóstico (CEFR).
     */
    public function getPlacementTest(Request $request, LanguageProfile $profile): JsonResponse
    {
        $this->authorizeProfile($request, $profile);

        $placementTest = $this->languageService->generatePlacementTest($profile);

        return response()->json([
            'placement_test' => $placementTest,
        ]);
    }

    /**
     * Submete as respostas do Teste de Nivelamento, define CEFR e pontos cegos.
     */
    public function submitPlacementTest(Request $request, LanguageProfile $profile): JsonResponse
    {
        $this->authorizeProfile($request, $profile);

        $validated = $request->validate([
            'questions' => ['required', 'array', 'min:1'],
            'answers' => ['required', 'array'],
        ]);

        $evaluation = $this->languageService->evaluatePlacementTest(
            $profile,
            $validated['questions'],
            $validated['answers']
        );

        $profile->update([
            'cefr_level' => $evaluation['cefr_level'] ?? 'A2',
            'weaknesses_diagnosis' => [
                'score_percentage' => $evaluation['score_percentage'] ?? 0,
                'executive_summary' => $evaluation['executive_summary'] ?? '',
                'blind_spots' => $evaluation['blind_spots'] ?? [],
                'strengths' => $evaluation['strengths'] ?? [],
                'recommended_study_plan' => $evaluation['recommended_study_plan'] ?? '',
                'evaluated_at' => now()->toISOString(),
            ],
        ]);

        return response()->json([
            'message' => 'Nivelamento concluído com sucesso!',
            'evaluation' => $evaluation,
            'profile' => $profile->fresh(),
        ]);
    }

    /**
     * Obtém ou gera sob demanda a lição de 15 minutos do dia (3 blocos).
     */
    public function getTodaySession(Request $request, LanguageProfile $profile): JsonResponse
    {
        $this->authorizeProfile($request, $profile);

        $today = Carbon::today()->toDateString();

        $session = $profile->sessions()
            ->whereDate('scheduled_date', $today)
            ->first();

        if (! $session || empty($session->lesson_payload)) {
            // Busca palavras para repetição espaçada
            $dueVocabulary = $profile->vocabularyVault()
                ->where('next_review_date', '<=', $today)
                ->orderBy('mastery_level', 'asc')
                ->take(5)
                ->get();

            if ($dueVocabulary->isEmpty()) {
                $dueVocabulary = $profile->vocabularyVault()->latest()->take(3)->get();
            }

            $lessonPayload = $this->languageService->generateDailyLesson($profile, $dueVocabulary);

            if (! $session) {
                $session = $profile->sessions()->create([
                    'scheduled_date' => $today,
                    'status' => 'ready',
                    'lesson_payload' => $lessonPayload,
                ]);
            } else {
                $session->update([
                    'lesson_payload' => $lessonPayload,
                    'status' => 'ready',
                ]);
            }
        }

        return response()->json([
            'session' => $session,
        ]);
    }

    /**
     * Submete a sessão diária, avalia com Gemini 3.8 Flash, atualiza streak e SRS.
     */
    public function submitDailySession(
        Request $request,
        LanguageProfile $profile,
        LanguageDailySession $session
    ): JsonResponse {
        $this->authorizeProfile($request, $profile);

        if ($session->language_profile_id !== $profile->id) {
            abort(403, 'Sessão não pertence a este perfil.');
        }

        $validated = $request->validate([
            'user_answers' => ['required', 'array'],
            'time_spent_seconds' => ['nullable', 'integer', 'min:0'],
        ]);

        $evaluation = $this->languageService->evaluateDailySession(
            $profile,
            $session->lesson_payload ?? [],
            $validated['user_answers']
        );

        DB::transaction(function () use ($session, $profile, $validated, $evaluation) {
            $session->update([
                'status' => 'completed',
                'user_answers' => $validated['user_answers'],
                'ai_feedback' => $evaluation,
                'score' => $evaluation['overall_score'] ?? 80,
                'time_spent_seconds' => $validated['time_spent_seconds'] ?? 900,
                'completed_at' => now(),
            ]);

            // Atualiza ofensiva (streak) diária
            $profile->recordCompletionToday();

            // Atualiza maestria dos itens de SRS revisados no Bloco 1
            $block1Results = $evaluation['block1_results'] ?? [];
            foreach ($block1Results as $result) {
                $itemId = $result['item_id'] ?? null;
                $isCorrect = (bool) ($result['is_correct'] ?? false);

                // Procura pelo termo no cofre
                $term = data_get($session->lesson_payload, "block1_srs.items.{$itemId}.term");
                if ($term) {
                    $vaultItem = $profile->vocabularyVault()
                        ->where('term_or_phrase', $term)
                        ->first();

                    $vaultItem?->recordReviewResult($isCorrect);
                }
            }

            // Insere novas palavras e expressões no Cofre de Repetição Espaçada
            $newWords = $evaluation['new_words_to_vault'] ?? [];
            foreach ($newWords as $newWord) {
                if (! empty($newWord['term_or_phrase'])) {
                    $profile->vocabularyVault()->updateOrCreate(
                        [
                            'term_or_phrase' => trim($newWord['term_or_phrase']),
                        ],
                        [
                            'translation' => trim($newWord['translation'] ?? ''),
                            'context_example' => $newWord['context_example'] ?? null,
                            'mastery_level' => 1,
                            'next_review_date' => Carbon::today()->addDay(),
                        ]
                    );
                }
            }
        });

        return response()->json([
            'message' => 'Parabéns! Sessão diária concluída.',
            'evaluation' => $evaluation,
            'session' => $session->fresh(),
            'profile' => $profile->fresh(),
        ]);
    }

    /**
     * Lista palavras do cofre de repetição espaçada (SRS).
     */
    public function getVocabularyVault(Request $request, LanguageProfile $profile): JsonResponse
    {
        $this->authorizeProfile($request, $profile);

        $vaultItems = $profile->vocabularyVault()
            ->orderBy('next_review_date', 'asc')
            ->orderBy('mastery_level', 'asc')
            ->get();

        $stats = [
            'total' => $vaultItems->count(),
            'mastered' => $vaultItems->where('mastery_level', 5)->count(),
            'learning' => $vaultItems->where('mastery_level', '<', 5)->count(),
            'due_today' => $vaultItems->where('next_review_date', '<=', Carbon::today())->count(),
        ];

        return response()->json([
            'items' => $vaultItems,
            'stats' => $stats,
        ]);
    }

    /**
     * Adiciona manualmente uma palavra ou expressão ao cofre.
     */
    public function addVocabularyWord(Request $request, LanguageProfile $profile): JsonResponse
    {
        $this->authorizeProfile($request, $profile);

        $validated = $request->validate([
            'term_or_phrase' => ['required', 'string', 'max:255'],
            'translation' => ['required', 'string', 'max:255'],
            'context_example' => ['nullable', 'string'],
        ]);

        $item = $profile->vocabularyVault()->create([
            'term_or_phrase' => trim($validated['term_or_phrase']),
            'translation' => trim($validated['translation']),
            'context_example' => $validated['context_example'] ?? null,
            'mastery_level' => 1,
            'next_review_date' => Carbon::today()->addDay(),
        ]);

        return response()->json([
            'message' => 'Palavra adicionada ao cofre com sucesso!',
            'item' => $item,
        ], 201);
    }

    /**
     * Remove uma palavra do cofre.
     */
    public function deleteVocabularyWord(
        Request $request,
        LanguageProfile $profile,
        LanguageVocabularyVault $vaultItem
    ): JsonResponse {
        $this->authorizeProfile($request, $profile);

        if ($vaultItem->language_profile_id !== $profile->id) {
            abort(403, 'Item não pertence a este perfil.');
        }

        $vaultItem->delete();

        return response()->json([
            'message' => 'Palavra removida do cofre.',
        ]);
    }

    private function authorizeProfile(Request $request, LanguageProfile $profile): void
    {
        if ($profile->user_id !== $request->user()->id) {
            abort(403, 'Acesso não autorizado a este perfil de idiomas.');
        }
    }
}
