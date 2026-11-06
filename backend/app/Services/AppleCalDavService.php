<?php

namespace App\Services;

use App\Models\User;
use App\Models\UserIntegration;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

class AppleCalDavService
{
    private const DEFAULT_SERVER = 'https://caldav.icloud.com';

    public function __construct(private readonly IntegrationService $integrationService)
    {
    }

    /**
     * Valida credenciais e descobre os endpoints de calendário e lembretes do usuário iCloud.
     *
     * @return array{verified: bool, principal_url: ?string, calendar_home_set: ?string}
     */
    public function discoverEndpoints(User $user): array
    {
        $integration = $user->integration(UserIntegration::PROVIDER_APPLE_CALDAV);
        if (! $integration) {
            return ['verified' => false, 'principal_url' => null, 'calendar_home_set' => null];
        }

        $appleId = $integration->credential('apple_id');
        $password = $integration->credential('app_password');
        $serverUrl = rtrim($integration->meta['server_url'] ?? self::DEFAULT_SERVER, '/');

        // 1. PROPFIND na raiz para descobrir current-user-principal
        $xmlBody = <<<XML
<?xml version="1.0" encoding="utf-8" ?>
<D:propfind xmlns:D="DAV:">
  <D:prop>
    <D:current-user-principal />
  </D:prop>
</D:propfind>
XML;

        $response = $this->client($appleId, $password)
            ->withHeaders(['Depth' => '0', 'Content-Type' => 'application/xml; charset="utf-8"'])
            ->send('PROPFIND', $serverUrl . '/', ['body' => $xmlBody]);

        if (! $response->successful()) {
            $integration->markError('Credenciais CalDAV inválidas ou recusadas pelo iCloud.', expired: true);
            return ['verified' => false, 'principal_url' => null, 'calendar_home_set' => null];
        }

        $body = $response->body();
        preg_match('/<D:current-user-principal[^>]*>.*?<D:href[^>]*>([^<]+)<\/D:href>/s', $body, $matches);
        $principalHref = $matches[1] ?? null;

        if (! $principalHref) {
            $integration->markError('Não foi possível localizar o Principal URL no iCloud.');
            return ['verified' => false, 'principal_url' => null, 'calendar_home_set' => null];
        }

        $principalUrl = str_starts_with($principalHref, 'http')
            ? $principalHref
            : $serverUrl . '/' . ltrim($principalHref, '/');

        // 2. PROPFIND no principal para descobrir calendar-home-set
        $xmlHome = <<<XML
<?xml version="1.0" encoding="utf-8" ?>
<D:propfind xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:caldav">
  <D:prop>
    <C:calendar-home-set />
  </D:prop>
</D:propfind>
XML;

        $resHome = $this->client($appleId, $password)
            ->withHeaders(['Depth' => '0', 'Content-Type' => 'application/xml; charset="utf-8"'])
            ->send('PROPFIND', $principalUrl, ['body' => $xmlHome]);

        $homeBody = $resHome->body();
        preg_match('/<C:calendar-home-set[^>]*>.*?<D:href[^>]*>([^<]+)<\/D:href>/s', $homeBody, $matchesHome);
        $calendarHomeHref = $matchesHome[1] ?? null;

        $calendarHomeSet = $calendarHomeHref
            ? (str_starts_with($calendarHomeHref, 'http') ? $calendarHomeHref : $serverUrl . '/' . ltrim($calendarHomeHref, '/'))
            : null;

        $integration->meta = array_merge($integration->meta ?? [], [
            'verified' => true,
            'principal_url' => $principalUrl,
            'calendar_home_set' => $calendarHomeSet,
        ]);
        $integration->status = 'connected';
        $integration->last_error = null;
        $integration->save();

        return [
            'verified' => true,
            'principal_url' => $principalUrl,
            'calendar_home_set' => $calendarHomeSet,
        ];
    }

    /**
     * Cria um evento (VEVENT) no calendário da Apple.
     *
     * @param  array{title: string, description?: string, starts_at: Carbon, ends_at: Carbon, location?: string}  $data
     * @return array{success: bool, uid: string, href: ?string}
     */
    public function createEvent(User $user, array $data, ?string $calendarUrl = null): array
    {
        $integration = $user->integration(UserIntegration::PROVIDER_APPLE_CALDAV);
        if (! $integration) {
            throw new \RuntimeException('Apple CalDAV não configurado.');
        }

        $appleId = $integration->credential('apple_id');
        $password = $integration->credential('app_password');

        $targetUrl = $calendarUrl
            ?: data_get($integration->meta, 'default_calendar_url')
            ?: data_get($integration->meta, 'calendar_home_set');

        if (! $targetUrl) {
            $endpoints = $this->discoverEndpoints($user);
            $targetUrl = $endpoints['calendar_home_set'] ?? self::DEFAULT_SERVER;
        }

        $uid = (string) Str::uuid();
        $dtStamp = now()->utc()->format('Ymd\THis\Z');
        $dtStart = $data['starts_at']->utc()->format('Ymd\THis\Z');
        $dtEnd = $data['ends_at']->utc()->format('Ymd\THis\Z');
        $summary = $this->escapeIcs($data['title']);
        $description = isset($data['description']) ? $this->escapeIcs($data['description']) : '';
        $location = isset($data['location']) ? $this->escapeIcs($data['location']) : '';

        $vcalendar = <<<ICS
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ABVOS//Autonomous Business Venture OS//PT
CALSCALE:GREGORIAN
BEGIN:VEVENT
UID:{$uid}
DTSTAMP:{$dtStamp}
DTSTART:{$dtStart}
DTEND:{$dtEnd}
SUMMARY:{$summary}
DESCRIPTION:{$description}
LOCATION:{$location}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
ICS;

        $eventUrl = rtrim($targetUrl, '/') . "/{$uid}.ics";

        $response = $this->client($appleId, $password)
            ->withHeaders(['Content-Type' => 'text/calendar; charset=utf-8'])
            ->send('PUT', $eventUrl, ['body' => $vcalendar]);

        if (! in_array($response->status(), [200, 201, 204], true)) {
            Log::error('Erro ao criar evento CalDAV no iCloud', [
                'status' => $response->status(),
                'response' => $response->body(),
            ]);
            throw new \RuntimeException('Falha ao criar evento no Apple Calendar via CalDAV: ' . $response->body());
        }

        return [
            'success' => true,
            'uid' => $uid,
            'href' => $eventUrl,
        ];
    }

    /**
     * Cria um lembrete (VTODO) compatível com o Apple Reminders / Lembretes do iOS/macOS.
     *
     * @param  array{title: string, description?: string, due_at?: Carbon, priority?: int}  $data
     * @return array{success: bool, uid: string, href: ?string}
     */
    public function createReminder(User $user, array $data, ?string $remindersUrl = null): array
    {
        $integration = $user->integration(UserIntegration::PROVIDER_APPLE_CALDAV);
        if (! $integration) {
            throw new \RuntimeException('Apple CalDAV não configurado.');
        }

        $appleId = $integration->credential('apple_id');
        $password = $integration->credential('app_password');

        $targetUrl = $remindersUrl
            ?: data_get($integration->meta, 'default_reminders_url')
            ?: data_get($integration->meta, 'calendar_home_set');

        if (! $targetUrl) {
            $endpoints = $this->discoverEndpoints($user);
            $targetUrl = $endpoints['calendar_home_set'] ?? self::DEFAULT_SERVER;
        }

        $uid = (string) Str::uuid();
        $dtStamp = now()->utc()->format('Ymd\THis\Z');
        $summary = $this->escapeIcs($data['title']);
        $description = isset($data['description']) ? $this->escapeIcs($data['description']) : '';
        $priority = $data['priority'] ?? 5; // 1 = Alta, 5 = Média, 9 = Baixa

        $dueLine = '';
        if (! empty($data['due_at'])) {
            $dueUtc = $data['due_at']->utc()->format('Ymd\THis\Z');
            $dueLine = "DUE:{$dueUtc}\n";
        }

        $vtodo = <<<ICS
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//ABVOS//Autonomous Business Venture OS//PT
CALSCALE:GREGORIAN
BEGIN:VTODO
UID:{$uid}
DTSTAMP:{$dtStamp}
SUMMARY:{$summary}
DESCRIPTION:{$description}
{$dueLine}PRIORITY:{$priority}
STATUS:NEEDS-ACTION
END:VTODO
END:VCALENDAR
ICS;

        $reminderUrl = rtrim($targetUrl, '/') . "/{$uid}.ics";

        $response = $this->client($appleId, $password)
            ->withHeaders(['Content-Type' => 'text/calendar; charset=utf-8'])
            ->send('PUT', $reminderUrl, ['body' => $vtodo]);

        if (! in_array($response->status(), [200, 201, 204], true)) {
            Log::error('Erro ao criar lembrete CalDAV no iCloud', [
                'status' => $response->status(),
                'response' => $response->body(),
            ]);
            throw new \RuntimeException('Falha ao criar lembrete no Apple Reminders: ' . $response->body());
        }

        return [
            'success' => true,
            'uid' => $uid,
            'href' => $reminderUrl,
        ];
    }

    private function client(string $username, string $password)
    {
        return Http::withBasicAuth($username, $password)
            ->timeout(20)
            ->withUserAgent('ABVOS-Agent/1.0 (CalDAV Sync)');
    }

    private function escapeIcs(string $text): string
    {
        return str_replace(["\\", "\n", ",", ";"], ["\\\\", "\\n", "\\,", "\\;"], $text);
    }
}
