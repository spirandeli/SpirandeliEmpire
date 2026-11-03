<?php

namespace App\Http\Controllers\Api;

use App\Models\Business;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Str;

class BusinessController extends Controller
{
    public function index(): JsonResponse
    {
        return response()->json(Business::with(['tasks', 'financialRecords'])->get());
    }

    public function show(int $id): JsonResponse
    {
        $business = Business::with(['tasks', 'financialRecords', 'memories'])->findOrFail($id);
        return response()->json($business);
    }

    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'category' => 'required|string|max:255',
            'description' => 'nullable|string',
            'template_used' => 'nullable|string',
            'budget_limit_brl' => 'nullable|numeric|min:0',
        ]);

        $slug = Str::slug($validated['name']);
        $storagePath = "businesses/{$slug}";

        $business = Business::create([
            'name' => $validated['name'],
            'slug' => $slug,
            'category' => $validated['category'],
            'description' => $validated['description'] ?? null,
            'template_used' => $validated['template_used'] ?? 'custom',
            'storage_path' => $storagePath,
            'budget_limit_brl' => $validated['budget_limit_brl'] ?? 50.00,
            'status' => 'provisioning',
        ]);

        return response()->json($business, 201);
    }

    public function updateStatus(Request $request, int $id): JsonResponse
    {
        $business = Business::findOrFail($id);
        $request->validate(['status' => 'required|in:active,paused,provisioning,archived']);

        $business->status = $request->input('status');
        $business->save();

        return response()->json($business);
    }
}

