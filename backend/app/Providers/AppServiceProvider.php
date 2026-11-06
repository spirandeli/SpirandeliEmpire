<?php

namespace App\Providers;

use App\Models\ApprovalQueue;
use App\Models\Business;
use App\Models\ContentAsset;
use App\Models\Task;
use App\Models\TikTokProduct;
use App\Models\User;
use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Database\Eloquent\Relations\Relation;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->singleton(\App\Services\GeminiAgentService::class, function ($app) {
            return \App\Services\GeminiAgentService::createDefault(
                $app->make(\App\Services\IntegrationService::class),
                $app->make(\App\Services\BusinessService::class),
                $app->make(\App\Services\TaskService::class),
                $app->make(\App\Services\ApprovalService::class),
                $app->make(\App\Services\GoogleWorkspaceService::class),
                $app->make(\App\Services\AppleCalDavService::class),
            );
        });
    }

    public function boot(): void
    {
        // Aliases estáveis para colunas polimórficas (approvable_type, tokenable_type).
        Relation::morphMap([
            'user' => User::class,
            'business' => Business::class,
            'task' => Task::class,
            'approval_queue' => ApprovalQueue::class,
            'tiktok_product' => TikTokProduct::class,
            'content_asset' => ContentAsset::class,
        ]);

        RateLimiter::for('api', fn (Request $request) => Limit::perMinute(240)->by(
            $request->user()?->id ?: $request->ip()
        ));

        // Chat com o agente consome tokens do Gemini: limite mais baixo por usuário.
        RateLimiter::for('agent', fn (Request $request) => Limit::perMinute(30)->by(
            $request->user()?->id ?: $request->ip()
        ));

        // Listener: reescrita autônoma de entregas quando o usuário solicita ajuste na fila
        \Illuminate\Support\Facades\Event::listen(
            \App\Events\ApprovalRevisionRequested::class,
            function (\App\Events\ApprovalRevisionRequested $event) {
                \App\Jobs\ProcessApprovalRevisionJob::dispatch(
                    $event->approval,
                    $event->feedback,
                    $event->section
                );
            }
        );
    }
}

