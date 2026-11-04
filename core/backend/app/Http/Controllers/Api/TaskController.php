<?php

namespace App\Http\Controllers\Api;

use App\Models\Business;
use App\Models\Task;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\Redis;

class TaskController extends Controller
{
    /**
     * List tasks with filters and summary counts.
     */
    public function index(Request $request): JsonResponse
    {
        $status = $request->input('status');
        $businessId = $request->input('business_id');
        $agentName = $request->input('agent_name');

        $query = Task::with('business:id,name,slug')->latest();

        if ($status) {
            $query->where('status', $status);
        }
        if ($businessId) {
            $query->where('business_id', $businessId);
        }
        if ($agentName) {
            $query->where('agent_name', $agentName);
        }

        $tasks = $query->paginate(30);

        $counts = [
            'total' => Task::count(),
            'pending' => Task::where('status', 'pending')->count(),
            'in_progress' => Task::where('status', 'in_progress')->count(),
            'completed' => Task::where('status', 'completed')->count(),
            'failed' => Task::where('status', 'failed')->count(),
            'cancelled' => Task::where('status', 'cancelled')->count(),
        ];

        return response()->json([
            'success' => true,
            'counts' => $counts,
            'tasks' => $tasks,
        ]);
    }

    /**
     * Show single task details.
     */
    public function show(int $id): JsonResponse
    {
        $task = Task::with('business')->findOrFail($id);

        return response()->json([
            'success' => true,
            'task' => $task,
        ]);
    }

    /**
     * Create and enqueue a new task.
     */
    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'title' => 'required|string|max:255',
            'type' => 'required|string|max:100',
            'agent_name' => 'nullable|string|max:100',
            'business_id' => 'nullable|integer|exists:businesses,id',
            'payload' => 'nullable|array',
            'estimated_cost_brl' => 'nullable|numeric|min:0',
        ]);

        $task = Task::create([
            'title' => $validated['title'],
            'type' => $validated['type'],
            'agent_name' => $validated['agent_name'] ?? 'Jeffrey',
            'business_id' => $validated['business_id'] ?? null,
            'payload' => $validated['payload'] ?? [],
            'status' => 'pending',
            'estimated_cost_brl' => $validated['estimated_cost_brl'] ?? 0.00,
        ]);

        // Push task to Redis queue for background execution by jeffrey-worker
        try {
            $queuePayload = json_encode([
                'id' => (string) $task->id,
                'type' => $task->type,
                'agent_name' => $task->agent_name,
                'business_id' => $task->business_id,
                'payload' => array_merge($task->payload ?? [], [
                    'task_id' => $task->id,
                    'prompt' => $task->payload['prompt'] ?? $task->title,
                    'estimated_cost_brl' => $task->estimated_cost_brl,
                ]),
                'created_at' => now()->toIso8601String(),
            ]);

            Redis::lpush('empire:jeffrey:tasks', $queuePayload);
        } catch (\Exception $e) {
            // Log fallback if Redis is temporarily unreachable during sync write
            \Log::warning("Redis queue push deferred for task #{$task->id}: " . $e->getMessage());
        }

        return response()->json([
            'success' => true,
            'task' => $task,
            'message' => "Tarefa #{$task->id} enfileirada para execução assíncrona.",
        ], 201);
    }

    /**
     * Cancel task.
     */
    public function cancel(int $id): JsonResponse
    {
        $task = Task::findOrFail($id);

        if (in_array($task->status, ['completed', 'failed', 'cancelled'])) {
            return response()->json([
                'success' => false,
                'message' => "A tarefa #{$id} já foi finalizada com status '{$task->status}'.",
            ], 422);
        }

        $task->status = 'cancelled';
        $task->completed_at = now();
        $task->save();

        // Remove any pending entries for this task from the Redis queue
        $this->removeTaskFromRedisQueue($task->id);

        return response()->json([
            'success' => true,
            'task' => $task,
            'message' => "Tarefa #{$id} cancelada com sucesso.",
        ]);
    }

    /**
     * Retry failed or cancelled task.
     */
    public function retry(int $id): JsonResponse
    {
        $task = Task::findOrFail($id);
        $task->status = 'pending';
        $task->error_message = null;
        $task->started_at = null;
        $task->completed_at = null;
        $task->save();

        try {
            // Avoid duplicate queue entries for the same task ID
            $this->removeTaskFromRedisQueue($task->id);

            $queuePayload = json_encode([
                'id' => (string) $task->id,
                'type' => $task->type,
                'agent_name' => $task->agent_name,
                'business_id' => $task->business_id,
                'payload' => array_merge($task->payload ?? [], [
                    'task_id' => $task->id,
                    'prompt' => $task->payload['prompt'] ?? $task->title,
                ]),
                'retry' => true,
                'created_at' => now()->toIso8601String(),
            ]);

            Redis::lpush('empire:jeffrey:tasks', $queuePayload);
        } catch (\Exception $e) {
            \Log::warning("Redis retry deferred: " . $e->getMessage());
        }

        return response()->json([
            'success' => true,
            'task' => $task,
            'message' => "Tarefa #{$id} reenfileirada com sucesso.",
        ]);
    }

    /**
     * Remove duplicate/cancelled task entries from Redis queue.
     */
    protected function removeTaskFromRedisQueue(int $taskId): void
    {
        try {
            $items = Redis::lrange('empire:jeffrey:tasks', 0, -1);
            foreach ($items as $raw) {
                $decoded = json_decode($raw, true);
                if (isset($decoded['id']) && (int) $decoded['id'] === $taskId) {
                    Redis::lrem('empire:jeffrey:tasks', 0, $raw);
                }
            }
        } catch (\Exception $e) {
            // Ignore Redis errors on cleanup
        }
    }
}

