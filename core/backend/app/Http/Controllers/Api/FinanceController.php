<?php

namespace App\Http\Controllers\Api;

use App\Models\Business;
use App\Models\FinancialRecord;
use App\Services\BudgetGuardService;
use Carbon\Carbon;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;

class FinanceController extends Controller
{
    /**
     * Financial consolidated summary and budget guard status.
     */
    public function summary(BudgetGuardService $budget): JsonResponse
    {
        $startOfMonth = Carbon::now()->startOfMonth();

        $totalRevenueAllTime = (float) FinancialRecord::where('type', 'revenue')->sum('amount_brl');
        $totalExpensesAllTime = (float) FinancialRecord::where('type', '!=', 'revenue')->sum('amount_brl');

        $monthRevenue = (float) FinancialRecord::where('type', 'revenue')
            ->where('recorded_at', '>=', $startOfMonth)
            ->sum('amount_brl');

        $monthExpenses = (float) FinancialRecord::where('type', '!=', 'revenue')
            ->where('recorded_at', '>=', $startOfMonth)
            ->sum('amount_brl');

        $budgetStatus = $budget->getBudgetStatus();

        // Expenses grouped by category
        $expensesByCategory = FinancialRecord::where('type', '!=', 'revenue')
            ->where('recorded_at', '>=', $startOfMonth)
            ->selectRaw('category, sum(amount_brl) as total')
            ->groupBy('category')
            ->get();

        // Expenses grouped by business
        $expensesByBusiness = FinancialRecord::where('type', '!=', 'revenue')
            ->where('recorded_at', '>=', $startOfMonth)
            ->with('business:id,name,slug')
            ->selectRaw('business_id, sum(amount_brl) as total')
            ->groupBy('business_id')
            ->get();

        return response()->json([
            'success' => true,
            'summary' => [
                'total_revenue_brl' => round($totalRevenueAllTime, 2),
                'total_expenses_brl' => round($totalExpensesAllTime, 2),
                'all_time_profit_brl' => round($totalRevenueAllTime - $totalExpensesAllTime, 2),
                'month_revenue_brl' => round($monthRevenue, 2),
                'month_expenses_brl' => round($monthExpenses, 2),
                'month_profit_brl' => round($monthRevenue - $monthExpenses, 2),
            ],
            'budget' => $budgetStatus,
            'categories' => $expensesByCategory,
            'businesses_cost' => $expensesByBusiness,
        ]);
    }

    /**
     * List all financial records (Ledger).
     */
    public function records(Request $request): JsonResponse
    {
        $type = $request->input('type');
        $businessId = $request->input('business_id');

        $query = FinancialRecord::with('business:id,name,slug')->latest('recorded_at');

        if ($type) {
            $query->where('type', $type);
        }
        if ($businessId) {
            $query->where('business_id', $businessId);
        }

        $records = $query->paginate(50);

        return response()->json([
            'success' => true,
            'records' => $records,
        ]);
    }

    /**
     * Record a new expense with strict budget ceiling check.
     */
    public function storeExpense(Request $request, BudgetGuardService $budget): JsonResponse
    {
        $validated = $request->validate([
            'description' => 'required|string|max:255',
            'amount_brl' => 'required|numeric|min:0.01',
            'category' => 'required|string|in:infraestrutura,ai_api,armazenamento,dominio_ssl,ferramentas,outros',
            'business_id' => 'nullable|integer|exists:businesses,id',
            'recorded_at' => 'nullable|date',
        ]);

        $amount = (float) $validated['amount_brl'];

        // Strict budget guard check: max R$ 200/month
        if (!$budget->canSpend($amount)) {
            $status = $budget->getBudgetStatus();
            return response()->json([
                'success' => false,
                'error' => "BLOQUEIO DE GOVERNANÇA: A despesa de R$ {$amount} excede o teto mensal permitido de R$ {$status['monthly_limit_brl']}. Restante disponível: R$ {$status['remaining_brl']}.",
                'budget_status' => $status,
            ], 422);
        }

        $record = FinancialRecord::create([
            'business_id' => $validated['business_id'] ?? null,
            'type' => 'infrastructure_expense',
            'category' => $validated['category'],
            'description' => $validated['description'],
            'amount_brl' => $amount,
            'is_confirmed' => true,
            'recorded_at' => $validated['recorded_at'] ?? now(),
        ]);

        // If associated with a business, increment business monthly cost
        if ($record->business_id) {
            $business = Business::find($record->business_id);
            if ($business) {
                $business->increment('current_month_cost_brl', $amount);
            }
        }

        return response()->json([
            'success' => true,
            'record' => $record->load('business'),
            'budget_status' => $budget->getBudgetStatus(),
        ], 201);
    }

    /**
     * Record new revenue.
     */
    public function storeRevenue(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'description' => 'required|string|max:255',
            'amount_brl' => 'required|numeric|min:0.01',
            'category' => 'required|string|in:youtube_adsense,amazon_kdp,produtos_digitais,afiliados,outros',
            'business_id' => 'nullable|integer|exists:businesses,id',
            'recorded_at' => 'nullable|date',
        ]);

        $amount = (float) $validated['amount_brl'];

        $record = FinancialRecord::create([
            'business_id' => $validated['business_id'] ?? null,
            'type' => 'revenue',
            'category' => $validated['category'],
            'description' => $validated['description'],
            'amount_brl' => $amount,
            'is_confirmed' => true,
            'recorded_at' => $validated['recorded_at'] ?? now(),
        ]);

        if ($record->business_id) {
            $business = Business::find($record->business_id);
            if ($business) {
                $business->increment('total_revenue_brl', $amount);
            }
        }

        return response()->json([
            'success' => true,
            'record' => $record->load('business'),
        ], 201);
    }
}
