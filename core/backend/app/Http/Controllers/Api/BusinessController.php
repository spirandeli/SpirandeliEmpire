<?php

namespace App\Http\Controllers\Api;

use App\Models\Business;
use App\Models\JeffreyMemory;
use App\Models\Task;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use Throwable;

class BusinessController extends Controller
{
    /**
     * List all businesses with tasks and financial records count.
     */
    public function index(): JsonResponse
    {
        $businesses = Business::withCount(['tasks', 'financialRecords', 'memories'])->get();

        // If table is completely empty, seed the initial 4 businesses defined in architecture
        if ($businesses->isEmpty()) {
            $initial = [
                [
                    'name' => 'RISADA.exe',
                    'slug' => 'risada-exe',
                    'category' => 'YouTube Dark (Histórias Bíblicas)',
                    'description' => 'Canal de histórias bíblicas com ilustrações originais, voz brasileira masculina e fidelidade teológica rigorosa.',
                    'budget_limit_brl' => 60.00,
                    'status' => 'active',
                    'storage_path' => 'businesses/risada-exe',
                ],
                [
                    'name' => 'KDP Factory',
                    'slug' => 'kdp-factory',
                    'category' => 'Amazon KDP Publishing',
                    'description' => 'Pipeline de produção de eBooks, devocionais e planos de leitura bíblica para Amazon KDP.',
                    'budget_limit_brl' => 50.00,
                    'status' => 'active',
                    'storage_path' => 'businesses/kdp-factory',
                ],
                [
                    'name' => 'Digital Products Factory',
                    'slug' => 'digital-products',
                    'category' => 'Digital Goods & PDFs',
                    'description' => 'Estudos bíblicos em PDF, cronologias, planners devocionais e apostilas de alta conversão.',
                    'budget_limit_brl' => 40.00,
                    'status' => 'active',
                    'storage_path' => 'businesses/digital-products',
                ],
                [
                    'name' => 'Printable Factory',
                    'slug' => 'printable-factory',
                    'category' => 'Printables & Artes',
                    'description' => 'Quadros decorativos, cartões e artes em altíssima resolução para impressão física e venda.',
                    'budget_limit_brl' => 30.00,
                    'status' => 'active',
                    'storage_path' => 'businesses/printable-factory',
                ],
            ];

            foreach ($initial as $item) {
                Business::create($item);
            }
            $businesses = Business::withCount(['tasks', 'financialRecords', 'memories'])->get();
        }

        return response()->json([
            'success' => true,
            'businesses' => $businesses,
        ]);
    }

    /**
     * Show single business details with tasks and memories.
     */
    public function show(int $id): JsonResponse
    {
        $business = Business::with([
            'tasks' => fn($q) => $q->latest()->limit(20),
            'financialRecords' => fn($q) => $q->latest()->limit(20),
            'memories' => fn($q) => $q->where('is_active', true),
        ])->findOrFail($id);

        return response()->json([
            'success' => true,
            'business' => $business,
        ]);
    }

    /**
     * Store and provision new business (used by Business Factory).
     */
    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'category' => 'required|string|max:255',
            'description' => 'nullable|string',
            'template_used' => 'nullable|string',
            'budget_limit_brl' => 'nullable|numeric|min:0|max:200',
        ]);

        $slug = Str::slug($validated['name']);
        if ($slug === '') {
            // Name made only of symbols/emojis would yield an empty slug
            $slug = 'negocio-' . Str::lower(Str::random(6));
        }
        
        // Ensure unique slug
        $originalSlug = $slug;
        $counter = 1;
        while (Business::where('slug', $slug)->exists()) {
            $slug = "{$originalSlug}-{$counter}";
            $counter++;
        }

        $storagePath = "businesses/{$slug}";
        // storage/ is a writable mounted volume (./storage on the host). base_path() pointed
        // inside the app code dir, which is not writable by www-data in the container.
        $fullPath = storage_path($storagePath);

        // 1. Create directory structure physically (non-fatal: never block DB provisioning)
        $directoriesCreated = false;
        $fsError = null;
        try {
            foreach (['assets', 'output', 'scripts', 'logs'] as $dir) {
                if (!File::isDirectory("{$fullPath}/{$dir}")) {
                    File::makeDirectory("{$fullPath}/{$dir}", 0775, true);
                }
            }

            // Create initial README documentation
            $readmeContent = "# {$validated['name']}\n\n"
                . "> **Categoria:** {$validated['category']}\n"
                . "> **Criado em:** " . date('Y-m-d H:i:s') . "\n\n"
                . "## Proposta de Valor\n"
                . ($validated['description'] ?? 'Negócio digital provisionado pelo SpirandeliEmpire OS Business Factory.') . "\n\n"
                . "## Diretrizes Operacionais\n"
                . "- Orçamento Máximo Alocado: R$ " . ($validated['budget_limit_brl'] ?? '50.00') . "/mês\n"
                . "- Isolamento de armazenamento garantido em `{$storagePath}`\n";

            File::put($fullPath . '/README.md', $readmeContent);
            $directoriesCreated = true;
        } catch (Throwable $e) {
            $fsError = $e->getMessage();
            Log::warning("Business Factory: falha ao criar diretórios em {$fullPath}: {$fsError}");
        }

        // 2-4. Persist in database atomically
        try {
            $business = DB::transaction(function () use ($validated, $slug, $storagePath, $directoriesCreated, $fsError) {
                $business = Business::create([
                    'name' => $validated['name'],
                    'slug' => $slug,
                    'category' => $validated['category'],
                    'description' => $validated['description'] ?? null,
                    'template_used' => $validated['template_used'] ?? 'custom',
                    'storage_path' => $storagePath,
                    'budget_limit_brl' => $validated['budget_limit_brl'] ?? 50.00,
                    'status' => 'active',
                ]);

                // Register operational memory for Jeffrey
                JeffreyMemory::create([
                    'business_id' => $business->id,
                    'category' => 'context',
                    'key' => "business_launch_{$business->slug}",
                    'content' => "Negócio digital {$business->name} ({$business->category}) provisionado com sucesso. Teto: R$ {$business->budget_limit_brl}.",
                    'is_active' => true,
                ]);

                // Create initial setup task
                Task::create([
                    'business_id' => $business->id,
                    'agent_name' => 'Business Agent',
                    'title' => "Estruturação inicial de {$business->name}",
                    'type' => 'provisioning',
                    'status' => $directoriesCreated ? 'completed' : 'failed',
                    'payload' => ['category' => $business->category, 'storage' => $storagePath],
                    'result' => ['directories_created' => $directoriesCreated, 'readme' => $directoriesCreated, 'error' => $fsError],
                    'completed_at' => now(),
                ]);

                return $business;
            });
        } catch (Throwable $e) {
            Log::error('Business Factory: falha ao persistir negócio', [
                'slug' => $slug,
                'exception' => get_class($e),
                'message' => $e->getMessage(),
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Falha ao registrar o negócio no banco de dados.',
                'error' => config('app.debug') ? $e->getMessage() : 'Veja storage/logs/laravel.log para detalhes.',
            ], 500);
        }

        return response()->json([
            'success' => true,
            'business' => $business,
            'message' => $directoriesCreated
                ? "Negócio {$business->name} provisionado com sucesso!"
                : "Negócio {$business->name} registrado, mas a estrutura de pastas não pôde ser criada (verifique permissões de storage/).",
        ], 201);
    }

    /**
     * Update business status (active, paused, archived).
     */
    public function updateStatus(Request $request, int $id): JsonResponse
    {
        $business = Business::findOrFail($id);
        $request->validate(['status' => 'required|in:active,paused,provisioning,archived']);

        $business->status = $request->input('status');
        $business->save();

        return response()->json([
            'success' => true,
            'business' => $business,
        ]);
    }

    /**
     * Delete/archive business.
     */
    public function destroy(int $id): JsonResponse
    {
        $business = Business::findOrFail($id);
        $business->delete();

        return response()->json([
            'success' => true,
            'message' => "Negócio {$business->name} removido do sistema.",
        ]);
    }
}
