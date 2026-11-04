<?php

use App\Http\Controllers\Api\AiEngineController;
use App\Http\Controllers\Api\AnalyticsController;
use App\Http\Controllers\Api\ApprovalController;
use App\Http\Controllers\Api\BusinessController;
use App\Http\Controllers\Api\DashboardController;
use App\Http\Controllers\Api\JeffreyController;
use App\Http\Controllers\Api\VpsManagerController;
use Illuminate\Support\Facades\Route;

Route::get('/health', function () {
    return response()->json(['status' => 'healthy', 'system' => 'SpirandeliEmpire OS', 'timestamp' => now()]);
});

Route::prefix('v1')->group(function () {
    // Dashboard Consolidated
    Route::get('/dashboard', [DashboardController::class, 'index']);

    // Business Management
    Route::get('/businesses', [BusinessController::class, 'index']);
    Route::post('/businesses', [BusinessController::class, 'store']);
    Route::get('/businesses/{id}', [BusinessController::class, 'show']);
    Route::patch('/businesses/{id}/status', [BusinessController::class, 'updateStatus']);

    // Jeffrey AI
    Route::middleware(['internal.secret'])->group(function () {
        Route::post('/jeffrey/chat', [JeffreyController::class, 'chat']);
        Route::get('/jeffrey/memories', [JeffreyController::class, 'getMemories']);
        Route::get('/jeffrey/decisions', [JeffreyController::class, 'getDecisions']);
        Route::get('/jeffrey/approvals', [JeffreyController::class, 'getPendingApprovals']);
    });

    // Approvals Management
    Route::get('/approvals', [ApprovalController::class, 'index']);
    Route::post('/approvals/{id}/decide', [ApprovalController::class, 'decide']);

    // AI Engine (Google Gemini, OpenAI, Llama Local & Token Governance)
    Route::get('/ai-engine/status', [AiEngineController::class, 'status']);
    Route::post('/ai-engine/test-provider', [AiEngineController::class, 'testProvider']);
    Route::post('/ai-engine/complete', [AiEngineController::class, 'complete']);
    Route::post('/ai-engine/estimate-tokens', [AiEngineController::class, 'estimateTokens']);

    // Analytics & Financials
    Route::get('/analytics', [AnalyticsController::class, 'index']);

    // VPS Admin
    Route::get('/vps/metrics', [VpsManagerController::class, 'metrics']);
});

