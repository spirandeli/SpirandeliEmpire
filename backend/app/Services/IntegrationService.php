<?php

namespace App\Services;

use App\Models\User;
use App\Models\UserIntegration;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Support\Facades\Http;
use Illuminate\Validation\ValidationException;

/**
 * Cofre de credenciais: tudo que é segredo vai em `credentials` (cast encrypted:array).
 * `meta` só guarda dados não sensíveis (dicas mascaradas, e-mail da conta, URLs).
 */
class IntegrationService
{
    public const APPLE_CALDAV_URL = 'https://caldav.icloud.com';

    // --- Gemini ----------------------------------------------------------------------

    public function saveGemini(User $user, string $apiKey, ?string $model = null, bool $validate = true): UserIntegration
    {
        if ($validate) {
            $this->assertGeminiKeyIsValid($apiKey);
        }

        return $this->upsert($user, UserIntegration::PROVIDER_GEMINI, [
            'credentials' => ['api_key' => $apiKey],
            'meta' => [
                'key_hint' => $this->mask($apiKey),
                'model' => $model ?: config('services.gemini.model'),
            ],
        ]);
    }

    /** Chave efetiva do usuário: cofre primeiro, fallback para a chave do sistema. */
    public function geminiApiKeyFor(User $user): ?string
    {
        return $user->integration(UserIntegration::PROVIDER_GEMINI)?->credential('api_key')
            ?: config('services.gemini.api_key');
    }

    public function geminiModelFor(User $user): string
    {
        return $user->integration(UserIntegration::PROVIDER_GEMINI)?->meta['model']
            ?? config('services.gemini.model');
    }

    private function assertGeminiKeyIsValid(string $apiKey): void
    {
        try {
            $response = Http::withHeaders(['x-goog-api-key' => $apiKey])
                ->timeout(15)
                ->get(rtrim(config('services.gemini.base_url'), '/').'/models', ['pageSize' => 1]);
        } catch (ConnectionException) {
            throw ValidationException::withMessages([
                'api_key' => 'Não foi possível contatar a API do Gemini para validar a chave. Tente novamente.',
            ]);
        }

        if (in_array($response->status(), [400, 401, 403], true)) {
            throw ValidationException::withMessages(['api_key' => 'A API Key do Gemini foi recusada. Verifique a chave.']);
        }

        if (! $response->successful()) {
            throw ValidationException::withMessages([
                'api_key' => "A API do Gemini respondeu {$response->status()} ao validar a chave. Tente novamente.",
            ]);
        }
    }

    // --- Apple CalDAV (iCloud) -------------------------------------------------------------

    public function saveAppleCaldav(User $user, string $appleId, string $appPassword, ?string $serverUrl = null): UserIntegration
    {
        return $this->upsert($user, UserIntegration::PROVIDER_APPLE_CALDAV, [
            'credentials' => ['apple_id' => $appleId, 'app_password' => $appPassword],
            'meta' => [
                'apple_id' => $appleId,
                'server_url' => $serverUrl ?: self::APPLE_CALDAV_URL,
                'key_hint' => $this->mask($appPassword),
                // Descoberta de calendários e verificação real: AppleCalDavService (Fase 4).
                'verified' => false,
            ],
        ]);
    }

    // --- Webhook Apple Shortcuts ---------------------------------------------------------------

    /**
     * Gera (ou rotaciona) o token. O texto plano é devolvido UMA vez; só o hash fica no banco.
     *
     * @return array{integration: UserIntegration, token: string}
     */
    public function generateShortcutsToken(User $user, ?string $label = null): array
    {
        $token = UserIntegration::generateWebhookToken();

        $integration = $this->upsert($user, UserIntegration::PROVIDER_SHORTCUTS, [
            'credentials' => null,
            'token_prefix' => $token['prefix'],
            'webhook_token_hash' => $token['hash'],
            'meta' => ['rotated_at' => now()->toIso8601String(), 'name' => $label ?: 'Atalhos (iPhone/Mac)'],
        ]);

        return ['integration' => $integration, 'token' => $token['plain']];
    }

    // --- Comum ---------------------------------------------------------------------------------------

    public function disconnect(UserIntegration $integration): void
    {
        // Eventos em cache perdem o vínculo (FK nullOnDelete); Google: revogação do token na Fase 4.
        $integration->delete();
    }

    private function upsert(User $user, string $provider, array $attributes): UserIntegration
    {
        $integration = UserIntegration::firstOrNew([
            'user_id' => $user->id,
            'provider' => $provider,
            'label' => 'default',
        ]);

        $integration->fill(array_merge([
            'status' => 'connected',
            'last_error' => null,
        ], $attributes))->save();

        return $integration;
    }

    private function mask(string $secret): string
    {
        $len = strlen($secret);

        return $len <= 8 ? str_repeat('•', $len) : substr($secret, 0, 4).str_repeat('•', 8).substr($secret, -4);
    }
}

