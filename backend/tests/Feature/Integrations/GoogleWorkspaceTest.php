<?php

namespace Tests\Feature\Integrations;

use App\Jobs\SyncGoogleCalendarJob;
use App\Models\CalendarEvent;
use App\Models\User;
use App\Models\UserIntegration;
use App\Services\GoogleWorkspaceService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Queue;
use Tests\TestCase;

class GoogleWorkspaceTest extends TestCase
{
    use RefreshDatabase;

    private User $user;
    private GoogleWorkspaceService $service;

    protected function setUp(): void
    {
        parent::setUp();
        $this->user = User::factory()->create();
        config([
            'services.google.client_id' => 'GOOGLE-CLIENT-ID-123.apps.googleusercontent.com',
            'services.google.client_secret' => 'GOOGLE-CLIENT-SECRET-XYZ',
            'services.google.redirect' => 'http://localhost:8080/api/integrations/google/callback',
        ]);
        $this->service = app(GoogleWorkspaceService::class);
        $this->actingAs($this->user, 'sanctum');
    }

    public function test_get_authorization_url_generates_valid_oauth_params(): void
    {
        $url = $this->service->getAuthorizationUrl($this->user);

        $this->assertStringStartsWith('https://accounts.google.com/o/oauth2/v2/auth?', $url);
        $this->assertStringContainsString('client_id=GOOGLE-CLIENT-ID-123', $url);
        $this->assertStringContainsString('access_type=offline', $url);
        $this->assertStringContainsString('prompt=consent', $url);
        $this->assertStringContainsString('calendar', $url);
        $this->assertStringContainsString('tasks', $url);

        $response = $this->getJson('/api/integrations/google/redirect')->assertOk();
        $this->assertStringContainsString('https://accounts.google.com', $response->json('auth_url'));
    }

    public function test_handle_callback_stores_encrypted_tokens_and_profile_meta(): void
    {
        Http::fake([
            'oauth2.googleapis.com/token' => Http::response([
                'access_token' => 'ya29.fake-access-token-12345',
                'refresh_token' => '1//fake-refresh-token-67890',
                'expires_in' => 3600,
                'token_type' => 'Bearer',
                'scope' => 'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/tasks',
            ], 200),
            'www.googleapis.com/oauth2/v3/userinfo' => Http::response([
                'email' => 'ceo@google.com',
                'name' => 'Fundador Google',
            ], 200),
        ]);

        $integration = $this->service->handleCallback('fake-auth-code');

        $this->assertSame(UserIntegration::PROVIDER_GOOGLE, $integration->provider);
        $this->assertSame('connected', $integration->status);
        $this->assertSame('ya29.fake-access-token-12345', $integration->credential('access_token'));
        $this->assertSame('1//fake-refresh-token-67890', $integration->credential('refresh_token'));
        $this->assertSame('ceo@google.com', $integration->meta['email']);
    }

    public function test_get_valid_access_token_refreshes_automatically_when_expired(): void
    {
        $integration = UserIntegration::create([
            'user_id' => $this->user->id,
            'provider' => UserIntegration::PROVIDER_GOOGLE,
            'credentials' => [
                'access_token' => 'expired-token',
                'refresh_token' => 'valid-refresh-token',
            ],
            'expires_at' => now()->subMinutes(10), // expirado
        ]);

        Http::fake([
            'oauth2.googleapis.com/token' => Http::response([
                'access_token' => 'new-fresh-access-token',
                'expires_in' => 3600,
            ], 200),
        ]);

        $freshToken = $this->service->getValidAccessToken($this->user);

        $this->assertSame('new-fresh-access-token', $freshToken);
        $this->assertSame('new-fresh-access-token', $integration->refresh()->credential('access_token'));
        $this->assertTrue($integration->expires_at->isAfter(now()->addMinutes(30)));
    }

    public function test_create_event_and_task_in_google_apis(): void
    {
        UserIntegration::create([
            'user_id' => $this->user->id,
            'provider' => UserIntegration::PROVIDER_GOOGLE,
            'credentials' => [
                'access_token' => 'valid-token',
                'refresh_token' => 'refresh-token',
            ],
            'expires_at' => now()->addHour(),
        ]);

        Http::fake([
            'www.googleapis.com/calendar/v3/calendars/primary/events' => Http::response([
                'id' => 'g_event_123',
                'summary' => 'Gravação de Vídeo',
                'status' => 'confirmed',
            ], 200),
            'tasks.googleapis.com/*' => Http::response([
                'id' => 'g_task_456',
                'title' => 'Revisar roteiro',
            ], 200),
        ]);

        $event = $this->service->createEvent($this->user, [
            'title' => 'Gravação de Vídeo',
            'starts_at' => now()->addDay(),
            'ends_at' => now()->addDay()->addHour(),
        ]);
        $this->assertSame('g_event_123', $event['id']);

        $task = $this->service->createTask($this->user, [
            'title' => 'Revisar roteiro',
        ]);
        $this->assertSame('g_task_456', $task['id']);
    }

    public function test_sync_google_calendar_job_persists_events_in_local_cache(): void
    {
        $integration = UserIntegration::create([
            'user_id' => $this->user->id,
            'provider' => UserIntegration::PROVIDER_GOOGLE,
            'credentials' => [
                'access_token' => 'valid-token',
                'refresh_token' => 'refresh-token',
            ],
            'expires_at' => now()->addHour(),
        ]);

        Http::fake([
            'www.googleapis.com/calendar/v3/calendars/primary/events*' => Http::response([
                'items' => [
                    [
                        'id' => 'ext_google_event_99',
                        'summary' => 'Reunião de Diretoria',
                        'start' => ['dateTime' => now()->addHours(3)->toRfc3339String()],
                        'end' => ['dateTime' => now()->addHours(4)->toRfc3339String()],
                        'status' => 'confirmed',
                    ],
                ],
            ], 200),
        ]);

        $job = new SyncGoogleCalendarJob($this->user);
        $job->handle($this->service);

        $this->assertDatabaseHas('calendar_events', [
            'user_id' => $this->user->id,
            'provider' => 'google',
            'external_id' => 'ext_google_event_99',
            'title' => 'Reunião de Diretoria',
        ]);
    }

    public function test_sync_endpoint_dispatches_job(): void
    {
        Queue::fake();

        $this->postJson('/api/integrations/google/sync')->assertOk();

        Queue::assertPushed(SyncGoogleCalendarJob::class);
    }
}
