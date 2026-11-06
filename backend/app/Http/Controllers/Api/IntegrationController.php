<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\Integration\SaveAppleCaldavRequest;
use App\Http\Requests\Integration\SaveGeminiRequest;
use App\Http\Resources\IntegrationResource;
use App\Models\UserIntegration;
use App\Services\IntegrationService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/** Cofre de integrações (SettingsIntegrationsView). Segredos nunca voltam na resposta. */
class IntegrationController extends Controller
{
    public function __construct(private readonly IntegrationService $integrations)
    {
    }

    public function index(Request $request)
    {
        return IntegrationResource::collection(
            $request->user()->integrations()->orderBy('provider')->get()
        );
    }

    public function saveGemini(SaveGeminiRequest $request): JsonResponse
    {
        $integration = $this->integrations->saveGemini(
            $request->user(),
            $request->validated('api_key'),
            $request->validated('model'),
        );

        // PUT idempotente (upsert): sempre 200, mesmo na primeira gravação.
        return (new IntegrationResource($integration))->response()->setStatusCode(200);
    }

    public function saveAppleCaldav(SaveAppleCaldavRequest $request): JsonResponse
    {
        $integration = $this->integrations->saveAppleCaldav(
            $request->user(),
            $request->validated('apple_id'),
            $request->validated('app_password'),
            $request->validated('server_url'),
        );

        // Despacha descoberta de calendários e validação em background
        \App\Jobs\SyncAppleCalDavJob::dispatch($request->user());

        // PUT idempotente (upsert): sempre 200, mesmo na primeira gravação.
        return (new IntegrationResource($integration))->response()->setStatusCode(200);
    }

    public function syncAppleCaldav(Request $request): JsonResponse
    {
        \App\Jobs\SyncAppleCalDavJob::dispatch($request->user());

        return response()->json([
            'message' => 'Sincronização do iCloud CalDAV enfileirada no worker.',
        ]);
    }

    /** Gera/rotaciona o token do webhook. O token em texto plano aparece só nesta resposta. */
    public function generateShortcutsToken(Request $request): JsonResponse
    {
        $request->validate(['name' => ['sometimes', 'string', 'max:60']]);

        ['integration' => $integration, 'token' => $token] = $this->integrations
            ->generateShortcutsToken($request->user(), $request->input('name'));

        return response()->json([
            'data' => new IntegrationResource($integration),
            'token' => $token,
            'webhook_url' => url('/api/webhooks/shortcuts'),
            'notice' => 'Guarde este token agora: ele não será exibido novamente.',
        ], 201);
    }

    public function destroy(Request $request, UserIntegration $integration): JsonResponse
    {
        $this->owned($integration, $request);

        $this->integrations->disconnect($integration);

        return response()->json(null, 204);
    }
}
