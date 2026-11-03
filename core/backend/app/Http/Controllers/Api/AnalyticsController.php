<?php

namespace App\Http\Controllers\Api;

use App\Models\FinancialRecord;
use App\Services\BudgetGuardService;
use Illuminate\Http\JsonResponse;
use Illuminate\Routing\Controller;

class AnalyticsController extends Controller
{
    public function index(BudgetGuardService $budget): JsonResponse
    {
        $records = FinancialRecord::with('business')->latest()->limit(100)->get();
        $budgetStatus = $budget->getBudgetStatus();

        return response()->json([
            'records' => $records,
            'budget' => $budgetStatus,
        ]);
    }
}

