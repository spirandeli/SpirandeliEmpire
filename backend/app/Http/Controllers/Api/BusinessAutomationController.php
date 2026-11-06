<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\Business\AutomationRequest;
use App\Http\Resources\BusinessAutomationResource;
use App\Models\Business;
use App\Models\BusinessAutomation;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/** Configurações de Automação/Cron de um negócio (aba do BusinessDetailView). */
class BusinessAutomationController extends Controller
{
    public function index(Request $request, Business $business)
    {
        $this->owned($business, $request);

        return BusinessAutomationResource::collection($business->automations()->orderBy('id')->get());
    }

    public function store(AutomationRequest $request, Business $business): JsonResponse
    {
        $this->owned($business, $request);

        $automation = $business->automations()->create($request->validated());

        return (new BusinessAutomationResource($automation->refresh()))->response()->setStatusCode(201);
    }

    public function update(AutomationRequest $request, Business $business, BusinessAutomation $automation): BusinessAutomationResource
    {
        $this->owned($business, $request);
        abort_unless($automation->business_id === $business->id, 404);

        $automation->fill($request->validated());
        if ($automation->isDirty('cron_expression') || $automation->isDirty('timezone')) {
            $automation->next_run_at = null; // recalculado no evento `saving` do model
        }
        $automation->save();

        return new BusinessAutomationResource($automation->refresh());
    }

    public function destroy(Request $request, Business $business, BusinessAutomation $automation): JsonResponse
    {
        $this->owned($business, $request);
        abort_unless($automation->business_id === $business->id, 404);

        $automation->delete();

        return response()->json(null, 204);
    }
}

