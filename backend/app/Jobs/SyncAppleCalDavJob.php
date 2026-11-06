<?php

namespace App\Jobs;

use App\Models\User;
use App\Models\UserIntegration;
use App\Services\AppleCalDavService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;

class SyncAppleCalDavJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 3;
    public int $timeout = 120;

    public function __construct(public readonly User $user)
    {
        $this->onQueue('integrations');
    }

    public function handle(AppleCalDavService $appleService): void
    {
        $integration = $this->user->integration(UserIntegration::PROVIDER_APPLE_CALDAV);
        if (! $integration || ! $integration->isConnected()) {
            return;
        }

        try {
            $endpoints = $appleService->discoverEndpoints($this->user);

            if ($endpoints['verified']) {
                $integration->markSynced();
            }
        } catch (\Throwable $e) {
            Log::error('Erro ao sincronizar Apple CalDAV no Job', [
                'user_id' => $this->user->id,
                'error' => $e->getMessage(),
            ]);
            $integration->markError('Falha ao sincronizar iCloud CalDAV: ' . $e->getMessage());
        }
    }
}

