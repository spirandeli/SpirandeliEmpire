<?php

use App\Http\Controllers\Api\AgentController;
use App\Http\Controllers\Api\AiEngineController;
use App\Http\Controllers\Api\AnalyticsController;
use App\Http\Controllers\Api\ApprovalController;
use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\BusinessController;
use App\Http\Controllers\Api\ChatController;
use App\Http\Controllers\Api\DashboardController;
use App\Http\Controllers\Api\FinanceController;
use App\Http\Controllers\Api\JeffreyController;
use App\Http\Controllers\Api\ProjectController;
use App\Http\Controllers\Api\TaskController;
use App\Http\Controllers\Api\VpsManagerController;
use App\Http\Middleware\EmpireAuthMiddleware;
use Illuminate\Support\Facades\Route;

Route::get('/health', function () {
    return response()->json([
        'status' => 'healthy',
        'system' => 'SpirandeliEmpire OS',
        'version' => '3.0.0',
        'timestamp' => now()->toIso8601String(),
    ]);
});

Route::prefix('v1')->group(function () {
    // --- 1. Public Authentication & Registration Gate ---
    Route::get('/auth/status', [AuthController::class, 'status']);
    Route::post('/auth/login', [AuthController::class, 'login']);
    Route::post('/auth/register', [AuthController::class, 'register']);
    Route::get('/chat/attachments/{filename}', [ChatController::class, 'serveAttachment']);

    // --- Protected Commander Routes ---
    Route::middleware(EmpireAuthMiddleware::class)->group(function () {
        Route::get('/auth/me', [AuthController::class, 'me']);
        Route::put('/auth/profile', [AuthController::class, 'updateProfile']);
        Route::get('/auth/profiles', [AuthController::class, 'listProfiles']);
        Route::post('/auth/logout', [AuthController::class, 'logout']);
        Route::post('/auth/change-password', [AuthController::class, 'changePassword']);

        // --- 2. Dashboard Consolidated Telemetry ---
        Route::get('/dashboard', [DashboardController::class, 'index']);

        // --- 3. Persistent Jeffrey Chat & Conversations ---
        Route::get('/chat/conversations', [ChatController::class, 'listConversations']);
        Route::post('/chat/conversations', [ChatController::class, 'createConversation']);
        Route::get('/chat/conversations/{id}', [ChatController::class, 'getConversation']);
        Route::patch('/chat/conversations/{id}', [ChatController::class, 'updateConversation']);
        Route::delete('/chat/conversations/{id}', [ChatController::class, 'deleteConversation']);
        Route::post('/chat/conversations/{id}/messages', [ChatController::class, 'sendMessage']);
        Route::get('/chat/tools', [ChatController::class, 'listTools']);
        Route::post('/chat/tools/execute', [ChatController::class, 'executeToolDirectly']);

        // Legacy Jeffrey Endpoint & Live Activity Telemetry
        Route::post('/jeffrey/chat', [JeffreyController::class, 'chat']);
        Route::get('/jeffrey/activity', [JeffreyController::class, 'getActivity']);
        Route::get('/jeffrey/memories', [JeffreyController::class, 'getMemories']);
        Route::get('/jeffrey/decisions', [JeffreyController::class, 'getDecisions']);
        Route::get('/jeffrey/approvals', [JeffreyController::class, 'getPendingApprovals']);

        // --- 4. Projects & Workspaces ---
        Route::get('/projects', [ProjectController::class, 'index']);
        Route::post('/projects', [ProjectController::class, 'store']);
        Route::get('/projects/{id}', [ProjectController::class, 'show']);
        Route::get('/projects/{id}/files', [ProjectController::class, 'files']);
        Route::post('/projects/{id}/read-file', [ProjectController::class, 'readFile']);

        // --- 5. Business Management, Accounts, Parameters & Automation ---
        Route::get('/businesses', [BusinessController::class, 'index']);
        Route::post('/businesses', [BusinessController::class, 'store']);
        Route::get('/businesses/{id}', [BusinessController::class, 'show']);
        Route::put('/businesses/{id}', [BusinessController::class, 'update']);
        Route::patch('/businesses/{id}/status', [BusinessController::class, 'updateStatus']);
        Route::post('/businesses/{id}/accounts', [BusinessController::class, 'saveAccounts']);
        Route::post('/businesses/{id}/automation', [BusinessController::class, 'saveAutomationParams']);
        Route::post('/businesses/{id}/run-agent', [BusinessController::class, 'runAgentAutomation']);
        Route::delete('/businesses/{id}', [BusinessController::class, 'destroy']);

        // --- 6. Financial Management & Budget Ceiling ---
        Route::get('/finance/summary', [FinanceController::class, 'summary']);
        Route::get('/finance/records', [FinanceController::class, 'records']);
        Route::post('/finance/expenses', [FinanceController::class, 'storeExpense']);
        Route::post('/finance/revenues', [FinanceController::class, 'storeRevenue']);
        Route::get('/analytics', [AnalyticsController::class, 'index']);

        // --- 7. VPS Administration, Docker Real & Security Audit ---
        Route::get('/vps/metrics', [VpsManagerController::class, 'metrics']);
        Route::get('/vps/security-audit', [VpsManagerController::class, 'securityAudit']);
        Route::get('/vps/containers', [VpsManagerController::class, 'containers']);
        Route::get('/vps/containers/{name}/logs', [VpsManagerController::class, 'containerLogs']);

        // --- 8. AI Engine & Specialized Agents ---
        Route::get('/ai-engine/status', [AiEngineController::class, 'status']);
        Route::post('/ai-engine/configure-keys', [AiEngineController::class, 'configureKeys']);
        Route::post('/ai-engine/test-provider', [AiEngineController::class, 'testProvider']);
        Route::post('/ai-engine/complete', [AiEngineController::class, 'complete']);
        Route::post('/ai-engine/estimate-tokens', [AiEngineController::class, 'estimateTokens']);
        Route::get('/agents', [AgentController::class, 'index']);
        Route::post('/agents', [AgentController::class, 'store']);
        Route::patch('/agents/{id}', [AgentController::class, 'update']);

        // --- 9. Approvals (Human-in-the-Loop) ---
        Route::get('/approvals', [ApprovalController::class, 'index']);
        Route::post('/approvals/{id}/decide', [ApprovalController::class, 'decide']);

        // --- 10. Tasks & Asynchronous Execution ---
        Route::get('/tasks', [TaskController::class, 'index']);
        Route::post('/tasks', [TaskController::class, 'store']);
        Route::get('/tasks/{id}', [TaskController::class, 'show']);
        Route::post('/tasks/{id}/cancel', [TaskController::class, 'cancel']);
        Route::post('/tasks/{id}/retry', [TaskController::class, 'retry']);
    });
});
