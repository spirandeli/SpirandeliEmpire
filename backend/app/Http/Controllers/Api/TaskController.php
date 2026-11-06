<?php

namespace App\Http\Controllers\Api;

use App\Enums\TaskStatus;
use App\Http\Controllers\Controller;
use App\Http\Requests\Task\MoveTaskRequest;
use App\Http\Requests\Task\StoreTaskRequest;
use App\Http\Requests\Task\UpdateTaskRequest;
use App\Http\Resources\TaskResource;
use App\Models\Business;
use App\Models\Task;
use App\Services\TaskService;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

class TaskController extends Controller
{
    private const DONE_LIMIT = 50;

    public function __construct(private readonly TaskService $tasks)
    {
    }

    /** Lista com filtros (modo "Lista" do TasksBoardView). */
    public function index(Request $request): AnonymousResourceCollection
    {
        $tasks = $this->filtered($request)
            ->with('business:id,name')
            ->orderBy('position')->orderByDesc('id')
            ->paginate($request->integer('per_page', 50));

        return TaskResource::collection($tasks);
    }

    /** Quadro Kanban: as 5 colunas, "Concluído" limitado às últimas entregas. */
    public function board(Request $request): JsonResponse
    {
        $open = $this->filtered($request)
            ->where('status', '!=', TaskStatus::Done->value)
            ->with('business:id,name')
            ->orderBy('position')->orderBy('id')
            ->get();

        $done = $this->filtered($request)
            ->where('status', TaskStatus::Done->value)
            ->with('business:id,name')
            ->latest('completed_at')
            ->limit(self::DONE_LIMIT)
            ->get();

        $all = $open->concat($done);

        $columns = collect(TaskStatus::cases())->map(fn (TaskStatus $status) => [
            'status' => $status->value,
            'label' => $status->label(),
            'count' => $all->filter(fn (Task $t) => $t->status === $status)->count(),
            'tasks' => TaskResource::collection($all->filter(fn (Task $t) => $t->status === $status)->values()),
        ]);

        return response()->json(['data' => $columns->values()]);
    }

    public function store(StoreTaskRequest $request): JsonResponse
    {
        $business = Business::findOrFail($request->integer('business_id'));
        $this->owned($business, $request);

        $task = $this->tasks->create($business, $request->safe()->except('business_id'));

        return (new TaskResource($task->load('business:id,name')))->response()->setStatusCode(201);
    }

    public function show(Request $request, Task $task): TaskResource
    {
        $this->owned($task, $request);

        return new TaskResource($task->load('business:id,name'));
    }

    public function update(UpdateTaskRequest $request, Task $task): TaskResource
    {
        $this->owned($task, $request);

        return new TaskResource($this->tasks->update($task, $request->validated())->load('business:id,name'));
    }

    public function move(MoveTaskRequest $request, Task $task): TaskResource
    {
        $this->owned($task, $request);

        $moved = $this->tasks->move(
            $task,
            TaskStatus::from($request->validated('status')),
            $request->validated('position'),
        );

        return new TaskResource($moved->load('business:id,name'));
    }

    public function destroy(Request $request, Task $task): JsonResponse
    {
        $this->owned($task, $request);

        $task->delete();

        return response()->json(null, 204);
    }

    private function filtered(Request $request): Builder
    {
        $request->validate([
            'business_id' => ['sometimes', 'integer'],
            'assignee' => ['sometimes', 'in:agent,user'],
            'status' => ['sometimes', 'in:backlog,in_progress_agent,awaiting_supervision,todo_user,done'],
            'priority' => ['sometimes', 'in:low,medium,high,urgent'],
            'search' => ['sometimes', 'string', 'max:120'],
            'per_page' => ['sometimes', 'integer', 'min:1', 'max:200'],
        ]);

        return Task::query()
            ->where('user_id', $request->user()->id)
            ->when($request->filled('business_id'), fn (Builder $q) => $q->where('business_id', $request->business_id))
            ->when($request->filled('assignee'), fn (Builder $q) => $q->where('assignee', $request->assignee))
            ->when($request->filled('status'), fn (Builder $q) => $q->where('status', $request->status))
            ->when($request->filled('priority'), fn (Builder $q) => $q->where('priority', $request->priority))
            ->when($request->filled('search'), fn (Builder $q) => $q->where('title', 'like', '%'.$request->search.'%'));
    }
}

