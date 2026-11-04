<?php

namespace App\Http\Controllers\Api;

use App\Models\Conversation;
use App\Models\Message;
use App\Services\JeffreyOrchestratorService;
use App\Services\ToolRegistryService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;

class ChatController extends Controller
{
    /**
     * List all persistent conversations ordered by last update.
     */
    public function listConversations(Request $request): JsonResponse
    {
        $conversations = Conversation::with(['latestMessage', 'business:id,name,slug', 'project:id,name,slug'])
            ->withCount('messages')
            ->orderBy('updated_at', 'desc')
            ->get();

        return response()->json([
            'success' => true,
            'conversations' => $conversations,
        ]);
    }

    /**
     * Create a new conversation thread.
     */
    public function createConversation(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'title' => 'nullable|string|max:100',
            'business_id' => 'nullable|integer|exists:businesses,id',
            'project_id' => 'nullable|integer|exists:projects,id',
        ]);

        $conversation = Conversation::create([
            'user_id' => $request->user()?->id,
            'title' => $validated['title'] ?? 'Nova Conversa',
            'business_id' => $validated['business_id'] ?? null,
            'project_id' => $validated['project_id'] ?? null,
        ]);

        // Automatically send initial greeting from Jeffrey
        Message::create([
            'conversation_id' => $conversation->id,
            'role' => 'assistant',
            'content' => "Saudações, Comandante. Eu sou Jeffrey, orquestrador central do SpirandeliEmpire OS.\n\nLinha de comando ativa e persistente. Em que projeto, negócio ou tarefa estratégica trabalharemos agora?",
            'provider' => 'system',
            'model' => 'jeffrey-core',
        ]);

        return response()->json([
            'success' => true,
            'conversation' => $conversation->load('messages'),
        ], 201);
    }

    /**
     * Get a specific conversation with all its messages.
     */
    public function getConversation(int $id): JsonResponse
    {
        $conversation = Conversation::with(['messages', 'business', 'project'])->findOrFail($id);

        return response()->json([
            'success' => true,
            'conversation' => $conversation,
        ]);
    }

    /**
     * Rename or update conversation.
     */
    public function updateConversation(Request $request, int $id): JsonResponse
    {
        $conversation = Conversation::findOrFail($id);

        $validated = $request->validate([
            'title' => 'nullable|string|max:100',
            'is_pinned' => 'nullable|boolean',
            'business_id' => 'nullable|integer|exists:businesses,id',
            'project_id' => 'nullable|integer|exists:projects,id',
        ]);

        $conversation->update($validated);

        return response()->json([
            'success' => true,
            'conversation' => $conversation,
        ]);
    }

    /**
     * Delete conversation with all messages.
     */
    public function deleteConversation(int $id): JsonResponse
    {
        $conversation = Conversation::findOrFail($id);
        $conversation->delete();

        return response()->json([
            'success' => true,
            'message' => 'Conversa excluída com sucesso.',
        ]);
    }

    /**
     * Send message into conversation and receive Jeffrey's real response with tool calling.
     */
    public function sendMessage(
        Request $request,
        int $id,
        JeffreyOrchestratorService $orchestrator
    ): JsonResponse {
        $conversation = Conversation::findOrFail($id);

        $request->validate([
            'message' => 'required|string',
            'provider' => 'nullable|string|in:hybrid,gemini,openai,ollama,llama',
        ]);

        $userMessage = $request->input('message');
        $provider = $request->input('provider');
        $userId = $request->user()?->id;

        $assistantMessage = $orchestrator->talkInConversation(
            $conversation,
            $userMessage,
            $provider,
            $userId
        );

        $conversation->touch(); // Update conversation timestamp

        return response()->json([
            'success' => true,
            'message' => $assistantMessage,
        ]);
    }

    /**
     * Get list of all tools in the system.
     */
    public function listTools(ToolRegistryService $tools): JsonResponse
    {
        return response()->json([
            'success' => true,
            'tools' => $tools->getAvailableTools(),
        ]);
    }

    /**
     * Execute a tool directly if authorized.
     */
    public function executeToolDirectly(Request $request, ToolRegistryService $tools): JsonResponse
    {
        $request->validate([
            'tool_name' => 'required|string',
            'arguments' => 'nullable|array',
        ]);

        $result = $tools->executeTool(
            $request->input('tool_name'),
            $request->input('arguments', []),
            $request->user()?->id
        );

        return response()->json($result);
    }
}
