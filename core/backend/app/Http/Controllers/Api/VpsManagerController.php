<?php

namespace App\Http\Controllers\Api;

use App\Services\VpsMonitorService;
use Illuminate\Http\JsonResponse;
use Illuminate\Routing\Controller;

class VpsManagerController extends Controller
{
    public function metrics(VpsMonitorService $vps): JsonResponse
    {
        return response()->json($vps->getSystemSummary());
    }
}

