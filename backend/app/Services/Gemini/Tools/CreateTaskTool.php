<?php

namespace App\Services\Gemini\Tools;

use App\Enums\TaskAssignee;
use App\Models\Business;
use App\Services\TaskService;
use Illuminate\Validation\ValidationException;

class CreateTaskTool extends AbstractTool
{
    public function __construct(private readonly TaskService $taskService)
    {
    }

    public function name(): string
    {
        return 'createTask';
    }

    public function description(): string
    {
        return 'Cria uma nova tarefa no quadro de operações do negócio. Define se a tarefa será executada pelo Agente IA (background worker) ou pelo Humano (supervisão/gravação), com prioridade, prazos e parâmetros de execução.';
    }

    public function parameters(): array
    {
        return [
            'type' => 'OBJECT',
            'properties' => [
                'business_id' => [
                    'type' => 'INTEGER',
                    'description' => 'ID do negócio ao qual a tarefa pertence. Se não informado, utiliza o negócio atual do contexto.',
                ],
                'title' => [
                    'type' => 'STRING',
                    'description' => 'Título claro e objetivo da tarefa.',
                ],
                'description' => [
                    'type' => 'STRING',
                    'description' => 'Instruções ou checklist para execução da tarefa.',
                ],
                'assignee' => [
                    'type' => 'STRING',
                    'enum' => ['agent', 'user'],
                    'description' => 'Quem deve executar: "agent" (worker da IA) ou "user" (o próprio usuário).',
                ],
                'priority' => [
                    'type' => 'STRING',
                    'enum' => ['low', 'medium', 'high', 'urgent'],
                    'description' => 'Nível de prioridade da tarefa.',
                ],
                'due_at' => [
                    'type' => 'STRING',
                    'description' => 'Data/hora limite para conclusão (formato ISO 8601, ex: 2026-11-08T18:00:00Z).',
                ],
                'scheduled_at' => [
                    'type' => 'STRING',
                    'description' => 'Data/hora agendada para início da execução (formato ISO 8601).',
                ],
                'agent_action' => [
                    'type' => 'STRING',
                    'description' => 'Para tarefas do agente: identificador da ação a ser processada pelo worker (ex: mine_products, generate_content, analyze_competition).',
                ],
                'payload' => [
                    'type' => 'OBJECT',
                    'description' => 'Parâmetros específicos necessários para o worker executar a ação.',
                ],
            ],
            'required' => ['title', 'assignee'],
        ];
    }

    public function execute(array $arguments, ToolExecutionContext $context): array
    {
        try {
            $businessId = $arguments['business_id'] ?? $context->business?->id;

            if (! $businessId) {
                return [
                    'success' => false,
                    'error' => 'É necessário informar business_id ou ter um negócio ativo no contexto para criar uma tarefa.',
                ];
            }

            $business = Business::where('user_id', $context->user->id)->findOrFail($businessId);

            $task = $this->taskService->create(
                $business,
                [
                    'title' => $arguments['title'],
                    'description' => $arguments['description'] ?? null,
                    'assignee' => $arguments['assignee'] ?? TaskAssignee::Agent->value,
                    'priority' => $arguments['priority'] ?? 'medium',
                    'due_at' => $arguments['due_at'] ?? null,
                    'scheduled_at' => $arguments['scheduled_at'] ?? null,
                    'agent_action' => $arguments['agent_action'] ?? null,
                    'payload' => $arguments['payload'] ?? null,
                ],
                source: 'agent'
            );

            return [
                'success' => true,
                'task_id' => $task->id,
                'title' => $task->title,
                'assignee' => $task->assignee->value,
                'status' => $task->status->value,
                'priority' => $task->priority,
                'business_id' => $business->id,
                'message' => "Tarefa #{$task->id} (\"{$task->title}\") criada com sucesso para {$task->assignee->label()}.",
            ];
        } catch (ValidationException $e) {
            return [
                'success' => false,
                'error' => 'Erro de validação nos dados da tarefa.',
                'details' => $e->errors(),
            ];
        } catch (\Throwable $e) {
            return [
                'success' => false,
                'error' => 'Falha ao criar tarefa: ' . $e->getMessage(),
            ];
        }
    }
}

