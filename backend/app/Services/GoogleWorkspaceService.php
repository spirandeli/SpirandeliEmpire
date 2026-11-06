<?php

namespace App\Services;

use App\Models\CalendarEvent;
use App\Models\User;
use App\Models\UserIntegration;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Illuminate\Validation\ValidationException;

class GoogleWorkspaceService
{
    private const OAUTH_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth';
    private const OAUTH_TOKEN_URL = 'https://oauth2.googleapis.com/token';
    private const CALENDAR_API_BASE = 'https://www.googleapis.com/calendar/v3';
    private const TASKS_API_BASE = 'https://tasks.googleapis.com/tasks/v1';

    public function __construct(private readonly IntegrationService $integrationService)
    {
    }

    /**
     * Gera a URL de autorização OAuth2 para redirecionar o usuário.
     */
    public function getAuthorizationUrl(User $user, ?string $redirectUri = null): string
    {
        $clientId = config('services.google.client_id');
        $redirect = $redirectUri ?: config('services.google.redirect');
        $scopes = config('services.google.scopes', [
            'openid',
            'email',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/tasks',
        ]);

        if (empty($clientId)) {
            throw ValidationException::withMessages([
                'google' => 'GOOGLE_CLIENT_ID não configurado no backend/.env.',
            ]);
        }

        $params = [
            'client_id' => $clientId,
            'redirect_uri' => $redirect,
            'response_type' => 'code',
            'scope' => implode(' ', $scopes),
            'access_type' => 'offline',
            'prompt' => 'consent',
            'state' => encrypt(['user_id' => $user->id, 'created_at' => now()->timestamp]),
        ];

        return self::OAUTH_AUTH_URL . '?' . http_build_query($params);
    }

    /**
     * Processa o callback OAuth e salva as credenciais de acesso no cofre.
     */
    public function handleCallback(string $code, ?string $redirectUri = null): UserIntegration
    {
        $clientId = config('services.google.client_id');
        $clientSecret = config('services.google.client_secret');
        $redirect = $redirectUri ?: config('services.google.redirect');

        $response = Http::asForm()->timeout(15)->post(self::OAUTH_TOKEN_URL, [
            'client_id' => $clientId,
            'client_secret' => $clientSecret,
            'code' => $code,
            'grant_type' => 'authorization_code',
            'redirect_uri' => $redirect,
        ]);

        if (! $response->successful()) {
            Log::error('Erro ao trocar código OAuth do Google por token', [
                'status' => $response->status(),
                'response' => $response->json(),
            ]);
            throw ValidationException::withMessages([
                'code' => 'Falha ao autenticar com o Google: ' . ($response->json('error_description') ?? 'Código inválido ou expirado.'),
            ]);
        }

        $tokenData = $response->json();
        $accessToken = $tokenData['access_token'];
        $refreshToken = $tokenData['refresh_token'] ?? null;
        $expiresIn = $tokenData['expires_in'] ?? 3600;

        // Recupera dados do perfil Google
        $userInfo = Http::withToken($accessToken)
            ->timeout(10)
            ->get('https://www.googleapis.com/oauth2/v3/userinfo')
            ->json();

        $email = $userInfo['email'] ?? null;

        // Localiza usuário através do contexto da sessão ou do state
        $user = auth()->user();
        if (! $user && request()->filled('state')) {
            try {
                $payload = decrypt(request()->input('state'));
                $user = User::find($payload['user_id'] ?? null);
            } catch (\Throwable) {
                // state inválido
            }
        }

        if (! $user) {
            throw ValidationException::withMessages(['state' => 'Sessão de autenticação inválida.']);
        }

        $integration = UserIntegration::firstOrNew([
            'user_id' => $user->id,
            'provider' => UserIntegration::PROVIDER_GOOGLE,
            'label' => 'default',
        ]);

        // Se o Google não enviou novo refresh_token, preserva o existente
        $existingRefreshToken = $integration->credential('refresh_token');

        $integration->fill([
            'status' => 'connected',
            'credentials' => [
                'access_token' => $accessToken,
                'refresh_token' => $refreshToken ?: $existingRefreshToken,
                'token_type' => $tokenData['token_type'] ?? 'Bearer',
            ],
            'meta' => [
                'email' => $email,
                'name' => $userInfo['name'] ?? null,
                'picture' => $userInfo['picture'] ?? null,
            ],
            'scopes' => explode(' ', $tokenData['scope'] ?? ''),
            'expires_at' => now()->addSeconds($expiresIn - 60),
            'last_error' => null,
        ])->save();

        return $integration;
    }

    /**
     * Obtém um access_token válido, renovando automaticamente caso tenha expirado.
     */
    public function getValidAccessToken(User $user): ?string
    {
        $integration = $user->integration(UserIntegration::PROVIDER_GOOGLE);
        if (! $integration) {
            return null;
        }

        $expiresAt = $integration->expires_at;
        $accessToken = $integration->credential('access_token');
        $refreshToken = $integration->credential('refresh_token');

        // Se o token ainda é válido com margem de segurança de 2 minutos
        if ($accessToken && $expiresAt && $expiresAt->isAfter(now()->addMinutes(2))) {
            return $accessToken;
        }

        // Se não tiver refresh_token, não é possível renovar
        if (! $refreshToken) {
            $integration->markError('Refresh token ausente. Reconecte a conta Google.', expired: true);
            return null;
        }

        // Renova o token via refresh_token
        $response = Http::asForm()->timeout(15)->post(self::OAUTH_TOKEN_URL, [
            'client_id' => config('services.google.client_id'),
            'client_secret' => config('services.google.client_secret'),
            'refresh_token' => $refreshToken,
            'grant_type' => 'refresh_token',
        ]);

        if (! $response->successful()) {
            $integration->markError('Falha ao renovar token do Google. Reconecte a conta.', expired: true);
            return null;
        }

        $data = $response->json();
        $newAccessToken = $data['access_token'];
        $expiresIn = $data['expires_in'] ?? 3600;

        $integration->mergeCredentials([
            'access_token' => $newAccessToken,
        ]);
        $integration->expires_at = now()->addSeconds($expiresIn - 60);
        $integration->status = 'connected';
        $integration->last_error = null;
        $integration->save();

        return $newAccessToken;
    }

    // --- Google Calendar API -------------------------------------------------

    /**
     * Lista eventos da agenda no intervalo especificado.
     *
     * @return array<int, array<string, mixed>>
     */
    public function listEvents(User $user, Carbon $from, Carbon $to, string $calendarId = 'primary'): array
    {
        $token = $this->getValidAccessToken($user);
        if (! $token) {
            return [];
        }

        $url = sprintf('%s/calendars/%s/events', self::CALENDAR_API_BASE, urlencode($calendarId));

        $response = Http::withToken($token)
            ->timeout(15)
            ->get($url, [
                'timeMin' => $from->toRfc3339String(),
                'timeMax' => $to->toRfc3339String(),
                'singleEvents' => 'true',
                'orderBy' => 'startTime',
                'maxResults' => 100,
            ]);

        if (! $response->successful()) {
            Log::warning('Erro ao listar eventos do Google Calendar', [
                'status' => $response->status(),
                'body' => $response->json(),
            ]);
            return [];
        }

        return $response->json('items', []);
    }

    /**
     * Cria um novo evento no Google Calendar.
     *
     * @param  array{title: string, description?: string, starts_at: Carbon, ends_at: Carbon, location?: string}  $data
     * @return array<string, mixed>
     */
    public function createEvent(User $user, array $data, string $calendarId = 'primary'): array
    {
        $token = $this->getValidAccessToken($user);
        if (! $token) {
            throw new \RuntimeException('Conta Google não conectada ou token expirado.');
        }

        $url = sprintf('%s/calendars/%s/events', self::CALENDAR_API_BASE, urlencode($calendarId));

        $payload = [
            'summary' => $data['title'],
            'description' => $data['description'] ?? null,
            'location' => $data['location'] ?? null,
            'start' => [
                'dateTime' => $data['starts_at']->toRfc3339String(),
            ],
            'end' => [
                'dateTime' => $data['ends_at']->toRfc3339String(),
            ],
        ];

        $response = Http::withToken($token)->timeout(15)->post($url, $payload);

        if (! $response->successful()) {
            throw new \RuntimeException('Falha ao criar evento no Google Calendar: ' . $response->body());
        }

        return $response->json();
    }

    // --- Google Tasks API ----------------------------------------------------

    /**
     * Cria uma nova tarefa no Google Tasks.
     */
    public function createTask(User $user, array $data, string $taskList = '@default'): array
    {
        $token = $this->getValidAccessToken($user);
        if (! $token) {
            throw new \RuntimeException('Conta Google não conectada ou token expirado.');
        }

        $url = sprintf('%s/lists/%s/tasks', self::TASKS_API_BASE, urlencode($taskList));

        $payload = [
            'title' => $data['title'],
            'notes' => $data['description'] ?? null,
            'due' => isset($data['due_at']) ? $data['due_at']->toRfc3339String() : null,
        ];

        $response = Http::withToken($token)->timeout(15)->post($url, array_filter($payload));

        if (! $response->successful()) {
            throw new \RuntimeException('Falha ao criar tarefa no Google Tasks: ' . $response->body());
        }

        return $response->json();
    }
}

