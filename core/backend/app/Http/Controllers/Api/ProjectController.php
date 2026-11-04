<?php

namespace App\Http\Controllers\Api;

use App\Models\Project;
use App\Services\ToolRegistryService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\File;
use Illuminate\Support\Str;

class ProjectController extends Controller
{
    /**
     * List all projects.
     */
    public function index(): JsonResponse
    {
        $projects = Project::withCount('conversations')->latest()->get();

        // If no projects exist in the DB, seed default projects based on workspace
        if ($projects->isEmpty()) {
            $defaultProjects = [
                [
                    'name' => 'SpirandeliEmpire OS Core',
                    'slug' => 'spirandeli-empire-core',
                    'description' => 'Núcleo do sistema operacional do império: Backend Laravel, Frontend Vue 3 e Caddy TLS.',
                    'path' => base_path(),
                    'git_repo' => 'https://github.com/spirandeli/SpirandeliEmpire.git',
                    'git_branch' => 'main',
                    'status' => 'active',
                    'stack' => 'laravel+vue',
                ],
                [
                    'name' => 'RISADA.exe Workspace',
                    'slug' => 'risada-exe-workspace',
                    'description' => 'Canal Dark de histórias bíblicas: Roteiros, narração Piper TTS, imagens e pipeline FFmpeg.',
                    'path' => storage_path('businesses/risada-exe'),
                    'git_branch' => 'main',
                    'status' => 'active',
                    'stack' => 'python+ffmpeg',
                ],
                [
                    'name' => 'KDP Factory Workspace',
                    'slug' => 'kdp-factory-workspace',
                    'description' => 'Fábrica de eBooks, devocionais e estudos bíblicos para publicação na Amazon KDP.',
                    'path' => storage_path('businesses/kdp-factory'),
                    'git_branch' => 'main',
                    'status' => 'active',
                    'stack' => 'python+markdown',
                ],
                [
                    'name' => 'TikTok Shop Afiliados',
                    'slug' => 'tiktok-shop-afiliados',
                    'description' => 'Pipeline de automação de vídeos curtos para TikTok Shop com clonagem de voz XTTS e n8n.',
                    'path' => storage_path('businesses/tiktok-shop-afiliados'),
                    'git_branch' => 'main',
                    'status' => 'active',
                    'stack' => 'n8n+xtts',
                ],
            ];

            foreach ($defaultProjects as $dp) {
                Project::create($dp);
            }
            $projects = Project::all();
        }

        return response()->json([
            'success' => true,
            'projects' => $projects,
        ]);
    }

    /**
     * Store new project.
     */
    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'name' => 'required|string|max:255',
            'description' => 'nullable|string',
            'path' => 'required|string',
            'git_repo' => 'nullable|string',
            'git_branch' => 'nullable|string',
            'stack' => 'nullable|string',
        ]);

        $slug = Str::slug($validated['name']);

        $project = Project::create([
            'name' => $validated['name'],
            'slug' => $slug,
            'description' => $validated['description'] ?? null,
            'path' => $validated['path'],
            'git_repo' => $validated['git_repo'] ?? null,
            'git_branch' => $validated['git_branch'] ?? 'main',
            'stack' => $validated['stack'] ?? 'general',
            'status' => 'active',
        ]);

        return response()->json([
            'success' => true,
            'project' => $project,
        ], 201);
    }

    /**
     * Show project details with Git status.
     */
    public function show(int $id): JsonResponse
    {
        $project = Project::with('conversations')->findOrFail($id);

        $gitStatus = 'Repositório não inicializado ou inacessível.';
        $gitBranch = $project->git_branch;

        if (File::exists($project->path . '/.git') || File::exists(base_path('.git'))) {
            $dir = escapeshellarg($project->path);
            $gitBranch = trim(shell_exec("git -C {$dir} branch --show-current 2>&1") ?: 'main');
            $statusRaw = shell_exec("git -C {$dir} status --short 2>&1");
            $gitStatus = trim($statusRaw ?: 'Working tree clean (sem modificações pendentes)');
        }

        return response()->json([
            'success' => true,
            'project' => $project,
            'git' => [
                'branch' => $gitBranch,
                'status' => $gitStatus,
            ],
        ]);
    }

    /**
     * Safe directory listing inside project workspace.
     */
    public function files(Request $request, int $id, ToolRegistryService $tools): JsonResponse
    {
        $project = Project::findOrFail($id);
        $subpath = $request->input('subpath', '');

        $result = $tools->executeTool('inspect_project', [
            'project_id' => $project->id,
            'subpath' => $subpath,
        ]);

        return response()->json($result);
    }

    /**
     * Safe file reader.
     */
    public function readFile(Request $request, int $id, ToolRegistryService $tools): JsonResponse
    {
        $project = Project::findOrFail($id);
        $request->validate(['path' => 'required|string']);

        $result = $tools->executeTool('read_project_file', [
            'project_id' => $project->id,
            'relative_path' => $request->input('path'),
        ]);

        return response()->json($result);
    }
}
