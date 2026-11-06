<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\AgentConversationResource;
use App\Http\Resources\AgentMessageResource;
use App\Models\AgentConversation;
use App\Models\Business;
use App\Services\GeminiAgentService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

class AgentConversationController extends Controller
{
    public function __construct(private readonly GeminiAgentService $agentService)
    {
    }

    public function index(Request $request): AnonymousResourceCollection
    {
        $request->validate([
            'business_id' => ['sometimes', 'integer'],
            'context_type' => ['sometimes', 'in:incubator,business_chat,autonomous_run'],
            'status' => ['sometimes', 'in:active,archived'],
            'per_page' => ['sometimes', 'integer', 'min:1', 'max:50'],
        ]);

        $conversations = $request->user()->agentConversations()
            ->when($request->filled('business_id'), fn ($q) => $q->where('business_id', $request->business_id))
            ->when($request->filled('context_type'), fn ($q) => $q->where('context_type', $request->context_type))
            ->when($request->filled('status'), fn ($q) => $q->where('status', $request->status))
            ->with('business:id,name,type')
            ->orderByDesc('last_message_at')
            ->orderByDesc('id')
            ->paginate($request->integer('per_page', 20));

        return AgentConversationResource::collection($conversations);
    }

    public function store(Request $request): JsonResponse
    {
        $request->validate([
            'business_id' => ['nullable', 'integer'],
            'title' => ['nullable', 'string', 'max:160'],
            'context_type' => ['sometimes', 'in:incubator,business_chat,autonomous_run'],
        ]);

        $business = null;
        if ($request->filled('business_id')) {
            $business = Business::where('user_id', $request->user()->id)->findOrFail($request->business_id);
        }

        $contextType = $request->input('context_type', $business ? 'business_chat' : 'incubator');
        $title = $request->input('title') ?: ($business ? "Operação: {$business->name}" : "Nova Sessão com COO");

        $conversation = $request->user()->agentConversations()->create([
            'business_id' => $business?->id,
            'title' => $title,
            'context_type' => $contextType,
            'status' => 'active',
        ]);

        return (new AgentConversationResource($conversation->load('business:id,name,type')))
            ->response()
            ->setStatusCode(201);
    }

    public function show(Request $request, string $uuid): AgentConversationResource
    {
        $conversation = AgentConversation::where('user_id', $request->user()->id)
            ->where('uuid', $uuid)
            ->with(['business:id,name,type', 'messages'])
            ->firstOrFail();

        return new AgentConversationResource($conversation);
    }

    public function sendMessage(Request $request, string $uuid): JsonResponse
    {
        $request->validate([
            'message' => ['required', 'string', 'min:1', 'max:25000'],
        ]);

        $conversation = AgentConversation::where('user_id', $request->user()->id)
            ->where('uuid', $uuid)
            ->with('business')
            ->firstOrFail();

        // Armazena a contagem atual de mensagens para retornar as novas mensagens geradas nesta iteração
        $beforeId = (int) $conversation->messages()->max('id');

        $finalReply = $this->agentService->replyToUser(
            $conversation,
            $request->input('message')
        );

        $newMessages = $conversation->messages()
            ->where('id', '>', $beforeId)
            ->orderBy('id')
            ->get();

        return response()->json([
            'data' => new AgentMessageResource($finalReply),
            'conversation' => new AgentConversationResource($conversation->refresh()->load('business:id,name,type')),
            'new_messages' => AgentMessageResource::collection($newMessages),
        ]);
    }
}

