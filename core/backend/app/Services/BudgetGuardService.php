<?php

namespace App\Services;

use App\Models\FinancialRecord;
use Carbon\Carbon;
use Illuminate\Support\Facades\DB;

class BudgetGuardService
{
    protected float $monthlyLimit;

    public function __construct()
    {
        $this->monthlyLimit = (float) config('ai.monthly_budget_limit_brl', env('MONTHLY_BUDGET_LIMIT_BRL', 200.00));
    }

    /**
     * Get current month spent expenses.
     */
    public function getCurrentMonthExpenses(): float
    {
        $startOfMonth = Carbon::now()->startOfMonth();
        
        return (float) FinancialRecord::where('type', '!=', 'revenue')
            ->where('recorded_at', '>=', $startOfMonth)
            ->sum('amount_brl');
    }

    /**
     * Check if an additional amount can be spent without violating the R$ 200 limit.
     * Uses database transaction lock to avoid race conditions in concurrent execution.
     */
    public function canSpend(float $amount): bool
    {
        return DB::transaction(function () use ($amount) {
            $startOfMonth = Carbon::now()->startOfMonth();
            $current = (float) FinancialRecord::where('type', '!=', 'revenue')
                ->where('recorded_at', '>=', $startOfMonth)
                ->lockForUpdate()
                ->sum('amount_brl');

            return ($current + $amount) <= $this->monthlyLimit;
        });
    }

    /**
     * Get budget status report.
     */
    public function getBudgetStatus(): array
    {
        $spent = $this->getCurrentMonthExpenses();
        $remaining = max(0, $this->monthlyLimit - $spent);
        $percentage = ($this->monthlyLimit > 0) ? ($spent / $this->monthlyLimit) * 100 : 100;
        $alertPct = (float) config('ai.alert_budget_percentage', env('ALERT_BUDGET_PERCENTAGE', 80));

        return [
            'monthly_limit_brl' => $this->monthlyLimit,
            'current_spent_brl' => round($spent, 2),
            'remaining_brl' => round($remaining, 2),
            'percentage_used' => round($percentage, 2),
            'is_over_budget' => $spent > $this->monthlyLimit,
            'warning_triggered' => $percentage >= $alertPct,
        ];
    }
}

