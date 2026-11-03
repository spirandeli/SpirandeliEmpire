<?php

namespace App\Http\Controllers\Api;

use App\Services\AiGatewayService;
use App\Services\TokenBudgetManagerService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;

class AiEngineController extends Controller
{
    /**
     * Get consolidated status of all AI engines and token governance.
     */
    public function status(AiGatewayService $aiGateway): JsonResponse
    {
        $status = $aiGateway->getProvidersStatus();

        return response()->json(array_merge($status, [
            'tts_engine' => 'Piper (Local CPU pt_BR-faber-medium)',
            'video_engine' => 'FFmpeg',
            'gpu_mode' => env('GPU_EXECUTION_MODE', 'cpu_only'),
            'gpu_remote_enabled' => (bool) env('GPU_REMOTE_ENABLED', false),
        ]));
    }

    /**
     * Test connection to a specific provider (gemini, openai, ollama).
     */
    public function testProvider(Request $request, AiGatewayService $aiGateway): JsonResponse
    {
        $request->validate([
            'provider' => 'required|string|in:gemini,google,openai,ollama,llama',
        ]);

        $result = $aiGateway->testProvider($request->input('provider'));

        return response()->json($result);
    }

    /**
     * Direct test completion across any provider with token measurement.
     */
    public function complete(Request $request, AiGatewayService $aiGateway): JsonResponse
    {
        $request->validate([
            'prompt' => 'required|string',
            'provider' => 'nullable|string|in:hybrid,gemini,openai,ollama,llama',
            'model' => 'nullable|string',
        ]);

        $result = $aiGateway->generate(
            $request->input('prompt'),
            'Você é um assistente de validação do SpirandeliEmpire OS. Responda de forma concisa.',
            $request->input('provider'),
            $request->input('model')
        );

        return response()->json($result);
    }

    /**
     * Estimate token size and calculate optimal task delegation.
     */
    public function estimateTokens(Request $request, TokenBudgetManagerService $tokenManager): JsonResponse
    {
        $request->validate([
            'text' => 'required|string',
            'preferred_provider' => 'nullable|string',
        ]);

        $text = $request->input('text');
        $estimatedTokens = $tokenManager->estimateTokens($text);
        $charLength = mb_strlen($text, 'UTF-8');
        $wordCount = count(preg_split('/\s+/u', trim($text), -1, PREG_SPLIT_NO_EMPTY));
        $delegation = $tokenManager->determineOptimalProvider($estimatedTokens, $request->input('preferred_provider'));

        return response()->json([
            'char_length' => $charLength,
            'word_count' => $wordCount,
            'estimated_tokens' => $estimatedTokens,
            'tier' => $delegation['tier'],
            'recommended_provider' => $delegation['provider'],
            'delegation_reason' => $delegation['reason'],
            'forced_delegation' => $delegation['forced_delegation'],
        ]);
    }
}
