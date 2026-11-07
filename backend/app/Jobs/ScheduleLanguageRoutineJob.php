<?php

namespace App\Jobs;

use App\Models\LanguageProfile;
use App\Models\UserIntegration;
use App\Services\AppleCalDavService;
use App\Services\GoogleWorkspaceService;
use Carbon\Carbon;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;

class ScheduleLanguageRoutineJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(public LanguageProfile $profile)
    {
    }

    public function handle(
        GoogleWorkspaceService $googleService,
        AppleCalDavService $appleService
    ): void {
        $user = $this->profile->user;
        if (! $user) {
            return;
        }

        $calendarSyncIds = $this->profile->calendar_sync_ids ?? [];

        // 1. Limpeza de agendamentos anteriores para evitar duplicatas
        if (! empty($calendarSyncIds['google_event_id'])) {
            try {
                $googleService->deleteEvent($user, $calendarSyncIds['google_event_id']);
            } catch (\Throwable $e) {
                Log::warning('Erro ao remover evento recorrente antigo no Google Calendar', [
                    'error' => $e->getMessage(),
                ]);
            }
            unset($calendarSyncIds['google_event_id']);
        }

        if (! empty($calendarSyncIds['apple_href'])) {
            try {
                $appleService->deleteEvent($user, $calendarSyncIds['apple_href']);
            } catch (\Throwable $e) {
                Log::warning('Erro ao remover evento recorrente antigo no Apple Calendar', [
                    'error' => $e->getMessage(),
                ]);
            }
            unset($calendarSyncIds['apple_href']);
        }

        // 2. Constrói a regra de recorrência (RRULE)
        $studyDays = $this->profile->study_days ?? ['MON', 'TUE', 'WED', 'THU', 'FRI'];
        $byDayMap = [
            'MON' => 'MO',
            'TUE' => 'TU',
            'WED' => 'WE',
            'THU' => 'TH',
            'FRI' => 'FR',
            'SAT' => 'SA',
            'SUN' => 'SU',
            'SEG' => 'MO',
            'TER' => 'TU',
            'QUA' => 'WE',
            'QUI' => 'TH',
            'SEX' => 'FR',
            'SAB' => 'SA',
            'DOM' => 'SU',
        ];

        $byDayValues = [];
        if (in_array('ALL', $studyDays, true)) {
            $byDayValues = ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU'];
        } else {
            foreach ($studyDays as $day) {
                $upper = strtoupper(trim($day));
                if (isset($byDayMap[$upper])) {
                    $byDayValues[] = $byDayMap[$upper];
                }
            }
        }

        if (empty($byDayValues)) {
            $byDayValues = ['MO', 'TU', 'WE', 'TH', 'FR'];
        }

        $rruleString = 'FREQ=WEEKLY;BYDAY=' . implode(',', array_unique($byDayValues));

        // 3. Monta horários de início e fim (15 minutos)
        $timeParts = explode(':', $this->profile->preferred_time ?? '07:30');
        $hour = (int) ($timeParts[0] ?? 7);
        $minute = (int) ($timeParts[1] ?? 30);

        // Define a próxima data de ocorrência compatível
        $startDate = Carbon::today()->setTime($hour, $minute, 0);
        if ($startDate->isPast()) {
            $startDate->addDay();
        }
        $endDate = (clone $startDate)->addMinutes($this->profile->daily_duration_minutes ?? 15);

        $appUrl = config('app.frontend_url', config('app.url', 'http://localhost:8080'));
        $languagesUrl = rtrim($appUrl, '/') . '/languages';

        $title = sprintf(
            '🔥 Academia de Idiomas: %s (15 min)',
            $this->profile->target_language
        );

        $description = sprintf(
            "Micro-learning diário adaptativo com Gemini 3.8 Flash.\nFoco: %s | Nível CEFR: %s\n\nAcesse sua sessão de 15 minutos:\n%s\n\nConstância gera fluência funcional!",
            ucfirst($this->profile->learning_focus),
            $this->profile->cefr_level,
            $languagesUrl
        );

        // 4. Sincroniza com Google Calendar (se usuário conectou)
        if ($user->integration(UserIntegration::PROVIDER_GOOGLE)) {
            try {
                $googleEvent = $googleService->createEvent($user, [
                    'title' => $title,
                    'description' => $description,
                    'starts_at' => $startDate,
                    'ends_at' => $endDate,
                    'location' => $languagesUrl,
                    'recurrence' => ['RRULE:' . $rruleString],
                    'reminders' => [
                        'useDefault' => false,
                        'overrides' => [
                            ['method' => 'popup', 'minutes' => 10],
                        ],
                    ],
                ]);

                if (! empty($googleEvent['id'])) {
                    $calendarSyncIds['google_event_id'] = $googleEvent['id'];
                }
            } catch (\Throwable $e) {
                Log::error('Falha ao agendar rotina de idiomas no Google Calendar', [
                    'profile_id' => $this->profile->id,
                    'error' => $e->getMessage(),
                ]);
            }
        }

        // 5. Sincroniza com Apple iCloud Calendar (se conectado)
        if ($user->integration(UserIntegration::PROVIDER_APPLE_CALDAV)) {
            try {
                $appleEvent = $appleService->createEvent($user, [
                    'title' => $title,
                    'description' => $description,
                    'starts_at' => $startDate,
                    'ends_at' => $endDate,
                    'location' => $languagesUrl,
                    'rrule' => $rruleString,
                    'alarm_minutes_before' => 10,
                ]);

                if (! empty($appleEvent['href'])) {
                    $calendarSyncIds['apple_href'] = $appleEvent['href'];
                    $calendarSyncIds['apple_uid'] = $appleEvent['uid'] ?? null;
                }
            } catch (\Throwable $e) {
                Log::error('Falha ao agendar rotina de idiomas no Apple Calendar', [
                    'profile_id' => $this->profile->id,
                    'error' => $e->getMessage(),
                ]);
            }
        }

        $this->profile->calendar_sync_ids = $calendarSyncIds;
        $this->profile->save();
    }
}
