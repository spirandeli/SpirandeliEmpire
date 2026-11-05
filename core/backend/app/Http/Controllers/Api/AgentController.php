<?php

namespace App\Http\Controllers\Api;

use App\Models\Agent;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Str;

class AgentController extends Controller
{
    /**
     * List all agents.
     */
    public function index(): JsonResponse
    {
        $agents = Agent::all();

        // Seed initial specialized agents if table is empty
        if ($agents->isEmpty()) {
            $defaultAgents = [
                [
                    'name' => 'Jeffrey',
                    'slug' => 'jeffrey',
                    'role' => 'Orquestrador & Arquiteto Central',
                    'description' => 'Coordena todos os negócios do império, executa ferramentas, gerencia infraestrutura e atua como consultor executivo.',
                    'model' => 'gemini',
                    'system_prompt' => 'Você é Jeffrey, orquestrador executivo do SpirandeliEmpire OS.',
                    'authorized_tools' => ['*'],
                    'is_active' => true,
                ],
                [
                    'name' => 'Research Agent',
                    'slug' => 'research-agent',
                    'role' => 'Pesquisador & Validador Teológico',
                    'description' => 'Realiza pesquisas bíblicas sem alucinação, validação histórica e levantamento de referências exatas para o RISADA.exe.',
                    'model' => 'gemini',
                    'system_prompt' => 'Você é o Research Agent do RISADA.exe. Valide referências históricas e bíblicas.',
                    'authorized_tools' => ['read_project_file', 'search_project_files'],
                    'is_active' => true,
                ],
                [
                    'name' => 'Business Analyst',
                    'slug' => 'business-analyst',
                    'role' => 'Analista de Viabilidade & Monetização',
                    'description' => 'Calcula orçamentos, projeções de receita, viabilidade de novos modelos e controle de gastos.',
                    'model' => 'gemini',
                    'system_prompt' => 'Você é o Business Analyst. Foque em viabilidade comercial e respeito ao teto de R$ 200/mês.',
                    'authorized_tools' => ['list_businesses', 'get_business_status'],
                    'is_active' => true,
                ],
                [
                    'name' => 'Content Creator',
                    'slug' => 'content-creator',
                    'role' => 'Roteirista & Redator de Alta Retenção',
                    'description' => 'Escreve roteiros narrativos de Shorts/Vídeos longos e manuscritos completos para Amazon KDP.',
                    'model' => 'gemini',
                    'system_prompt' => 'Você é o Content Creator. Escreva roteiros com ganchos a cada 30 segundos.',
                    'authorized_tools' => ['create_project_file'],
                    'is_active' => true,
                ],
                [
                    'name' => 'DevOps Engineer',
                    'slug' => 'devops-engineer',
                    'role' => 'Administrador da VPS & Docker',
                    'description' => 'Supervisiona containers, volumes de armazenamento, consumo de memória e saúde dos daemons.',
                    'model' => 'gemini',
                    'system_prompt' => 'Você é o DevOps Engineer. Zele pela integridade dos containers e Uptime Kuma.',
                    'authorized_tools' => ['get_system_metrics', 'list_docker_containers'],
                    'is_active' => true,
                ],
                [
                    'name' => 'Finance Agent',
                    'slug' => 'finance-agent',
                    'role' => 'Guardião do Teto Orçamentário',
                    'description' => 'Monitora todas as despesas e bloqueia preventivamente qualquer gasto que ameace estourar o limite de R$ 200/mês.',
                    'model' => 'gemini',
                    'system_prompt' => 'Você é o Finance Agent. O limite de R$ 200/mês é sagrado.',
                    'authorized_tools' => ['get_system_metrics'],
                    'is_active' => true,
                ],
            ];

            foreach ($defaultAgents as $a) {
                Agent::create($a);
            }
            $agents = Agent::all();
        }

        return response()->json([
            'success' => true,
            'agents' => $agents,
        ]);
    }

    /**
     * Store new custom agent.
     */
    public function store(Request $request): JsonResponse
    {
        $validated = $request->validate([
            'name' => 'required|string|max:100',
            'role' => 'required|string|max:100',
            'description' => 'nullable|string',
            'model' => 'required|string',
            'system_prompt' => 'nullable|string',
            'authorized_tools' => 'nullable|array',
        ]);

        $agent = Agent::create([
            'name' => $validated['name'],
            'slug' => Str::slug($validated['name']),
            'role' => $validated['role'],
            'description' => $validated['description'] ?? null,
            'model' => $validated['model'],
            'system_prompt' => $validated['system_prompt'] ?? null,
            'authorized_tools' => $validated['authorized_tools'] ?? [],
            'is_active' => true,
        ]);

        return response()->json([
            'success' => true,
            'agent' => $agent,
        ], 201);
    }

    /**
     * Update agent settings.
     */
    public function update(Request $request, int $id): JsonResponse
    {
        $agent = Agent::findOrFail($id);

        $validated = $request->validate([
            'name' => 'nullable|string|max:100',
            'role' => 'nullable|string|max:100',
            'description' => 'nullable|string',
            'model' => 'nullable|string',
            'system_prompt' => 'nullable|string',
            'authorized_tools' => 'nullable|array',
            'is_active' => 'nullable|boolean',
        ]);

        $agent->update($validated);

        return response()->json([
            'success' => true,
            'agent' => $agent,
        ]);
    }
}
