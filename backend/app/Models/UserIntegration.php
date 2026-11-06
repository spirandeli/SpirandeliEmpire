<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Str;

class UserIntegration extends Model
{
    public const PROVIDER_GEMINI = 'gemini';
    public const PROVIDER_GOOGLE = 'google';
    public const PROVIDER_APPLE_CALDAV = 'apple_caldav';
    public const PROVIDER_SHORTCUTS = 'shortcuts_webhook';
    public const PROVIDER_TIKTOK_SHOP = 'tiktok_shop';

    protected $fillable = [
        'user_id', 'provider', 'label', 'status', 'credentials', 'meta', 'scopes',
        'token_prefix', 'webhook_token_hash',
        'expires_at', 'last_synced_at', 'last_used_at', 'last_error',
    ];

    /** Credenciais e hash do token jamais saem em JSON/API. */
    protected $hidden = ['credentials', 'webhook_token_hash'];

    protected function casts(): array
    {
        return [
            // AES-256 via APP_KEY: chaves de API, tokens OAuth, senha de app CalDAV
            'credentials' => 'encrypted:array',
            'meta' => 'array',
            'scopes' => 'array',
            'expires_at' => 'datetime',
            'last_synced_at' => 'datetime',
            'last_used_at' => 'datetime',
        ];
    }

    protected $attributes = [
        'label' => 'default',
        'status' => 'connected',
    ];

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function calendarEvents(): HasMany
    {
        return $this->hasMany(CalendarEvent::class);
    }

    public function scopeProvider(Builder $query, string $provider): Builder
    {
        return $query->where('provider', $provider);
    }

    public function scopeConnected(Builder $query): Builder
    {
        return $query->where('status', 'connected');
    }

    public function isConnected(): bool
    {
        return $this->status === 'connected';
    }

    /** Lê uma credencial descriptografada (ex.: 'api_key', 'refresh_token'). */
    public function credential(string $key, mixed $default = null): mixed
    {
        return data_get($this->credentials ?? [], $key, $default);
    }

    /** Mescla credenciais preservando as existentes (ex.: renovação do access_token). */
    public function mergeCredentials(array $new): self
    {
        $this->credentials = array_merge($this->credentials ?? [], $new);

        return $this;
    }

    public function markError(string $message, bool $expired = false): void
    {
        $this->forceFill([
            'status' => $expired ? 'expired' : 'error',
            'last_error' => mb_substr($message, 0, 2000),
        ])->save();
    }

    public function markSynced(): void
    {
        $this->forceFill(['status' => 'connected', 'last_error' => null, 'last_synced_at' => now()])->save();
    }

    // --- Webhook Token (Apple Shortcuts) -----------------------------------------

    public static function hashToken(string $plain): string
    {
        return hash('sha256', $plain);
    }

    /**
     * Gera um token novo: o texto plano é retornado UMA vez (exibir ao usuário); só o hash é persistido.
     *
     * @return array{plain: string, hash: string, prefix: string}
     */
    public static function generateWebhookToken(): array
    {
        $plain = 'abvos_'.Str::random(48);

        return [
            'plain' => $plain,
            'hash' => self::hashToken($plain),
            'prefix' => substr($plain, 0, 10),
        ];
    }

    public static function findByWebhookToken(string $plain): ?self
    {
        return static::query()
            ->where('provider', self::PROVIDER_SHORTCUTS)
            ->where('status', 'connected')
            ->where('webhook_token_hash', self::hashToken($plain))
            ->first();
    }
}
