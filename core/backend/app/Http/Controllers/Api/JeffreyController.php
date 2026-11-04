<?php

namespace App\Http\Controllers\Api;

use App\Models\AgentDecision;
use App\Models\ApprovalRequest;
use App\Models\JeffreyMemory;
use App\Models\Task;
use App\Services\JeffreyOrchestratorService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\Redis;

class JeffreyController extends Controller
{
    public function chat(Request $request, JeffreyOrchestratorService $orchestrator): JsonResponse
    {
        $request->validate([
            'message' => 'required|string',
            'business_id' => 'nullable|integer',
            'provider' => 'nullable|string|in:hybrid,gemini,openai,ollama,llama',
        ]);

        $result = $orchestrator->talk(
            $request->input('message'),
            $request->input('business_id'),
            $request->input('provider')
        );

        return response()->json($result);
    }

    public function getMemories(): JsonResponse
    {
        return response()->json(JeffreyMemory::where('is_active', true)->get());
    }

    public function getDecisions(Request $request): JsonResponse
    {
        $perPage = min(100, max(10, (int) $request->input('per_page', 50)));
        return response()->json(AgentDecision::latest()->paginate($perPage));
    }

    public function getPendingApprovals(): JsonResponse
    {
        return response()->json(ApprovalRequest::where('status', 'pending')->get());
    }

    /**
     * Consolidated live telemetry of what Jeffrey and specialized agents are working on right now.
     */
    public function getActivity(): JsonResponse
    {
        $counts = [
            'total' => Task::count(),
            'pending' => Task::where('status', 'pending')->count(),
            'in_progress' => Task::where('status', 'in_progress')->count(),
            'completed' => Task::where('status', 'completed')->count(),
            'failed' => Task::where('status', 'failed')->count(),
            'cancelled' => Task::where('status', 'cancelled')->count(),
        ];

        $activeTasks = Task::with('business:id,name,slug')
            ->whereIn('status', ['in_progress', 'pending'])
            ->orderByRaw("CASE WHEN status = 'in_progress' THEN 0 ELSE 1 END")
            ->orderBy('created_at', 'asc')
            ->get();

        $recentTasks = Task::with('business:id,name,slug')
            ->latest()
            ->limit(25)
            ->get();

        $recentDecisions = AgentDecision::with('business:id,name,slug')
            ->latest()
            ->limit(20)
            ->get();

        $queueLength = 0;
        $workerState = null;

        try {
            // Migrate any tasks stuck in legacy prefixed Redis keys into the unified key
            foreach (['spirandeli_database_empire:jeffrey:tasks', 'laravel_database_empire:jeffrey:tasks'] as $legacyKey) {
                $legacyLen = (int) Redis::llen($legacyKey);
                while ($legacyLen > 0) {
                    $item = Redis::rpop($legacyKey);
                    if ($item) {
                        Redis::lpush('empire:jeffrey:tasks', $item);
                    }
                    $legacyLen--;
                }
            }

            // If there are pending tasks in PostgreSQL but Redis queue is empty, re-enqueue eligible ones automatically
            $currentQueueLen = (int) Redis::llen('empire:jeffrey:tasks');
            if ($counts['pending'] > 0 && $currentQueueLen === 0) {
                foreach ($activeTasks->where('status', 'pending') as $orphanTask) {
                    $depId = $orphanTask->payload['depends_on_task_id'] ?? null;
                    if ($depId) {
                        $parentTask = Task::find($depId);
                        if ($parentTask && in_array($parentTask->status, ['pending', 'in_progress'], true)) {
                            continue;
                        }
                    }
                    $queuePayload = json_encode([
                        'id' => (string) $orphanTask->id,
                        'title' => $orphanTask->title,
                        'type' => $orphanTask->type,
                        'agent_name' => $orphanTask->agent_name,
                        'business_id' => $orphanTask->business_id,
                        'payload' => array_merge($orphanTask->payload ?? [], [
                            'task_id' => $orphanTask->id,
                            'prompt' => $orphanTask->payload['prompt'] ?? $orphanTask->title,
                        ]),
                        'created_at' => optional($orphanTask->created_at)->toIso8601String() ?? now()->toIso8601String(),
                    ]);
                    Redis::lpush('empire:jeffrey:tasks', $queuePayload);
                }
            }

            $queueLength = (int) Redis::llen('empire:jeffrey:tasks');
            $rawState = Redis::get('empire:jeffrey:worker_state');
            if ($rawState) {
                $workerState = json_decode($rawState, true);
            }
        } catch (\Exception $e) {
            // Redis fallback
        }

        $running = $activeTasks->firstWhere('status', 'in_progress');
        $workerActivelyRunning = $running !== null || (($workerState['status'] ?? '') === 'working');

        if ($running && (($workerState['status'] ?? '') !== 'working')) {
            $workerState = [
                'status' => 'working',
                'task_id' => $running->id,
                'title' => $running->title,
                'agent_name' => $running->agent_name,
                'step' => 'Executando inferência e processamento em background...',
                'progress_percent' => 55,
                'started_at' => optional($running->started_at)->toIso8601String(),
            ];
        } elseif (!$running && $counts['pending'] > 0 && (($workerState['status'] ?? '') !== 'working')) {
            $next = $activeTasks->first();
            $workerState = [
                'status' => 'queued',
                'task_id' => $next?->id,
                'title' => $next?->title,
                'agent_name' => $next?->agent_name ?? 'Jeffrey',
                'step' => 'Na fila aguardando worker iniciar processamento...',
                'progress_percent' => 15,
            ];
        } elseif (!$workerState) {
            $workerState = [
                'status' => 'idle',
                'step' => 'Ocioso — Aguardando novas ordens ou tarefas assíncronas.',
                'progress_percent' => 0,
            ];
        }

        return response()->json([
            'success' => true,
            'is_working' => $workerActivelyRunning,
            'has_queued' => $counts['pending'] > 0,
            'queue_length' => $queueLength,
            'worker_state' => $workerState,
            'counts' => $counts,
            'active_tasks' => $activeTasks,
            'recent_tasks' => $recentTasks,
            'recent_decisions' => $recentDecisions,
            'timestamp' => now()->toIso8601String(),
        ]);
    }
}
