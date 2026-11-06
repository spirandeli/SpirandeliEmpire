<?php

namespace App\Services\Gemini\Tools;

use App\Models\ApprovalQueue;
use App\Models\Business;
use App\Services\ApprovalService;
use Illuminate\Validation\ValidationException;

class SubmitForHumanApprovalTool extends AbstractTool
{
    public function __construct(private readonly ApprovalService $approvalService)
    {
    }

    public function name(): string
    {
        return 'submitForHumanApproval';
    }

    public function description(): string
    {
        return 'Envia um pacote de trabalho pronto gerado pela IA (ex: produto minerado + 3 hooks virais + roteiro de vídeo + copy + prompts visuais, ou um plano estratégico) para a Inbox de Supervisão Humana (Human-in-the-Loop) para que o usuário revise e aprove antes da publicação.';
    }

    public function parameters(): array
    {
        return [
            'type' => 'OBJECT',
            'properties' => [
                'business_id' => [
                    'type' => 'INTEGER',
                    'description' => 'ID do negócio. Se omitido, usa o negócio ativo no contexto.',
                ],
                'task_id' => [
                    'type' => 'INTEGER',
                    'description' => 'ID da tarefa relacionada (se houver). Se informada, a tarefa será movida para "Aguardando Supervisão".',
                ],
                'type' => [
                    'type' => 'STRING',
                    'enum' => [
                        ApprovalQueue::TYPE_TIKTOK_CONTENT_PACKAGE,
                        ApprovalQueue::TYPE_BUSINESS_PLAN,
                        ApprovalQueue::TYPE_STRATEGY_CHANGE,
                        ApprovalQueue::TYPE_CALENDAR_ACTION,
                        ApprovalQueue::TYPE_GENERIC,
                    ],
                    'description' => 'Tipo da entrega submetida.',
                ],
                'title' => [
                    'type' => 'STRING',
                    'description' => 'Título de destaque para a entrega na Inbox de Supervisão.',
                ],
                'summary' => [
                    'type' => 'STRING',
                    'description' => 'Resumo executivo do que foi preparado e do potencial esperado (ex: margem estimada, público, ângulo).',
                ],
                'payload' => [
                    'type' => 'OBJECT',
                    'description' => 'Estrutura completa da entrega. Para tiktok_content_package deve conter: { product, hooks: string[], script: string, visual_prompts: string[], caption: string, hashtags: string[], cta: string }.',
                ],
                'priority' => [
                    'type' => 'STRING',
                    'enum' => ['low', 'medium', 'high', 'urgent'],
                    'description' => 'Prioridade de revisão pelo usuário.',
                ],
                'agent_confidence' => [
                    'type' => 'NUMBER',
                    'description' => 'Grau de confiança do agente na qualidade do material (0.00 a 1.00).',
                ],
            ],
            'required' => ['title', 'payload'],
        ];
    }

    public function execute(array $arguments, ToolExecutionContext $context): array
    {
        try {
            $businessId = $arguments['business_id'] ?? $context->business?->id;

            if (! $businessId) {
                return [
                    'success' => false,
                    'error' => 'É necessário informar business_id ou ter um negócio ativo no contexto para submeter aprovação.',
                ];
            }

            $business = Business::where('user_id', $context->user->id)->findOrFail($businessId);

            $approval = $this->approvalService->submit(
                $business,
                [
                    'title' => $arguments['title'],
                    'summary' => $arguments['summary'] ?? null,
                    'type' => $arguments['type'] ?? ApprovalQueue::TYPE_GENERIC,
                    'payload' => $arguments['payload'],
                    'priority' => $arguments['priority'] ?? 'medium',
                    'agent_confidence' => isset($arguments['agent_confidence']) ? (float) $arguments['agent_confidence'] : 0.85,
                    'task_id' => $arguments['task_id'] ?? null,
                ]
            );

            return [
                'success' => true,
                'approval_id' => $approval->id,
                'title' => $approval->title,
                'status' => $approval->status->value,
                'expires_at' => $approval->expires_at?->toIso8601String(),
                'message' => "Entrega \"{$approval->title}\" submetida à Inbox de Supervisão do usuário com sucesso (ID #{$approval->id}).",
            ];
        } catch (ValidationException $e) {
            return [
                'success' => false,
                'error' => 'Erro de validação nos dados da entrega.',
                'details' => $e->errors(),
            ];
        } catch (\Throwable $e) {
            return [
                'success' => false,
                'error' => 'Falha ao submeter para aprovação: ' . $e->getMessage(),
            ];
        }
    }
}

