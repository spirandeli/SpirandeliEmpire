<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\Business\StoreBusinessRequest;
use App\Http\Requests\Business\UpdateBusinessRequest;
use App\Http\Resources\BusinessResource;
use App\Models\Business;
use App\Services\BusinessService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\AnonymousResourceCollection;

class BusinessController extends Controller
{
    public function __construct(private readonly BusinessService $businesses)
    {
    }

    public function index(Request $request): AnonymousResourceCollection
    {
        $request->validate([
            'status' => ['sometimes', 'in:draft,planning,active,paused,archived'],
            'type' => ['sometimes', 'string'],
            'search' => ['sometimes', 'string', 'max:120'],
            'per_page' => ['sometimes', 'integer', 'min:1', 'max:100'],
        ]);

        $businesses = $request->user()->businesses()
            ->when($request->filled('status'), fn ($q) => $q->where('status', $request->status))
            ->when($request->filled('type'), fn ($q) => $q->where('type', $request->type))
            ->when($request->filled('search'), fn ($q) => $q->where('name', 'like', '%'.$request->search.'%'))
            ->withCount([
                'tasks as tasks_open' => fn ($q) => $q->open(),
                'approvalQueues as pending_approvals' => fn ($q) => $q->awaitingReview(),
                'tiktokProducts',
            ])
            ->latest('updated_at')
            ->paginate($request->integer('per_page', 25));

        return BusinessResource::collection($businesses);
    }

    public function store(StoreBusinessRequest $request): JsonResponse
    {
        $data = $request->safe()->except(['with_default_automations']);

        $business = $this->businesses->create(
            $request->user(),
            $data,
            $request->boolean('with_default_automations', true),
        );

        return (new BusinessResource($business))->response()->setStatusCode(201);
    }

    public function show(Request $request, Business $business): BusinessResource
    {
        $this->owned($business, $request);

        $business->load([
            'automations',
            'tiktokProducts' => fn ($q) => $q->latest()->limit(50),
        ])->loadCount([
            'tasks as tasks_open' => fn ($q) => $q->open(),
            'approvalQueues as pending_approvals' => fn ($q) => $q->awaitingReview(),
            'tiktokProducts',
        ]);

        return new BusinessResource($business);
    }

    public function mineNow(Request $request, Business $business): JsonResponse
    {
        $this->owned($business, $request);

        \App\Jobs\TikTokShopMinerJob::dispatch($business);

        return response()->json([
            'message' => 'Job de mineração de produtos TikTok Shop despachado com sucesso!',
        ]);
    }

    public function update(UpdateBusinessRequest $request, Business $business): BusinessResource
    {
        $this->owned($business, $request);

        return new BusinessResource($this->businesses->update($business, $request->validated()));
    }

    public function destroy(Request $request, Business $business): JsonResponse
    {
        $this->owned($business, $request);

        $business->forceFill(['status' => 'archived', 'automation_enabled' => false])->save();
        $business->delete();

        return response()->json(null, 204);
    }

    public function activate(Request $request, Business $business): BusinessResource
    {
        $this->owned($business, $request);

        return new BusinessResource($this->businesses->activate($business));
    }

    public function pause(Request $request, Business $business): BusinessResource
    {
        $this->owned($business, $request);

        return new BusinessResource($this->businesses->pause($business));
    }
}

