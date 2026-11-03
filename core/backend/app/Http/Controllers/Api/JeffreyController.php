<?php

namespace App\Http\Controllers\Api;

use App\Models\AgentDecision;
use App\Models\ApprovalRequest;
use App\Models\JeffreyMemory;
use App\Services\JeffreyOrchestratorService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;

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

    public function getDecisions(): JsonResponse
    {
        return response()->json(AgentDecision::latest()->limit(50)->get());
    }

    public function getPendingApprovals(): JsonResponse
    {
        return response()->json(ApprovalRequest::where('status', 'pending')->get());
    }
}
