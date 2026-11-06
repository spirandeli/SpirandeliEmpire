<?php

namespace App\Services\Gemini\Tools;

use App\Models\CalendarEvent;
use App\Models\UserIntegration;
use App\Services\AppleCalDavService;
use App\Services\GoogleWorkspaceService;
use Illuminate\Support\Carbon;

class CreateReminderTool extends AbstractTool
{
    public function __construct(
        private readonly GoogleWorkspaceService $googleService,
        private readonly AppleCalDavService $appleService,
    ) {
    }

    public function name(): string
    {
        return 'createReminder';
    }

    public function description(): string
    {
        return 'Cria um lembrete no Apple Reminders (iOS/macOS) ou Google Tasks. Muito útil para notificar o usuário 2 horas antes do horário de pico de postagem ou alertar sobre revisões pendentes com o link direto da página de aprovação.';
    }

    public function parameters(): array
    {
        return [
            'type' => 'OBJECT',
            'properties' => [
                'title' => [
                    'type' => 'STRING',
                    'description' => 'Texto do lembrete (ex: [Revisão Necessária] Aprovar vídeo TikTok Shop antes das 18h).',
                ],
                'description' => [
                    'type' => 'STRING',
                    'description' => 'Notas adicionais ou URL de ação.',
                ],
                'due_at' => [
                    'type' => 'STRING',
                    'description' => 'Data e hora para o alerta do lembrete disparar (formato ISO 8601).',
                ],
                'priority' => [
                    'type' => 'STRING',
                    'enum' => ['low', 'medium', 'high'],
                    'description' => 'Prioridade do lembrete.',
                ],
                'provider' => [
                    'type' => 'STRING',
                    'enum' => ['auto', 'apple', 'google'],
                    'description' => 'Qual aplicativo usar (auto prefere Apple Reminders se conectado, ou Google Tasks).',
                ],
            ],
            'required' => ['title'],
        ];
    }

    public function execute(array $arguments, ToolExecutionContext $context): array
    {
        try {
            $user = $context->user;
            $userTz = $user->timezone ?: 'America/Sao_Paulo';
            $dueAt = ! empty($arguments['due_at']) ? Carbon::parse($arguments['due_at'])->setTimezone($userTz) : null;
            $provider = $arguments['provider'] ?? 'auto';

            $hasApple = (bool) $user->integration(UserIntegration::PROVIDER_APPLE_CALDAV);
            $hasGoogle = (bool) $user->integration(UserIntegration::PROVIDER_GOOGLE);

            $chosenProvider = match ($provider) {
                'apple' => 'apple',
                'google' => 'google',
                default => $hasApple ? 'apple' : ($hasGoogle ? 'google' : null),
            };

            $externalId = 'rem_' . uniqid();

            if ($chosenProvider === 'apple' && $hasApple) {
                $priorityNum = match ($arguments['priority'] ?? 'medium') {
                    'high' => 1,
                    'low' => 9,
                    default => 5,
                };

                $created = $this->appleService->createReminder($user, [
                    'title' => $arguments['title'],
                    'description' => $arguments['description'] ?? null,
                    'due_at' => $dueAt,
                    'priority' => $priorityNum,
                ]);
                $externalId = $created['uid'] ?? $externalId;
            } elseif ($chosenProvider === 'google' && $hasGoogle) {
                $created = $this->googleService->createTask($user, [
                    'title' => $arguments['title'],
                    'description' => $arguments['description'] ?? null,
                    'due_at' => $dueAt,
                ]);
                $externalId = $created['id'] ?? $externalId;
            }

            // Salva no banco de dados local
            $event = CalendarEvent::create([
                'user_id' => $user->id,
                'provider' => $chosenProvider ?: 'internal',
                'kind' => 'reminder',
                'external_id' => $externalId,
                'title' => $arguments['title'],
                'description' => $arguments['description'] ?? null,
                'starts_at' => $dueAt,
                'created_by_agent' => true,
                'status' => 'confirmed',
                'synced_at' => now(),
            ]);

            return [
                'success' => true,
                'reminder_id' => $event->id,
                'title' => $event->title,
                'provider' => $chosenProvider ?: 'lembrete interno',
                'due_at' => $dueAt?->toIso8601String(),
                'message' => "Lembrete \"{$event->title}\" agendado com sucesso para {$dueAt?->format('d/m/Y H:i')}.",
            ];
        } catch (\Throwable $e) {
            return [
                'success' => false,
                'error' => 'Falha ao criar lembrete: ' . $e->getMessage(),
            ];
        }
    }
}

