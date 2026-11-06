<?php

use App\Http\Controllers\Api\AgentConversationController;
use App\Http\Controllers\Api\AgentLogController;
use App\Http\Controllers\Api\ApprovalQueueController;
use App\Http\Controllers\Api\AppleShortcutsController;
use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\GoogleOAuthController;
use App\Http\Controllers\Api\BusinessAutomationController;
use App\Http\Controllers\Api\BusinessController;
use App\Http\Controllers\Api\IntegrationController;
use App\Http\Controllers\Api\TaskController;
use App\Http\Controllers\Api\UniversalWebhookController;
use Illuminate\Support\Facades\Route;

/*
|--------------------------------------------------------------------------
| API (prefixo /api)
|--------------------------------------------------------------------------
| SPA: GET /sanctum/csrf-cookie -> POST /api/auth/login (cookie de sessão)
| Token: POST /api/auth/login com `device_name` -> Authorization: Bearer
*/

Route::prefix('auth')->group(function () {
    Route::post('register', [AuthController::class, 'register'])->middleware('throttle:10,1');
    Route::post('login', [AuthController::class, 'login']);

    Route::middleware('auth:sanctum')->group(function () {
        Route::get('me', [AuthController::class, 'me']);
        Route::put('profile', [AuthController::class, 'updateProfile']);
        Route::post('logout', [AuthController::class, 'logout']);
        Route::post('provision-showcase', [AuthController::class, 'provisionShowcase']);
    });
});

// --- Webhooks Públicos & Callbacks Externos ---------------------------------
Route::post('webhooks/shortcuts', [AppleShortcutsController::class, 'handle'])
    ->middleware('throttle:60,1');
Route::post('webhooks/in/{secret_token}', [UniversalWebhookController::class, 'handle'])
    ->middleware('throttle:120,1');
Route::get('integrations/google/callback', [GoogleOAuthController::class, 'callback']);

Route::middleware(['auth:sanctum', 'throttle:api'])->group(function () {

    // --- Negócios + automações + growth metrics --------------------------------
    Route::apiResource('businesses', BusinessController::class);
    Route::post('businesses/{business}/activate', [BusinessController::class, 'activate']);
    Route::post('businesses/{business}/pause', [BusinessController::class, 'pause']);
    Route::post('businesses/{business}/mine', [BusinessController::class, 'mineNow']);
    Route::get('businesses/{business}/growth-metrics', [UniversalWebhookController::class, 'metrics']);
    Route::post('businesses/{business}/webhooks/simulate', [UniversalWebhookController::class, 'simulate']);
    Route::post('businesses/{business}/optimize-growth', [UniversalWebhookController::class, 'optimizeNow']);
    Route::apiResource('businesses.automations', BusinessAutomationController::class)
        ->except('show')
        ->scoped();

    // --- Tarefas (Kanban híbrido) -------------------------------------------------
    Route::get('tasks/board', [TaskController::class, 'board']);
    Route::apiResource('tasks', TaskController::class);
    Route::patch('tasks/{task}/move', [TaskController::class, 'move']);

    // --- Inbox de Supervisão (aprovações) ---------------------------------------------
    Route::get('approvals/summary', [ApprovalQueueController::class, 'summary']);
    Route::get('approvals', [ApprovalQueueController::class, 'index']);
    Route::get('approvals/{approval}', [ApprovalQueueController::class, 'show']);
    Route::post('approvals/{approval}/approve', [ApprovalQueueController::class, 'approve']);
    Route::post('approvals/{approval}/revision', [ApprovalQueueController::class, 'revision']);
    Route::post('approvals/{approval}/reject', [ApprovalQueueController::class, 'reject']);

    // --- Conversas & Chat com Gemini 3.8 (Incubadora / Operação) -------------
    Route::get('agent/conversations', [AgentConversationController::class, 'index']);
    Route::post('agent/conversations', [AgentConversationController::class, 'store']);
    Route::get('agent/conversations/{uuid}', [AgentConversationController::class, 'show']);
    Route::post('agent/conversations/{uuid}/messages', [AgentConversationController::class, 'sendMessage'])
        ->middleware('throttle:agent');

    // --- Console do agente ----------------------------------------------------------------
    Route::get('agent/logs', [AgentLogController::class, 'index']);

    // --- Cofre de integrações ---------------------------------------------------------------
    Route::get('integrations', [IntegrationController::class, 'index']);
    Route::put('integrations/gemini', [IntegrationController::class, 'saveGemini']);
    Route::put('integrations/apple-caldav', [IntegrationController::class, 'saveAppleCaldav']);
    Route::post('integrations/apple-caldav/sync', [IntegrationController::class, 'syncAppleCaldav']);
    Route::get('integrations/google/redirect', [GoogleOAuthController::class, 'redirect']);
    Route::post('integrations/google/sync', [GoogleOAuthController::class, 'sync']);
    Route::post('integrations/shortcuts/token', [IntegrationController::class, 'generateShortcutsToken']);
    Route::delete('integrations/{integration}', [IntegrationController::class, 'destroy']);
});

// --- Rotas Administrativas & Governança de IA (Apenas is_admin = true) -------
Route::prefix('admin')->middleware(['auth:sanctum', 'admin', 'throttle:api'])->group(function () {
    Route::get('ai-governance/stats', [\App\Http\Controllers\Api\AdminAiGovernanceController::class, 'stats']);
    Route::patch('ai-governance/users/{user}/limits', [\App\Http\Controllers\Api\AdminAiGovernanceController::class, 'updateLimits']);
    Route::post('ai-governance/users/{user}/kill-switch', [\App\Http\Controllers\Api\AdminAiGovernanceController::class, 'toggleKillSwitch']);
    Route::post('ai-governance/users/{user}/reset-usage', [\App\Http\Controllers\Api\AdminAiGovernanceController::class, 'resetUsage']);
});
