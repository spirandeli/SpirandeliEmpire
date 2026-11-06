<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\ApprovalQueue;
use App\Models\Business;
use App\Models\Task;
use App\Models\UserIntegration;
use App\Services\ApprovalService;
use App\Services\TaskService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class AppleShortcutsController extends Controller
{
    public function __construct(
        private readonly TaskService $taskService,
        private readonly ApprovalService $approvalService,
    ) {
    }

    /**
     * Endpoint unificado para requisições do Apple Shortcuts (iOS / macOS).
     * Autenticação via header `X-ABVOS-Token` ou query `token`.
     */
    public function handle(Request $request): JsonResponse
    {
        $token = $request->header('X-ABVOS-Token') ?: $request->input('token');

        if (! $token) {
            return response()->json(['error' => 'Token do webhook ausente (use o header X-ABVOS-Token ou ?token=).'], 401);
        }

        $integration = UserIntegration::findByWebhookToken($token);
        if (! $integration) {
            return response()->json(['error' => 'Token do webhook inválido ou revogado.'], 403);
        }

        $user = $integration->user;
        $integration->forceFill(['last_used_at' => now()])->save();

        $action = $request->input('action', 'daily_briefing');

        return match ($action) {
            'capture_task' => $this->captureTask($request, $user),
            'daily_briefing' => $this->dailyBriefing($user),
            'approve_item' => $this->approveItem($request, $user),
            'list_pending_approvals' => $this->listPendingApprovals($user),
            default => response()->json(['error' => "Ação desconhecida: {$action}."], 400),
        };
    }

    private function captureTask(Request $request, $user): JsonResponse
    {
        $title = $request->input('title');
        if (empty($title)) {
            return response()->json(['error' => 'O título da tarefa é obrigatório.'], 422);
        }

        $businessId = $request->input('business_id');
        $business = $businessId
            ? Business::where('user_id', $user->id)->find($businessId)
            : $user->businesses()->first();

        if (! $business) {
            return response()->json(['error' => 'Nenhum negócio cadastrado para associar a tarefa.'], 422);
        }

        $assignee = $request->input('assignee', 'user');

        $task = $this->taskService->create($business, [
            'title' => $title,
            'description' => $request->input('description', 'Criada via Atalhos do iPhone / Siri.'),
            'assignee' => $assignee,
            'priority' => $request->input('priority', 'medium'),
            'due_at' => $request->filled('due_at') ? now()->parse($request->input('due_at')) : null,
        ], source: 'user');

        return response()->json([
            'success' => true,
            'message' => "Tarefa #{$task->id} criada para {$business->name}.",
            'task' => [
                'id' => $task->id,
                'title' => $task->title,
                'assignee' => $task->assignee->value,
                'status' => $task->status->value,
            ],
        ], 201);
    }

    private function dailyBriefing($user): JsonResponse
    {
        $pendingApprovals = ApprovalQueue::query()
            ->where('user_id', $user->id)
            ->awaitingReview()
            ->with('business:id,name')
            ->get();

        $openTasks = Task::query()
            ->where('user_id', $user->id)
            ->where('status', 'todo_user')
            ->orderBy('priority')
            ->limit(5)
            ->get();

        $summaryText = sprintf(
            "Olá %s! Você tem %d entrega(s) aguardando sua revisão na Inbox de Supervisão e %d tarefa(s) pendentes para você hoje.",
            $user->name,
            $pendingApprovals->count(),
            $openTasks->count()
        );

        return response()->json([
            'spoken_text' => $summaryText,
            'pending_approvals_count' => $pendingApprovals->count(),
            'pending_approvals' => $pendingApprovals->map(fn ($a) => [
                'id' => $a->id,
                'title' => $a->title,
                'business' => $a->business?->name,
                'type' => $a->type,
            ]),
            'tasks_to_do' => $openTasks->map(fn ($t) => [
                'id' => $t->id,
                'title' => $t->title,
                'priority' => $t->priority,
            ]),
        ]);
    }

    private function approveItem(Request $request, $user): JsonResponse
    {
        $approvalId = $request->input('approval_id');

        $approval = $approvalId
            ? ApprovalQueue::where('user_id', $user->id)->find($approvalId)
            : ApprovalQueue::where('user_id', $user->id)->awaitingReview()->oldest('id')->first();

        if (! $approval) {
            return response()->json(['error' => 'Nenhum item pendente para aprovação.'], 404);
        }

        $approved = $this->approvalService->approve($approval);

        return response()->json([
            'success' => true,
            'message' => "Entrega #{$approved->id} (\"{$approved->title}\") aprovada com sucesso!",
            'approval_id' => $approved->id,
            'status' => $approved->status->value,
        ]);
    }

    private function listPendingApprovals($user): JsonResponse
    {
        $items = ApprovalQueue::where('user_id', $user->id)
            ->awaitingReview()
            ->with('business:id,name')
            ->limit(10)
            ->get();

        return response()->json([
            'items' => $items->map(fn ($i) => [
                'id' => $i->id,
                'title' => $i->title,
                'business' => $i->business?->name,
            ]),
        ]);
    }
}

