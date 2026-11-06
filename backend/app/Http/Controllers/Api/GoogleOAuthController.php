<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Jobs\SyncGoogleCalendarJob;
use App\Services\GoogleWorkspaceService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;

class GoogleOAuthController extends Controller
{
    public function __construct(private readonly GoogleWorkspaceService $googleService)
    {
    }

    public function redirect(Request $request): JsonResponse
    {
        $url = $this->googleService->getAuthorizationUrl($request->user());

        return response()->json(['auth_url' => $url]);
    }

    public function callback(Request $request): RedirectResponse
    {
        $code = $request->input('code');
        $frontendUrl = config('app.frontend_url', 'http://localhost:8080');

        if (! $code) {
            return redirect("{$frontendUrl}/settings/integrations?error=google_denied");
        }

        try {
            $this->googleService->handleCallback($code);
            return redirect("{$frontendUrl}/settings/integrations?success=google_connected");
        } catch (\Throwable $e) {
            return redirect("{$frontendUrl}/settings/integrations?error=" . urlencode($e->getMessage()));
        }
    }

    public function sync(Request $request): JsonResponse
    {
        SyncGoogleCalendarJob::dispatch($request->user());

        return response()->json([
            'message' => 'Sincronização do Google Calendar enfileirada no worker.',
        ]);
    }
}

