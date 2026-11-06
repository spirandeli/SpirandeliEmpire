<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\AiUsageLog;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class AdminAiGovernanceController extends Controller
{
    /**
     * Retorna o dashboard completo de governança, custos e ranking de consumo de IA.
     */
    public function stats(Request $request): JsonResponse
    {
        $startOfMonth = now()->startOfMonth();

        // 1. Métricas Globais (Agregações SQL otimizadas)
        $monthlyTokens = (int) AiUsageLog::where('created_at', '>=', $startOfMonth)->sum('total_tokens');
        $monthlyCostUsd = (float) AiUsageLog::where('created_at', '>=', $startOfMonth)->sum('estimated_cost_usd');
        $monthlyCostBrl = round($monthlyCostUsd * 5.80, 2);

        $totalUsers = User::count();
        $activeAiUsers = User::where('is_ai_active', true)->count();
        $blockedUsers = User::where('is_ai_active', false)->count();

        // 2. Ranking de Usuários por Consumo
        $users = User::query()
            ->withCount(['businesses', 'tasks'])
            ->orderByDesc('tokens_used_this_month')
            ->get()
            ->map(function (User $u) use ($startOfMonth) {
                $userCostUsd = (float) $u->aiUsageLogs()
                    ->where('created_at', '>=', $startOfMonth)
                    ->sum('estimated_cost_usd');

                $limit = $u->monthly_token_limit ?: 1;
                $pct = round(($u->tokens_used_this_month / $limit) * 100, 1);

                return [
                    'id' => $u->id,
                    'name' => $u->name,
                    'email' => $u->email,
                    'is_admin' => $u->isAdmin(),
                    'is_ai_active' => $u->isAiActive(),
                    'monthly_token_limit' => $u->monthly_token_limit,
                    'tokens_used_this_month' => $u->tokens_used_this_month,
                    'usage_percentage' => min(100, $pct),
                    'is_exceeded' => $u->hasExceededMonthlyTokenLimit(),
                    'cost_usd' => round($userCostUsd, 4),
                    'cost_brl' => round($userCostUsd * 5.80, 2),
                    'businesses_count' => $u->businesses_count,
                    'tasks_count' => $u->tasks_count,
                ];
            });

        // 3. Distribuição por Modelo
        $byModel = AiUsageLog::query()
            ->where('created_at', '>=', $startOfMonth)
            ->groupBy('model')
            ->selectRaw('model, sum(total_tokens) as total_tokens, sum(estimated_cost_usd) as total_cost, count(*) as calls_count')
            ->get();

        // 4. Distribuição por Contexto (Chat vs Workers/Cron)
        $byContext = AiUsageLog::query()
            ->where('created_at', '>=', $startOfMonth)
            ->groupBy('context')
            ->selectRaw('context, sum(total_tokens) as total_tokens, sum(estimated_cost_usd) as total_cost, count(*) as calls_count')
            ->get();

        // 5. Histórico Recente de Chamadas (Audit Trail)
        $recentLogs = AiUsageLog::query()
            ->with(['user:id,name,email', 'business:id,name'])
            ->latest('id')
            ->limit(25)
            ->get()
            ->map(fn ($log) => [
                'id' => $log->id,
                'user_name' => $log->user?->name ?? 'Sistema',
                'business_name' => $log->business?->name,
                'model' => $log->model,
                'context' => $log->context,
                'prompt_tokens' => $log->prompt_tokens,
                'completion_tokens' => $log->completion_tokens,
                'total_tokens' => $log->total_tokens,
                'estimated_cost_usd' => (float) $log->estimated_cost_usd,
                'latency_ms' => $log->latency_ms,
                'created_at' => $log->created_at?->toIso8601String(),
            ]);

        return response()->json([
            'metrics' => [
                'monthly_tokens' => $monthlyTokens,
                'monthly_cost_usd' => round($monthlyCostUsd, 4),
                'monthly_cost_brl' => $monthlyCostBrl,
                'total_users' => $totalUsers,
                'active_ai_users' => $activeAiUsers,
                'blocked_users' => $blockedUsers,
            ],
            'users' => $users,
            'by_model' => $byModel,
            'by_context' => $byContext,
            'recent_logs' => $recentLogs,
        ]);
    }

    /**
     * Atualiza limite de tokens e flags de governança do usuário.
     */
    public function updateLimits(Request $request, User $user): JsonResponse
    {
        $validated = $request->validate([
            'monthly_token_limit' => ['required', 'integer', 'min:10000', 'max:500000000'],
            'is_ai_active' => ['sometimes', 'boolean'],
        ]);

        $user->update($validated);

        return response()->json([
            'message' => "Limites do usuário {$user->name} atualizados com sucesso.",
            'user' => [
                'id' => $user->id,
                'monthly_token_limit' => $user->monthly_token_limit,
                'is_ai_active' => $user->is_ai_active,
            ],
        ]);
    }

    /**
     * Kill-switch imediato: ativa ou desativa o acesso à IA para aquele usuário.
     */
    public function toggleKillSwitch(User $user): JsonResponse
    {
        $newState = ! $user->is_ai_active;
        $user->update(['is_ai_active' => $newState]);

        return response()->json([
            'message' => $newState
                ? "Acesso à IA ATIVADO para {$user->name}."
                : "Acesso à IA BLOQUEADO para {$user->name}. Todos os workers deste usuário serão suspensos.",
            'is_ai_active' => $newState,
        ]);
    }

    /**
     * Zera o consumo mensal de tokens do usuário (ex: virada de ciclo manual ou renovação).
     */
    public function resetUsage(User $user): JsonResponse
    {
        $user->update(['tokens_used_this_month' => 0]);

        return response()->json([
            'message' => "Consumo mensal de tokens de {$user->name} foi resetado para zero.",
            'tokens_used_this_month' => 0,
        ]);
    }
}

