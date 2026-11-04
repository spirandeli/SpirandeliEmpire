<?php

namespace App\Http\Controllers\Api;

use App\Models\ApprovalRequest;
use App\Models\Task;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\Redis;

class ApprovalController extends Controller
{
    public function index(): JsonResponse
    {
        return response()->json(ApprovalRequest::with('business')->latest()->get());
    }

    public function decide(Request $request, int $id): JsonResponse
    {
        $request->validate([
            'decision' => 'required|in:approved,rejected',
            'reason' => 'nullable|string',
        ]);

        $approval = ApprovalRequest::findOrFail($id);
        $approval->status = $request->input('decision');
        $approval->reviewed_by = 'Commander';
        $approval->reviewed_at = now();
        $approval->rejection_reason = $request->input('reason');
        $approval->save();

        // If approved and linked to a blocked background task, automatically re-enqueue it with human_approved=true
        if ($approval->status === 'approved') {
            $payload = is_array($approval->payload) ? $approval->payload : [];
            $taskId = $payload['task_id'] ?? null;
            if ($taskId) {
                $task = Task::find($taskId);
                if ($task) {
                    $taskPayload = array_merge($task->payload ?? [], [
                        'task_id' => $task->id,
                        'prompt' => $task->payload['prompt'] ?? $task->title,
                        'human_approved' => true,
                    ]);
                    $task->status = 'pending';
                    $task->error_message = null;
                    $task->payload = $taskPayload;
                    $task->save();

                    try {
                        Redis::lpush('empire:jeffrey:tasks', json_encode([
                            'id' => (string) $task->id,
                            'title' => $task->title,
                            'type' => $task->type,
                            'agent_name' => $task->agent_name,
                            'business_id' => $task->business_id,
                            'payload' => $taskPayload,
                            'created_at' => now()->toIso8601String(),
                        ]));
                    } catch (\Exception $e) {
                        // Worker auto-recovery will also pick it up from PostgreSQL
                    }
                }
            }
        }

        return response()->json($approval);
    }
}

