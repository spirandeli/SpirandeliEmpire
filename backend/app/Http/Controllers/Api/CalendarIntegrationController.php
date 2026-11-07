<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\CalendarEvent;
use App\Models\User;
use App\Services\CalendarFeedService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Response;

class CalendarIntegrationController extends Controller
{
    public function __construct(
        private readonly CalendarFeedService $feedService
    ) {
    }

    /**
     * Rota 1 — Assinatura de Feed Dinâmico RFC 5545 (Zero-Auth / Stateless).
     * GET /api/v1/calendar/feed/{calendar_token}.ics
     *
     * Permite que clientes de calendário (Apple Calendar / Google Agenda)
     * façam o polling periódico em background sem necessidade de sessão/cookies.
     */
    public function feed(string $calendarToken): Response
    {
        // Se a rota receber com o sufixo .ics, remove para buscar apenas o token
        $cleanToken = str_ends_with($calendarToken, '.ics')
            ? substr($calendarToken, 0, -4)
            : $calendarToken;

        $user = User::where('calendar_token', $cleanToken)->first();

        if (! $user) {
            abort(404, 'Feed de calendário não encontrado ou token inválido.');
        }

        $icsContent = $this->feedService->generateFeedForUser($user);

        return response($icsContent, 200, [
            'Content-Type' => 'text/calendar; charset=utf-8',
            'Content-Disposition' => 'inline; filename="agenda.ics"',
            'Cache-Control' => 'no-cache, no-store, max-age=0, must-revalidate',
            'Pragma' => 'no-cache',
            'Expires' => '0',
        ]);
    }

    /**
     * Rota 2 — Download de Evento Único (.ics).
     * GET /api/v1/calendar/events/{event}/download
     */
    public function downloadSingleEvent(Request $request, CalendarEvent $event): Response
    {
        $icsContent = $this->feedService->generateSingleEventIcs($event);

        $filename = sprintf('evento-%s.ics', $event->id);

        return response($icsContent, 200, [
            'Content-Type' => 'text/calendar; charset=utf-8',
            'Content-Disposition' => sprintf('attachment; filename="%s"', $filename),
            'Cache-Control' => 'no-cache, no-store, max-age=0, must-revalidate',
            'Pragma' => 'no-cache',
        ]);
    }

    /**
     * Rota Auxiliar Autenticada — Retorna a URL do feed e token do usuário conectado.
     * GET /api/v1/calendar/me/feed-url
     */
    public function getMyFeedUrl(Request $request): JsonResponse
    {
        $user = $request->user();
        $token = $user->getOrCreateCalendarToken();
        $feedUrl = url("/api/v1/calendar/feed/{$token}.ics");
        $webcalUrl = preg_replace('/^https?:/i', 'webcal:', $feedUrl);

        return response()->json([
            'calendar_token' => $token,
            'feed_url' => $feedUrl,
            'webcal_url' => $webcalUrl,
            'upcoming_events_count' => $user->calendarEvents()->where('starts_at', '>=', now())->count(),
        ]);
    }
}

