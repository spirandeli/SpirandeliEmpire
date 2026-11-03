<?php

namespace App\Http\Controllers\Api;

use App\Models\ApprovalRequest;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;

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

        return response()->json($approval);
    }
}

