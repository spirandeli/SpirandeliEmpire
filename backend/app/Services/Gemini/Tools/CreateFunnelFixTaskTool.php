<?php

namespace App\Services\Gemini\Tools;

use App\Enums\TaskAssignee;
use App\Enums\TaskStatus;
use App\Models\Business;
use App\Models\Task;
use App\Services\TaskService;
use Illuminate\Validation\ValidationException;

class CreateFunnelFixTaskTool extends AbstractTool
{
    public function __construct(private readonly ?TaskService $taskService = null)
    {
    }

    public function name(): string
    {
        return 'createFunnelFixTask';
    }

    public function description(): string
    {
        return 'Cria uma tarefa de correção de funil de alta prioridade no Kanban para resolver gargalos de conversão identificados no ciclo OODA.';
    }

    public function parameters(): array
    {
        return [
            'type' => 'OBJECT',
            'properties' => [
                'business_id' => [
                    'type' => 'INTEGER',
                    'description' => 'ID do negócio. Se omitido, usa o negócio atual do contexto.',
                ],
                'title' => [
                    'type' => 'STRING',
                    'description' => 'Título da ação corretiva de funil.',
                ],
                'description' => [
                    'type' => 'STRING',
                    'description' => 'Diagnóstico detalhado do gargalo e passos para corrigi-lo.',
                ],
                'bottleneck_stage' => [
                    'type' => 'STRING',
                    'enum' => ['attraction', 'retention', 'conversion', 'checkout'],
                    'description' => 'Etapa do funil onde o gargalo foi identificado.',
                ],
                'priority' => [
                    'type' => 'STRING',
                    'enum' => ['high', 'urgent'],
                    'description' => 'Prioridade da tarefa.',
                ],
                'assignee' => [
                    'type' => 'STRING',
                    'enum' => ['agent', 'user'],
                    'description' => 'Quem deve executar: "agent" para automação/IA ou "user" para gravação/decisão financeira.',
                ],
            ],
            'required' => ['title', 'description', 'bottleneck_stage'],
        ];
    }

    public function execute(array $arguments, ToolExecutionContext $context): array
    {
        $businessId = $arguments['business_id'] ?? $context->business?->id;
        if (!$businessId) {
            throw ValidationException::withMessages(['business_id' => 'ID do negócio é obrigatório.']);
        }

        $business = Business::find($businessId);
        if (!$business) {
            throw ValidationException::withMessages(['business_id' => 'Negócio não encontrado.']);
        }

        $assigneeStr = strtolower((string) ($arguments['assignee'] ?? 'agent'));
        $assignee = $assigneeStr === 'user' ? TaskAssignee::User : TaskAssignee::Agent;
        $status = $assignee === TaskAssignee::User ? TaskStatus::TodoUser : TaskStatus::Backlog;

        $priorityStr = strtolower((string) ($arguments['priority'] ?? 'high'));
        $priority = in_array($priorityStr, ['urgent', 'high', 'medium', 'low'], true) ? $priorityStr : 'high';

        $task = Task::create([
            'business_id' => $business->id,
            'user_id' => $business->user_id,
            'title' => '🔧 Funil: ' . $arguments['title'],
            'description' => $arguments['description'],
            'assignee' => $assignee,
            'status' => $status,
            'priority' => $priority,
            'metadata' => [
                'type' => 'funnel_fix',
                'bottleneck_stage' => $arguments['bottleneck_stage'],
                'source' => 'ooda_growth_engine',
            ],
        ]);

        return [
            'success' => true,
            'task_id' => $task->id,
            'title' => $task->title,
            'assignee' => $task->assignee->value,
            'status' => $task->status->value,
        ];
    }
}
