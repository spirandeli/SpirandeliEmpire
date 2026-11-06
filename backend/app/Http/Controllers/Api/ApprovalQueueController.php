<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\Approval\ApproveApprovalRequest;
use App\Http\Requests\Approval\RejectApprovalRequest;
use App\Http\Requests\Approval\RevisionApprovalRequest;
use App\Http\Resources\ApprovalQueueResource;
use App\Models\ApprovalQueue;
use App\Services\ApprovalService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;
use Illuminate\Support\Carbon;

/** Inbox de Supervisão (Human-in-the-Loop). */
class ApprovalQueueController extends Controller
{
    public function __construct(private readonly ApprovalService $approvals)
    {
    }

    /** Por padrão lista só o que aguarda decisão (`pending` + `revision_requested`). */
    public function index(Request $request): AnonymousResourceCollection
    {
        $request->validate([
            'status' => ['sometimes', 'in:pending,revision_requested,revising,approved,scheduled,rejected,expired,awaiting'],
            'business_id' => ['sometimes', 'integer'],
            'type' => ['sometimes', 'string', 'max:48'],
            'per_page' => ['sometimes', 'integer', 'min:1', 'max:100'],
        ]);

        $status = $request->input('status', 'awaiting');

        $items = ApprovalQueue::query()
            ->where('user_id', $request->user()->id)
            ->when($status === 'awaiting', fn ($q) => $q->awaitingReview(), fn ($q) => $q->where('status', $status))
            ->when($request->filled('business_id'), fn ($q) => $q->where('business_id', $request->business_id))
            ->when($request->filled('type'), fn ($q) => $q->where('type', $request->type))
            ->with('business:id,name')
            ->orderByRaw("CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END")
            ->latest('id')
            ->paginate($request->integer('per_page', 20));

        return ApprovalQueueResource::collection($items);
    }

    /** Contadores para o badge do menu / Dashboard. */
    public function summary(Request $request): JsonResponse
    {
        return response()->json(['data' => $this->approvals->summaryFor($request->user()->id)]);
    }

    public function show(Request $request, ApprovalQueue $approval): ApprovalQueueResource
    {
        $this->owned($approval, $request);

        return new ApprovalQueueResource($approval->load('business:id,name'));
    }

    public function approve(ApproveApprovalRequest $request, ApprovalQueue $approval): ApprovalQueueResource
    {
        $this->owned($approval, $request);

        $scheduledFor = $request->filled('scheduled_for') ? Carbon::parse($request->input('scheduled_for')) : null;

        return new ApprovalQueueResource(
            $this->approvals->approve($approval, $scheduledFor, $request->input('selected_hook_index'))
        );
    }

    public function revision(RevisionApprovalRequest $request, ApprovalQueue $approval): ApprovalQueueResource
    {
        $this->owned($approval, $request);

        return new ApprovalQueueResource(
            $this->approvals->requestRevision($approval, $request->validated('feedback'), $request->validated('section'))
        );
    }

    public function reject(RejectApprovalRequest $request, ApprovalQueue $approval): ApprovalQueueResource
    {
        $this->owned($approval, $request);

        return new ApprovalQueueResource(
            $this->approvals->reject($approval, $request->validated('reason'), $request->boolean('discard_product'))
        );
    }
}
