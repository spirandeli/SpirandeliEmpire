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
            $queueLength = (int) Redis::llen('empire:jeffrey:tasks');
            $rawState = Redis::get('empire:jeffrey:worker_state');
            if ($rawState) {
                $workerState = json_decode($rawState, true);
            }
        } catch (\Exception $e) {
            // Redis fallback
        }

        if (!$workerState) {
            $running = $activeTasks->firstWhere('status', 'in_progress');
            if ($running) {
                $workerState = [
                    'status' => 'working',
                    'task_id' => $running->id,
                    'title' => $running->title,
                    'agent_name' => $running->agent_name,
                    'step' => 'Executando inferência e processamento em background...',
                    'progress_percent' => 55,
                    'started_at' => optional($running->started_at)->toIso8601String(),
                ];
            } elseif ($counts['pending'] > 0) {
                $next = $activeTasks->first();
                $workerState = [
                    'status' => 'queued',
                    'task_id' => $next?->id,
                    'title' => $next?->title,
                    'agent_name' => $next?->agent_name ?? 'Jeffrey',
                    'step' => 'Na fila aguardando worker iniciar processamento...',
                    'progress_percent' => 15,
                ];
            } else {
                $workerState = [
                    'status' => 'idle',
                    'step' => 'Ocioso — Aguardando novas ordens ou tarefas assíncronas.',
                    'progress_percent' => 0,
                ];
            }
        }

        return response()->json([
            'success' => true,
            'is_working' => ($counts['in_progress'] > 0 || $counts['pending'] > 0 || ($workerState['status'] ?? '') === 'working'),
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
