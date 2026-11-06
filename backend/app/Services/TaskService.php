<?php

namespace App\Services;

use App\Enums\TaskAssignee;
use App\Enums\TaskStatus;
use App\Models\Business;
use App\Models\Task;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\ValidationException;

/**
 * Regras do Kanban híbrido (Agente IA x Humano).
 * Reutilizado pela tool `createTask` do Gemini (Fase 3) e pelos workers (Fase 5).
 */
class TaskService
{
    /** Colunas permitidas por executor. */
    private const ALLOWED = [
        'agent' => ['backlog', 'in_progress_agent', 'awaiting_supervision', 'done'],
        'user' => ['backlog', 'todo_user', 'done'],
    ];

    /**
     * @param  string  $source  'user' | 'agent'
     * @param  bool  $byWorker  true quando o próprio worker coloca a tarefa em execução
     */
    public function create(Business $business, array $data, string $source = 'user', bool $byWorker = false): Task
    {
        $assignee = TaskAssignee::from($data['assignee'] ?? TaskAssignee::User->value);
        $status = isset($data['status'])
            ? TaskStatus::from($data['status'])
            : ($assignee === TaskAssignee::Agent ? TaskStatus::Backlog : TaskStatus::TodoUser);

        $this->assertStatusAllowed($assignee, $status, $byWorker);

        return DB::transaction(function () use ($business, $data, $source, $assignee, $status) {
            return Task::create(array_merge($data, [
                'business_id' => $business->id,
                'user_id' => $business->user_id,
                'assignee' => $assignee,
                'status' => $status,
                'source' => $source,
                'position' => $data['position'] ?? $this->nextPosition($business->id, $status),
            ]));
        });
    }

    public function update(Task $task, array $data): Task
    {
        return DB::transaction(function () use ($task, $data) {
            $newAssignee = isset($data['assignee']) ? TaskAssignee::from($data['assignee']) : $task->assignee;

            // Troca de executor: reposiciona a tarefa numa coluna válida para o novo dono.
            if ($newAssignee !== $task->assignee) {
                $data['assignee'] = $newAssignee;
                if (! in_array($task->status->value, self::ALLOWED[$newAssignee->value], true)
                    || $task->status === TaskStatus::InProgressAgent) {
                    $target = $newAssignee === TaskAssignee::Agent ? TaskStatus::Backlog : TaskStatus::TodoUser;
                    $data['status'] = $target;
                    $data['position'] = $this->nextPosition($task->business_id, $target);
                }
            }

            $task->update($data);

            return $task->refresh();
        });
    }

    /**
     * Move a tarefa no Kanban (drag & drop) e reordena a coluna de destino.
     */
    public function move(Task $task, TaskStatus $status, ?int $position = null, bool $byWorker = false): Task
    {
        $this->assertStatusAllowed($task->assignee, $status, $byWorker);

        return DB::transaction(function () use ($task, $status, $position) {
            $position ??= $this->nextPosition($task->business_id, $status);

            Task::query()
                ->where('business_id', $task->business_id)
                ->where('status', $status->value)
                ->where('id', '!=', $task->id)
                ->where('position', '>=', $position)
                ->increment('position');

            $task->fill(['status' => $status, 'position' => $position])->save();

            return $task->refresh();
        });
    }

    private function assertStatusAllowed(TaskAssignee $assignee, TaskStatus $status, bool $byWorker): void
    {
        if ($status === TaskStatus::InProgressAgent && ! $byWorker) {
            throw ValidationException::withMessages([
                'status' => 'Somente o worker do agente pode colocar uma tarefa em execução.',
            ]);
        }

        if (! in_array($status->value, self::ALLOWED[$assignee->value], true)) {
            throw ValidationException::withMessages([
                'status' => "Tarefas do executor \"{$assignee->label()}\" não podem ficar em \"{$status->label()}\".",
            ]);
        }
    }

    private function nextPosition(int $businessId, TaskStatus $status): int
    {
        $max = Task::query()
            ->where('business_id', $businessId)
            ->where('status', $status->value)
            ->max('position');

        return $max === null ? 0 : ((int) $max) + 1;
    }
}

