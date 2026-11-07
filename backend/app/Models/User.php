<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Notifications\Notifiable;
use Laravel\Sanctum\HasApiTokens;

class User extends Authenticatable
{
    use HasApiTokens, HasFactory, Notifiable;

    protected $fillable = [
        'name',
        'email',
        'password',
        'timezone',
        'locale',
        'agent_enabled',
        'is_admin',
        'is_ai_active',
        'monthly_token_limit',
        'tokens_used_this_month',
        'settings',
        'calendar_token',
        'last_login_at',
    ];

    protected $hidden = ['password', 'remember_token'];

    protected function casts(): array
    {
        return [
            'email_verified_at' => 'datetime',
            'last_login_at' => 'datetime',
            'password' => 'hashed',
            'agent_enabled' => 'boolean',
            'is_admin' => 'boolean',
            'is_ai_active' => 'boolean',
            'monthly_token_limit' => 'integer',
            'tokens_used_this_month' => 'integer',
            'settings' => 'array',
        ];
    }

    public function businesses(): HasMany
    {
        return $this->hasMany(Business::class);
    }

    public function tasks(): HasMany
    {
        return $this->hasMany(Task::class);
    }

    public function approvalQueues(): HasMany
    {
        return $this->hasMany(ApprovalQueue::class);
    }

    public function integrations(): HasMany
    {
        return $this->hasMany(UserIntegration::class);
    }

    public function calendarEvents(): HasMany
    {
        return $this->hasMany(CalendarEvent::class);
    }

    public function agentConversations(): HasMany
    {
        return $this->hasMany(AgentConversation::class);
    }

    public function agentLogs(): HasMany
    {
        return $this->hasMany(AgentLog::class);
    }

    public function aiUsageLogs(): HasMany
    {
        return $this->hasMany(AiUsageLog::class);
    }

    public function languageProfiles(): HasMany
    {
        return $this->hasMany(LanguageProfile::class);
    }

    public function activeLanguageProfile(): ?LanguageProfile
    {
        return $this->languageProfiles()
            ->where('is_active', true)
            ->latest('updated_at')
            ->first();
    }

    /**
     * Retorna ou gera um calendar_token único para assinatura do feed iCal RFC 5545.
     */
    public function getOrCreateCalendarToken(): string
    {
        if (empty($this->calendar_token)) {
            $this->calendar_token = \Illuminate\Support\Str::random(48);
            $this->saveQuietly();
        }

        return $this->calendar_token;
    }

    /**
     * Retorna a URL pública do feed iCalendar para o usuário.
     */
    public function calendarFeedUrl(): string
    {
        $token = $this->getOrCreateCalendarToken();
        return url("/api/v1/calendar/feed/{$token}.ics");
    }

    /** Integração conectada de um provider (ou null). */
    public function integration(string $provider, string $label = 'default'): ?UserIntegration
    {
        return $this->integrations()
            ->where('provider', $provider)
            ->where('label', $label)
            ->where('status', 'connected')
            ->first();
    }

    // --- Governança de IA & FinOps -----------------------------------------------

    public function isAdmin(): bool
    {
        return (bool) $this->is_admin;
    }

    public function isAiActive(): bool
    {
        return (bool) $this->is_ai_active;
    }

    /**
     * Verifica se o usuário atingiu o limite mensal de tokens contratado.
     */
    public function hasExceededMonthlyTokenLimit(): bool
    {
        if ($this->monthly_token_limit <= 0) {
            return false; // Sem limite rígido
        }

        return $this->tokens_used_this_month >= $this->monthly_token_limit;
    }

    /**
     * Registra o consumo de tokens de uma chamada à IA e atualiza o medidor mensal.
     */
    public function recordAiUsage(
        int $promptTokens,
        int $completionTokens,
        string $model,
        ?string $context = 'chat',
        ?int $businessId = null,
        ?int $conversationId = null,
        int $latencyMs = 0
    ): AiUsageLog {
        $totalTokens = $promptTokens + $completionTokens;
        $costUsd = AiUsageLog::calculateCostUsd($model, $promptTokens, $completionTokens);

        $log = $this->aiUsageLogs()->create([
            'business_id' => $businessId,
            'agent_conversation_id' => $conversationId,
            'model' => $model,
            'context' => $context ?? 'chat',
            'prompt_tokens' => $promptTokens,
            'completion_tokens' => $completionTokens,
            'total_tokens' => $totalTokens,
            'estimated_cost_usd' => $costUsd,
            'latency_ms' => $latencyMs,
        ]);

        $this->increment('tokens_used_this_month', $totalTokens);

        return $log;
    }
}
