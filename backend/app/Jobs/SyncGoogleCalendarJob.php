<?php

namespace App\Jobs;

use App\Models\CalendarEvent;
use App\Models\User;
use App\Models\UserIntegration;
use App\Services\GoogleWorkspaceService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Log;

class SyncGoogleCalendarJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 3;
    public int $timeout = 120;

    public function __construct(public readonly User $user)
    {
        $this->onQueue('integrations');
    }

    public function handle(GoogleWorkspaceService $googleService): void
    {
        $integration = $this->user->integration(UserIntegration::PROVIDER_GOOGLE);
        if (! $integration || ! $integration->isConnected()) {
            return;
        }

        $from = now()->subDays(7);
        $to = now()->addDays(30);

        try {
            $events = $googleService->listEvents($this->user, $from, $to);

            foreach ($events as $raw) {
                $externalId = $raw['id'] ?? null;
                if (! $externalId) {
                    continue;
                }

                $startsAtStr = $raw['start']['dateTime'] ?? $raw['start']['date'] ?? null;
                $endsAtStr = $raw['end']['dateTime'] ?? $raw['end']['date'] ?? null;
                $allDay = isset($raw['start']['date']) && ! isset($raw['start']['dateTime']);

                $startsAt = $startsAtStr ? Carbon::parse($startsAtStr) : null;
                $endsAt = $endsAtStr ? Carbon::parse($endsAtStr) : null;

                CalendarEvent::updateOrCreate(
                    [
                        'user_id' => $this->user->id,
                        'provider' => 'google',
                        'external_id' => $externalId,
                    ],
                    [
                        'user_integration_id' => $integration->id,
                        'kind' => 'event',
                        'title' => $raw['summary'] ?? '(Sem título)',
                        'description' => $raw['description'] ?? null,
                        'location' => $raw['location'] ?? null,
                        'starts_at' => $startsAt,
                        'ends_at' => $endsAt,
                        'all_day' => $allDay,
                        'status' => $raw['status'] ?? 'confirmed',
                        'raw' => $raw,
                        'synced_at' => now(),
                    ]
                );
            }

            $integration->markSynced();
        } catch (\Throwable $e) {
            Log::error('Erro ao sincronizar Google Calendar no Job', [
                'user_id' => $this->user->id,
                'error' => $e->getMessage(),
            ]);
            $integration->markError('Falha na sincronização do Google Calendar: ' . $e->getMessage());
        }
    }
}

