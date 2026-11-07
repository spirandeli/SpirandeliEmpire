<?php

namespace App\Services;

use App\Models\CalendarEvent;
use App\Models\User;
use Carbon\Carbon;
use Illuminate\Support\Collection;

/**
 * Serviço responsável por gerar arquivos e feeds iCalendar (.ics)
 * em estrita conformidade com a especificação RFC 5545 (CRLF obrigatório).
 */
class CalendarFeedService
{
    private const CRLF = "\r\n";
    private const PRODID = '-//SpirandeliEmpire//SpirandeliEmpire Calendar 2.0//PT';

    /**
     * Gera o feed iCalendar completo com todos os eventos futuros e recentes do usuário.
     */
    public function generateFeedForUser(User $user, int $daysPast = 30, int $daysFuture = 365): string
    {
        $since = Carbon::now()->subDays($daysPast);
        $until = Carbon::now()->addDays($daysFuture);

        // Busca eventos do usuário no intervalo
        $events = CalendarEvent::query()
            ->where('user_id', $user->id)
            ->where('status', '!=', 'cancelled')
            ->where(function ($query) use ($since, $until) {
                $query->whereBetween('starts_at', [$since, $until])
                    ->orWhere(function ($q) use ($since) {
                        $q->whereNull('ends_at')
                            ->where('starts_at', '>=', $since);
                    });
            })
            ->orderBy('starts_at', 'asc')
            ->get();

        $calendarName = sprintf('Spirandeli Empire - %s', $user->name);
        $calendarDescription = 'Agenda sincronizada nativa via feed RFC 5545 (Spirandeli Empire)';

        return $this->buildIcalendarString($events, $calendarName, $calendarDescription);
    }

    /**
     * Gera o arquivo .ics para download de um único evento específico.
     *
     * @param  CalendarEvent|array<string, mixed>|object  $event
     */
    public function generateSingleEventIcs(mixed $event): string
    {
        $calendarName = 'Spirandeli Empire - Agendamento';
        $calendarDescription = 'Confirmação de evento gerada pelo Spirandeli Empire';

        $collection = collect([$event]);

        return $this->buildIcalendarString($collection, $calendarName, $calendarDescription);
    }

    /**
     * Constrói o corpo VCALENDAR com linhas terminadas estritamente em CRLF (\r\n).
     *
     * @param  Collection<int, mixed>  $events
     */
    private function buildIcalendarString(Collection $events, string $calendarName, string $calendarDescription): string
    {
        $crlf = self::CRLF;
        $lines = [];

        // Cabeçalho obrigatório RFC 5545
        $lines[] = 'BEGIN:VCALENDAR';
        $lines[] = 'VERSION:2.0';
        $lines[] = 'PRODID:' . self::PRODID;
        $lines[] = 'CALSCALE:GREGORIAN';
        $lines[] = 'METHOD:PUBLISH';
        $lines[] = 'X-WR-CALNAME:' . $this->escapeText($calendarName);
        $lines[] = 'X-WR-CALDESC:' . $this->escapeText($calendarDescription);
        $lines[] = 'X-WR-TIMEZONE:UTC';
        $lines[] = 'X-WR-TTL:PT1H'; // Sugestão aos clientes para refresh a cada 1 hora

        foreach ($events as $event) {
            $lines = array_merge($lines, $this->buildVeventLines($event));
        }

        $lines[] = 'END:VCALENDAR';

        // Garante que toda quebra de linha seja rigorosamente \r\n (CRLF) e termine com \r\n
        return implode($crlf, $lines) . $crlf;
    }

    /**
     * Constrói o bloco VEVENT para um evento específico.
     *
     * @param  CalendarEvent|array<string, mixed>|object  $event
     * @return array<int, string>
     */
    private function buildVeventLines(mixed $event): array
    {
        $id = data_get($event, 'id', '0');
        $title = (string) data_get($event, 'title', 'Novo Agendamento');
        $description = (string) data_get($event, 'description', '');
        $location = (string) data_get($event, 'location', '');
        $startsAt = data_get($event, 'starts_at') ?? data_get($event, 'start_at');
        $endsAt = data_get($event, 'ends_at') ?? data_get($event, 'end_at');

        $startCarbon = $startsAt ? Carbon::parse($startsAt) : Carbon::now();
        $endCarbon = $endsAt ? Carbon::parse($endsAt) : (clone $startCarbon)->addMinutes(30);

        // Conversão obrigatória para UTC no padrão Ymd\THis\Z
        $dtStartUtc = $startCarbon->copy()->utc()->format('Ymd\THis\Z');
        $dtEndUtc = $endCarbon->copy()->utc()->format('Ymd\THis\Z');
        $dtStampUtc = Carbon::now()->utc()->format('Ymd\THis\Z');

        $domain = parse_url(config('app.url', 'http://localhost'), PHP_URL_HOST) ?: 'spirandeliempire.com';
        $uid = sprintf('event-%s@%s', $id, $domain);

        $vevent = [
            'BEGIN:VEVENT',
            'UID:' . $uid,
            'DTSTAMP:' . $dtStampUtc,
            'DTSTART:' . $dtStartUtc,
            'DTEND:' . $dtEndUtc,
            'SUMMARY:' . $this->escapeText($title),
            'DESCRIPTION:' . $this->escapeText($description),
            'LOCATION:' . $this->escapeText($location),
            'STATUS:CONFIRMED',
            // Alarme nativo de lembrete 15 minutos antes
            'BEGIN:VALARM',
            'TRIGGER:-PT15M',
            'ACTION:DISPLAY',
            'DESCRIPTION:' . $this->escapeText($title),
            'END:VALARM',
            'END:VEVENT',
        ];

        return $vevent;
    }

    /**
     * Sanitiza caracteres especiais de texto conforme a especificação RFC 5545 (seção 3.3.11):
     * - Caracteres '\', ';', ',' são escapados com barra invertida (\).
     * - Quebras de linha (\r\n, \r, \n) são convertidas na string literal '\n' (duas letras: barra e n).
     */
    public function escapeText(?string $text): string
    {
        if ($text === null || $text === '') {
            return '';
        }

        // 1. Escapa barras invertidas primeiro para não re-escapar as criadas a seguir
        $escaped = str_replace('\\', '\\\\', $text);

        // 2. Normaliza quebras de linha para a sequência literal de dois caracteres \n
        $escaped = preg_replace("/\r\n|\r|\n/", '\\n', $escaped);

        // 3. Escapa ponto-e-vírgula e vírgula
        $escaped = str_replace([';', ','], ['\\;', '\\,'], $escaped);

        return $escaped;
    }
}

