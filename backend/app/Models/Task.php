<?php

namespace App\Models;

use App\Enums\TaskAssignee;
use App\Enums\TaskStatus;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class Task extends Model
{
    use HasFactory, SoftDeletes;

    protected $fillable = [
        'business_id', 'user_id', 'parent_id', 'title', 'description', 'assignee', 'status',
        'priority', 'source', 'position', 'due_at', 'scheduled_at', 'started_at', 'completed_at',
        'agent_action', 'payload', 'result', 'failure_reason', 'attempts',
        'external_calendar_provider', 'external_calendar_id',
    ];

    protected function casts(): array
    {
        return [
            'assignee' => TaskAssignee::class,
            'status' => TaskStatus::class,
            'payload' => 'array',
            'result' => 'array',
            'due_at' => 'datetime',
            'scheduled_at' => 'datetime',
            'started_at' => 'datetime',
            'completed_at' => 'datetime',
            'position' => 'integer',
            'attempts' => 'integer',
        ];
    }

    protected static function booted(): void
    {
        // Timestamps coerentes com o Kanban: concluir/reabrir e iniciar execução do worker.
        static::saving(function (Task $task) {
            if ($task->isDirty('status')) {
                if ($task->status === TaskStatus::Done) {
                    $task->completed_at ??= now();
                } else {
                    $task->completed_at = null;
                }

                if ($task->status === TaskStatus::InProgressAgent) {
                    $task->started_at ??= now();
                }
            }
        });
    }

    // --- Relacionamentos -------------------------------------------------------

    public function business(): BelongsTo
    {
        return $this->belongsTo(Business::class);
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function parent(): BelongsTo
    {
        return $this->belongsTo(self::class, 'parent_id');
    }

    public function subtasks(): HasMany
    {
        return $this->hasMany(self::class, 'parent_id');
    }

    public function approvalQueues(): HasMany
    {
        return $this->hasMany(ApprovalQueue::class);
    }

    public function logs(): HasMany
    {
        return $this->hasMany(AgentLog::class);
    }

    public function calendarEvents(): HasMany
    {
        return $this->hasMany(CalendarEvent::class);
    }

    // --- Scopes ------------------------------------------------------------------

    public function scopeAssignedToAgent(Builder $query): Builder
    {
        return $query->where('assignee', TaskAssignee::Agent->value);
    }

    public function scopeAssignedToUser(Builder $query): Builder
    {
        return $query->where('assignee', TaskAssignee::User->value);
    }

    public function scopeOpen(Builder $query): Builder
    {
        return $query->where('status', '!=', TaskStatus::Done->value);
    }

    public function scopeWithStatus(Builder $query, TaskStatus $status): Builder
    {
        return $query->where('status', $status->value);
    }

    /** Fila de trabalho do agente: tarefas do agente no backlog prontas para execução. */
    public function scopeRunnableByAgent(Builder $query): Builder
    {
        return $query->assignedToAgent()
            ->where('status', TaskStatus::Backlog->value)
            ->where(fn (Builder $q) => $q->whereNull('scheduled_at')->orWhere('scheduled_at', '<=', now()));
    }

    // --- Transições ----------------------------------------------------------------

    public function moveTo(TaskStatus $status): self
    {
        $this->status = $status;
        $this->save();

        return $this;
    }

    public function markFailed(string $reason): self
    {
        $this->forceFill([
            'status' => TaskStatus::Backlog,
            'failure_reason' => mb_substr($reason, 0, 2000),
            'attempts' => $this->attempts + 1,
        ])->save();

        return $this;
    }
}
