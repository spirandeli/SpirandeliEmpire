<?php

namespace App\Http\Controllers\Api;

use App\Models\Conversation;
use App\Models\Message;
use App\Services\JeffreyOrchestratorService;
use App\Services\ToolRegistryService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\File;
use Symfony\Component\HttpFoundation\Response;

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
            'content' => "Saudações, Comandante. Eu sou Jeffrey, orquestrador central do SpirandeliEmpire OS.\n\nLinha de comando ativa com suporte a **anexos (imagens, documentos, roteiros, planilhas)** e **mensagens de voz**. Em que projeto, negócio ou tarefa estratégica trabalharemos agora?",
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
     * Send message (with optional file/image attachments and voice recordings) into conversation.
     */
    public function sendMessage(
        Request $request,
        int $id,
        JeffreyOrchestratorService $orchestrator
    ): JsonResponse {
        $conversation = Conversation::findOrFail($id);

        $request->validate([
            'message' => 'nullable|string',
            'provider' => 'nullable|string|in:hybrid,gemini,openai,ollama,llama,cooperative',
            'attachments' => 'nullable|array|max:8',
        ]);

        $rawAttachments = $request->input('attachments', []);
        $userMessage = trim((string) $request->input('message', ''));

        if ($userMessage === '' && empty($rawAttachments)) {
            return response()->json([
                'success' => false,
                'message' => 'Envie uma mensagem de texto, áudio ou anexo.',
            ], 422);
        }

        // Persist attachments to storage/businesses/chat-attachments
        $attachDir = storage_path('businesses/chat-attachments');
        if (!File::isDirectory($attachDir)) {
            @File::makeDirectory($attachDir, 0775, true);
        }

        $processedAttachments = [];
        foreach ($rawAttachments as $att) {
            if (!is_array($att)) continue;
            $origName = preg_replace('/[^a-zA-Z0-9._\-]/', '_', (string) ($att['name'] ?? 'anexo.bin'));
            $mime = (string) ($att['mime_type'] ?? 'application/octet-stream');
            $b64 = (string) ($att['data_base64'] ?? '');
            $textContent = (string) ($att['text_content'] ?? '');
            $isVoice = !empty($att['is_voice']) || str_starts_with($mime, 'audio/');
            $isImage = str_starts_with($mime, 'image/');

            // Strip data URL prefix if present (e.g. "data:image/png;base64,...")
            if (str_contains($b64, ',')) {
                [, $b64] = explode(',', $b64, 2);
            }

            $storedFilename = time() . '_' . substr(md5($origName . microtime()), 0, 8) . '_' . $origName;
            $storedPath = $attachDir . DIRECTORY_SEPARATOR . $storedFilename;
            $decodedBytes = $b64 ? base64_decode($b64, true) : false;

            if ($decodedBytes !== false && strlen($decodedBytes) <= 15 * 1024 * 1024) {
                @File::put($storedPath, $decodedBytes);
                // If it's a readable text/code/CSV/MD/JSON file and text_content wasn't passed, extract up to 24KB
                if ($textContent === '' && preg_match('/(text\/|json|xml|csv|javascript|markdown|\.md$|\.txt$|\.csv$|\.py$|\.php$|\.js$|\.ts$|\.html$)/i', $mime . ' ' . $origName)) {
                    $textContent = mb_substr($decodedBytes, 0, 24000, 'UTF-8');
                }
            }

            $processedAttachments[] = [
                'name' => $origName,
                'filename' => $storedFilename,
                'url' => "/api/v1/chat/attachments/{$storedFilename}",
                'mime_type' => $mime,
                'size' => (int) ($att['size'] ?? ($decodedBytes ? strlen($decodedBytes) : 0)),
                'is_voice' => $isVoice,
                'is_image' => $isImage,
                'text_content' => $textContent,
                'data_base64' => ($isImage || $isVoice || $mime === 'application/pdf') ? $b64 : '',
            ];
        }

        if ($userMessage === '') {
            $hasVoice = collect($processedAttachments)->contains('is_voice', true);
            $userMessage = $hasVoice
                ? '🎙️ [Mensagem de Voz enviada pelo Comandante — ouça/transcreva o áudio em anexo e execute a solicitação]'
                : '📎 [Arquivo(s) enviado(s) pelo Comandante — analise o(s) anexo(s) e responda]';
        }

        $provider = $request->input('provider');
        $userId = $request->user()?->id;

        $assistantMessage = $orchestrator->talkInConversation(
            $conversation,
            $userMessage,
            $provider,
            $userId,
            $processedAttachments
        );

        $conversation->touch();

        return response()->json([
            'success' => true,
            'message' => $assistantMessage,
        ]);
    }

    /**
     * Serve a chat attachment file safely.
     */
    public function serveAttachment(string $filename): Response
    {
        $safeFilename = basename(preg_replace('/[^a-zA-Z0-9._\-]/', '', $filename));
        $filePath = storage_path('businesses/chat-attachments/' . $safeFilename);

        if (!$safeFilename || !File::exists($filePath) || File::isDirectory($filePath)) {
            return response()->json(['error' => 'Anexo não encontrado.'], 404);
        }

        $mime = File::mimeType($filePath) ?: 'application/octet-stream';
        if (str_ends_with($safeFilename, '.webm')) {
            $mime = 'audio/webm';
        } elseif (str_ends_with($safeFilename, '.ogg')) {
            $mime = 'audio/ogg';
        } elseif (str_ends_with($safeFilename, '.mp3')) {
            $mime = 'audio/mpeg';
        }

        return response()->file($filePath, [
            'Content-Type' => $mime,
            'Cache-Control' => 'private, max-age=86400',
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
