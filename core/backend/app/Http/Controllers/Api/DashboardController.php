<?php

namespace App\Http\Controllers\Api;

use App\Models\AgentDecision;
use App\Models\ApprovalRequest;
use App\Models\Business;
use App\Models\Conversation;
use App\Models\FinancialRecord;
use App\Models\Project;
use App\Models\Task;
use App\Services\BudgetGuardService;
use App\Services\VpsMonitorService;
use Carbon\Carbon;
use Illuminate\Http\JsonResponse;
use Illuminate\Routing\Controller;

class DashboardController extends Controller
{
    public function index(VpsMonitorService $vps, BudgetGuardService $budget): JsonResponse
    {
        $businesses = Business::withCount('tasks')->get();
        $budgetStatus = $budget->getBudgetStatus();
        $systemMetrics = $vps->getSystemSummary();

        $startOfMonth = Carbon::now()->startOfMonth();

        $activeBusinessesCount = $businesses->where('status', 'active')->count();
        $pausedBusinessesCount = $businesses->where('status', 'paused')->count();
        $provisioningBusinessesCount = $businesses->where('status', 'provisioning')->count();

        $runningTasksCount = Task::where('status', 'in_progress')->count();
        $completedTasksCount = Task::where('status', 'completed')->count();
        $failedTasksCount = Task::where('status', 'failed')->count();
        $pendingApprovalsCount = ApprovalRequest::where('status', 'pending')->count();
        $totalProjects = Project::count();
        $totalConversations = Conversation::count();

        $monthRevenue = (float) FinancialRecord::where('type', 'revenue')
            ->where('recorded_at', '>=', $startOfMonth)
            ->sum('amount_brl');

        $monthExpenses = (float) FinancialRecord::where('type', '!=', 'revenue')
            ->where('recorded_at', '>=', $startOfMonth)
            ->sum('amount_brl');

        $recentTasks = Task::with('business:id,name,slug')
            ->latest()
            ->limit(5)
            ->get();

        $recentDecisions = AgentDecision::with('business:id,name,slug')
            ->latest()
            ->limit(5)
            ->get();

        return response()->json([
            'success' => true,
            'summary' => [
                'total_businesses' => $businesses->count(),
                'active_businesses' => $activeBusinessesCount,
                'paused_businesses' => $pausedBusinessesCount,
                'provisioning_businesses' => $provisioningBusinessesCount,
                'running_tasks' => $runningTasksCount,
                'completed_tasks' => $completedTasksCount,
                'failed_tasks' => $failedTasksCount,
                'pending_approvals' => $pendingApprovalsCount,
                'total_projects' => $totalProjects,
                'total_conversations' => $totalConversations,
            ],
            'financials' => [
                'total_revenue_brl' => round($monthRevenue, 2),
                'total_expenses_brl' => round($monthExpenses, 2),
                'estimated_profit_brl' => round($monthRevenue - $monthExpenses, 2),
                'budget' => $budgetStatus,
            ],
            'vps' => $systemMetrics,
            'businesses' => $businesses,
            'recent_tasks' => $recentTasks,
            'recent_decisions' => $recentDecisions,
        ]);
    }
}
