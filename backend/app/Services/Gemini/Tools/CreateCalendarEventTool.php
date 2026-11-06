<?php

namespace App\Services\Gemini\Tools;

use App\Models\CalendarEvent;
use App\Models\UserIntegration;
use App\Services\AppleCalDavService;
use App\Services\GoogleWorkspaceService;
use Illuminate\Support\Carbon;

class CreateCalendarEventTool extends AbstractTool
{
    public function __construct(
        private readonly GoogleWorkspaceService $googleService,
        private readonly AppleCalDavService $appleService,
    ) {
    }

    public function name(): string
    {
        return 'createCalendarEvent';
    }

    public function description(): string
    {
        return 'Cria um evento de compromisso ou janela de gravação na agenda do usuário (Google Calendar ou Apple iCloud Calendar). Use após verificar a disponibilidade com get_user_schedule.';
    }

    public function parameters(): array
    {
        return [
            'type' => 'OBJECT',
            'properties' => [
                'title' => [
                    'type' => 'STRING',
                    'description' => 'Título do evento na agenda (ex: [Gravação TikTok] Mini Processador 3 em 1).',
                ],
                'description' => [
                    'type' => 'STRING',
                    'description' => 'Detalhes do evento, links de aprovação, roteiro ou checklist de gravação.',
                ],
                'starts_at' => [
                    'type' => 'STRING',
                    'description' => 'Data e hora de início (formato ISO 8601, ex: 2026-11-07T14:00:00-03:00).',
                ],
                'ends_at' => [
                    'type' => 'STRING',
                    'description' => 'Data e hora de término (formato ISO 8601, ex: 2026-11-07T15:00:00-03:00).',
                ],
                'provider' => [
                    'type' => 'STRING',
                    'enum' => ['auto', 'google', 'apple'],
                    'description' => 'Provedor de calendário. "auto" utiliza o que estiver conectado.',
                ],
            ],
            'required' => ['title', 'starts_at', 'ends_at'],
        ];
    }

    public function execute(array $arguments, ToolExecutionContext $context): array
    {
        try {
            $user = $context->user;
            $userTz = $user->timezone ?: 'America/Sao_Paulo';

            $startsAt = Carbon::parse($arguments['starts_at'])->setTimezone($userTz);
            $endsAt = Carbon::parse($arguments['ends_at'])->setTimezone($userTz);
            $provider = $arguments['provider'] ?? 'auto';

            $hasGoogle = (bool) $user->integration(UserIntegration::PROVIDER_GOOGLE);
            $hasApple = (bool) $user->integration(UserIntegration::PROVIDER_APPLE_CALDAV);

            $chosenProvider = match ($provider) {
                'google' => 'google',
                'apple' => 'apple',
                default => $hasGoogle ? 'google' : ($hasApple ? 'apple' : null),
            };

            $externalId = 'local_' . uniqid();

            if ($chosenProvider === 'google' && $hasGoogle) {
                $created = $this->googleService->createEvent($user, [
                    'title' => $arguments['title'],
                    'description' => $arguments['description'] ?? null,
                    'starts_at' => $startsAt,
                    'ends_at' => $endsAt,
                ]);
                $externalId = $created['id'] ?? $externalId;
            } elseif ($chosenProvider === 'apple' && $hasApple) {
                $created = $this->appleService->createEvent($user, [
                    'title' => $arguments['title'],
                    'description' => $arguments['description'] ?? null,
                    'starts_at' => $startsAt,
                    'ends_at' => $endsAt,
                ]);
                $externalId = $created['uid'] ?? $externalId;
            }

            // Persiste no cache local unificado
            $event = CalendarEvent::create([
                'user_id' => $user->id,
                'provider' => $chosenProvider ?: 'internal',
                'kind' => 'event',
                'external_id' => $externalId,
                'title' => $arguments['title'],
                'description' => $arguments['description'] ?? null,
                'starts_at' => $startsAt,
                'ends_at' => $endsAt,
                'created_by_agent' => true,
                'status' => 'confirmed',
                'synced_at' => now(),
            ]);

            return [
                'success' => true,
                'event_id' => $event->id,
                'title' => $event->title,
                'provider' => $chosenProvider ?: 'agenda interna (sem sincronização externa configurada)',
                'starts_at' => $startsAt->toIso8601String(),
                'ends_at' => $endsAt->toIso8601String(),
                'message' => "Evento \"{$event->title}\" agendado com sucesso para {$startsAt->format('d/m/Y H:i')}.",
            ];
        } catch (\Throwable $e) {
            return [
                'success' => false,
                'error' => 'Falha ao criar evento no calendário: ' . $e->getMessage(),
            ];
        }
    }
}

