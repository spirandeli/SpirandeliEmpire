<?php

namespace App\Services\Gemini\Tools;

use App\Models\AgentLearning;
use App\Models\Business;
use Illuminate\Validation\ValidationException;

class SaveBusinessLearningTool extends AbstractTool
{
    public function name(): string
    {
        return 'saveBusinessLearning';
    }

    public function description(): string
    {
        return 'Grava uma tese ou aprendizado validado por dados de conversão e ROI na memória contínua do negócio (agent_learnings), guiando as futuras decisões do agente.';
    }

    public function parameters(): array
    {
        return [
            'type' => 'OBJECT',
            'properties' => [
                'business_id' => [
                    'type' => 'INTEGER',
                    'description' => 'ID do negócio. Se omitido, usa o do contexto.',
                ],
                'topic' => [
                    'type' => 'STRING',
                    'description' => 'Tópico ou categoria do aprendizado (ex: Ângulos de Gancho, Comportamento de Checkout, Melhores Horários).',
                ],
                'insight' => [
                    'type' => 'STRING',
                    'description' => 'Conclusão clara e acionável baseada em dados reais de ROI.',
                ],
                'confidence_score' => [
                    'type' => 'INTEGER',
                    'description' => 'Nível de confiança da tese (0 a 100).',
                ],
                'data_source' => [
                    'type' => 'STRING',
                    'description' => 'Origem da evidência (ex: webhook_conversions, ooda_cycle, ab_testing).',
                ],
            ],
            'required' => ['topic', 'insight'],
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

        $learning = AgentLearning::create([
            'business_id' => $business->id,
            'topic' => $arguments['topic'],
            'insight' => $arguments['insight'],
            'confidence_score' => (int) ($arguments['confidence_score'] ?? 85),
            'data_source' => $arguments['data_source'] ?? 'ooda_cycle',
            'metadata' => [
                'created_by' => 'Gemini 3.8 Growth Engine',
            ],
        ]);

        return [
            'success' => true,
            'learning_id' => $learning->id,
            'topic' => $learning->topic,
            'confidence_score' => $learning->confidence_score,
        ];
    }
}
