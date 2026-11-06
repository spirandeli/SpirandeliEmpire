<?php

namespace Tests\Feature\Integrations;

use App\Jobs\SyncAppleCalDavJob;
use App\Models\User;
use App\Models\UserIntegration;
use App\Services\AppleCalDavService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Queue;
use Tests\TestCase;

class AppleCalDavTest extends TestCase
{
    use RefreshDatabase;

    private User $user;
    private AppleCalDavService $service;

    protected function setUp(): void
    {
        parent::setUp();
        $this->user = User::factory()->create();
        $this->service = app(AppleCalDavService::class);
        $this->actingAs($this->user, 'sanctum');
    }

    public function test_discover_endpoints_parses_principal_and_calendar_home_set(): void
    {
        UserIntegration::create([
            'user_id' => $this->user->id,
            'provider' => UserIntegration::PROVIDER_APPLE_CALDAV,
            'credentials' => [
                'apple_id' => 'spira@icloud.com',
                'app_password' => 'abcd-efgh-ijkl-mnop',
            ],
            'meta' => [
                'server_url' => 'https://caldav.icloud.com',
            ],
        ]);

        $xmlPrincipalResponse = <<<XML
<?xml version="1.0" encoding="utf-8" ?>
<D:multistatus xmlns:D="DAV:">
  <D:response>
    <D:propstat>
      <D:prop>
        <D:current-user-principal>
          <D:href>/123456789/principal/</D:href>
        </D:current-user-principal>
      </D:prop>
    </D:propstat>
  </D:response>
</D:multistatus>
XML;

        $xmlHomeResponse = <<<XML
<?xml version="1.0" encoding="utf-8" ?>
<D:multistatus xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:response>
    <D:propstat>
      <D:prop>
        <C:calendar-home-set>
          <D:href>/123456789/calendars/</D:href>
        </C:calendar-home-set>
      </D:prop>
    </D:propstat>
  </D:response>
</D:multistatus>
XML;

        Http::fake([
            'https://caldav.icloud.com/' => Http::response($xmlPrincipalResponse, 207),
            'https://caldav.icloud.com/123456789/principal/' => Http::response($xmlHomeResponse, 207),
        ]);

        $result = $this->service->discoverEndpoints($this->user);

        $this->assertTrue($result['verified']);
        $this->assertSame('https://caldav.icloud.com/123456789/principal/', $result['principal_url']);
        $this->assertSame('https://caldav.icloud.com/123456789/calendars/', $result['calendar_home_set']);
    }

    public function test_create_event_and_reminder_in_apple_caldav(): void
    {
        UserIntegration::create([
            'user_id' => $this->user->id,
            'provider' => UserIntegration::PROVIDER_APPLE_CALDAV,
            'status' => 'connected',
            'credentials' => [
                'apple_id' => 'spira@icloud.com',
                'app_password' => 'abcd-efgh-ijkl-mnop',
            ],
            'meta' => [
                'server_url' => 'https://caldav.icloud.com',
                'calendar_home_set' => 'https://caldav.icloud.com/123456789/calendars/',
            ],
        ]);

        Http::fake([
            'caldav.icloud.com/*' => Http::response('', 201),
        ]);

        $resEvent = $this->service->createEvent($this->user, [
            'title' => 'Gravação Vídeo TikTok',
            'starts_at' => now()->addDay(),
            'ends_at' => now()->addDay()->addHour(),
        ]);
        $this->assertTrue($resEvent['success']);
        $this->assertNotEmpty($resEvent['uid']);

        $resReminder = $this->service->createReminder($this->user, [
            'title' => 'Aprovar roteiro de afiliados',
            'due_at' => now()->addHours(5),
            'priority' => 1,
        ]);
        $this->assertTrue($resReminder['success']);
        $this->assertNotEmpty($resReminder['uid']);
    }

    public function test_sync_apple_caldav_job_dispatches(): void
    {
        Queue::fake();

        $this->postJson('/api/integrations/apple-caldav/sync')->assertOk();

        Queue::assertPushed(SyncAppleCalDavJob::class);
    }
}
