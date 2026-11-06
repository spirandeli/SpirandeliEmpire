<?php

namespace App\Services\Gemini\Tools;

use App\Models\CalendarEvent;
use Illuminate\Support\Carbon;

class CheckUserScheduleTool extends AbstractTool
{
    public function name(): string
    {
        return 'checkUserSchedule';
    }

    public function description(): string
    {
        return 'Verifica a disponibilidade real na agenda do usuário dentro de um período (Google Calendar e Apple iCloud sincronizados), além das preferências de horários de trabalho. Use esta ferramenta SEMPRE antes de propor horários de gravação de vídeos, revisões ou compromissos.';
    }

    public function parameters(): array
    {
        return [
            'type' => 'OBJECT',
            'properties' => [
                'from' => [
                    'type' => 'STRING',
                    'description' => 'Início do intervalo a consultar (formato ISO 8601, ex: 2026-11-06T09:00:00-03:00). Se omitido, assume o momento atual.',
                ],
                'to' => [
                    'type' => 'STRING',
                    'description' => 'Fim do intervalo a consultar (formato ISO 8601). Se omitido, assume as próximas 48 horas a partir de "from".',
                ],
            ],
        ];
    }

    public function execute(array $arguments, ToolExecutionContext $context): array
    {
        try {
            $userTz = $context->user->timezone ?: config('app.timezone', 'America/Sao_Paulo');

            $from = ! empty($arguments['from'])
                ? Carbon::parse($arguments['from'])->setTimezone($userTz)
                : Carbon::now($userTz);

            $to = ! empty($arguments['to'])
                ? Carbon::parse($arguments['to'])->setTimezone($userTz)
                : $from->copy()->addDays(2);

            if ($to->isBefore($from)) {
                return [
                    'success' => false,
                    'error' => 'A data final ("to") deve ser posterior à data inicial ("from").',
                ];
            }

            // Busca compromissos na tabela cache unificada
            $events = CalendarEvent::query()
                ->where('user_id', $context->user->id)
                ->between($from, $to)
                ->orderBy('starts_at')
                ->get()
                ->map(fn (CalendarEvent $e) => [
                    'id' => $e->id,
                    'title' => $e->title,
                    'provider' => $e->provider,
                    'kind' => $e->kind,
                    'starts_at' => $e->starts_at?->setTimezone($userTz)->toIso8601String(),
                    'ends_at' => $e->ends_at?->setTimezone($userTz)->toIso8601String(),
                    'all_day' => (bool) $e->all_day,
                ]);

            $workHours = data_get($context->user->settings, 'work_hours', [
                'start' => '09:00',
                'end' => '18:00',
                'recording_windows' => ['14:00-16:00'],
            ]);

            return [
                'success' => true,
                'period' => [
                    'from' => $from->toIso8601String(),
                    'to' => $to->toIso8601String(),
                    'timezone' => $userTz,
                ],
                'busy_events_count' => $events->count(),
                'busy_events' => $events->values()->all(),
                'user_preferences' => [
                    'preferred_work_hours' => $workHours,
                ],
                'message' => $events->isEmpty()
                    ? "Agenda livre entre {$from->format('d/m H:i')} e {$to->format('d/m H:i')} ({$userTz})."
                    : "Encontrados {$events->count()} compromisso(s) no período.",
            ];
        } catch (\Throwable $e) {
            return [
                'success' => false,
                'error' => 'Falha ao consultar agenda: ' . $e->getMessage(),
            ];
        }
    }
}

