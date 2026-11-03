<?php

namespace App\Http\Controllers\Api;

use App\Models\ApprovalRequest;
use App\Models\Business;
use App\Models\FinancialRecord;
use App\Models\Task;
use App\Services\BudgetGuardService;
use App\Services\VpsMonitorService;
use Illuminate\Http\JsonResponse;
use Illuminate\Routing\Controller;

class DashboardController extends Controller
{
    public function index(VpsMonitorService $vps, BudgetGuardService $budget): JsonResponse
    {
        $businesses = Business::all();
        $budgetStatus = $budget->getBudgetStatus();
        $systemMetrics = $vps->getSystemSummary();

        $activeBusinessesCount = $businesses->where('status', 'active')->count();
        $pausedBusinessesCount = $businesses->where('status', 'paused')->count();
        $provisioningBusinessesCount = $businesses->where('status', 'provisioning')->count();

        $runningTasksCount = Task::where('status', 'in_progress')->count();
        $pendingApprovalsCount = ApprovalRequest::where('status', 'pending')->count();

        $totalRevenue = FinancialRecord::where('type', 'revenue')->sum('amount_brl');
        $totalExpenses = FinancialRecord::where('type', '!=', 'revenue')->sum('amount_brl');

        return response()->json([
            'summary' => [
                'total_businesses' => $businesses->count(),
                'active_businesses' => $activeBusinessesCount,
                'paused_businesses' => $pausedBusinessesCount,
                'provisioning_businesses' => $provisioningBusinessesCount,
                'running_tasks' => $runningTasksCount,
                'pending_approvals' => $pendingApprovalsCount,
            ],
            'financials' => [
                'total_revenue_brl' => round((float) $totalRevenue, 2),
                'total_expenses_brl' => round((float) $totalExpenses, 2),
                'estimated_profit_brl' => round((float) ($totalRevenue - $totalExpenses), 2),
                'budget' => $budgetStatus,
            ],
            'vps' => $systemMetrics,
            'businesses' => $businesses,
        ]);
    }
}

