<?php

namespace App\Models;

use Cron\CronExpression;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Carbon;

class BusinessAutomation extends Model
{
    public const TYPE_TIKTOK_MINING = 'tiktok_product_mining';
    public const TYPE_CONTENT_GENERATION = 'affiliate_content_generation';
    public const TYPE_CALENDAR_SYNC = 'calendar_sync';
    public const TYPE_PERFORMANCE_REVIEW = 'performance_review';

    protected $fillable = [
        'business_id', 'type', 'name', 'cron_expression', 'timezone', 'is_enabled', 'config',
        'last_run_at', 'next_run_at', 'last_status', 'last_error', 'run_count', 'failure_count',
    ];

    protected function casts(): array
    {
        return [
            'is_enabled' => 'boolean',
            'config' => 'array',
            'last_run_at' => 'datetime',
            'next_run_at' => 'datetime',
            'run_count' => 'integer',
            'failure_count' => 'integer',
        ];
    }

    protected static function booted(): void
    {
        static::saving(function (BusinessAutomation $automation) {
            if ($automation->is_enabled && ($automation->isDirty('cron_expression') || $automation->next_run_at === null)) {
                $automation->next_run_at = $automation->computeNextRun();
            }
        });
    }

    public function business(): BelongsTo
    {
        return $this->belongsTo(Business::class);
    }

    public function logs(): HasMany
    {
        return $this->hasMany(AgentLog::class);
    }

    /** Automações habilitadas cujo horário já chegou (consumidas pelo Scheduler). */
    public function scopeDue(Builder $query): Builder
    {
        return $query->where('is_enabled', true)
            ->where(fn (Builder $q) => $q->whereNull('next_run_at')->orWhere('next_run_at', '<=', now()))
            ->where(fn (Builder $q) => $q->whereNull('last_status')->orWhere('last_status', '!=', 'running'));
    }

    public function scopeOfType(Builder $query, string $type): Builder
    {
        return $query->where('type', $type);
    }

    public function computeNextRun(?Carbon $from = null): ?Carbon
    {
        if (! CronExpression::isValidExpression($this->cron_expression)) {
            return null;
        }

        $from = ($from ?? now())->copy()->setTimezone($this->timezone ?: config('app.timezone'));
        $next = (new CronExpression($this->cron_expression))->getNextRunDate($from->toDateTime());

        return Carbon::instance($next)->setTimezone(config('app.timezone'));
    }

    public function markRunning(): void
    {
        $this->forceFill(['last_status' => 'running', 'last_error' => null])->save();
    }

    public function markSuccess(): void
    {
        $this->forceFill([
            'last_status' => 'success',
            'last_error' => null,
            'last_run_at' => now(),
            'next_run_at' => $this->computeNextRun(),
            'run_count' => $this->run_count + 1,
        ])->save();
    }

    public function markFailed(string $error): void
    {
        $this->forceFill([
            'last_status' => 'failed',
            'last_error' => mb_substr($error, 0, 2000),
            'last_run_at' => now(),
            'next_run_at' => $this->computeNextRun(),
            'failure_count' => $this->failure_count + 1,
        ])->save();
    }
}
