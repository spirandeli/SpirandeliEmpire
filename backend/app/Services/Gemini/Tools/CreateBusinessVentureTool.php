<?php

namespace App\Services\Gemini\Tools;

use App\Services\BusinessService;
use Illuminate\Validation\ValidationException;

class CreateBusinessVentureTool extends AbstractTool
{
    public function __construct(private readonly BusinessService $businessService)
    {
    }

    public function name(): string
    {
        return 'createBusinessVenture';
    }

    public function description(): string
    {
        return 'Cria e estrutura um novo empreendimento/negócio digital no sistema. Salva o Business Model Canvas estruturado, nicho, metas financeiras/operacionais, canais de aquisição, regras de marca e playbook de automação.';
    }

    public function parameters(): array
    {
        return [
            'type' => 'OBJECT',
            'properties' => [
                'name' => [
                    'type' => 'STRING',
                    'description' => 'Nome do negócio ou marca.',
                ],
                'type' => [
                    'type' => 'STRING',
                    'description' => 'Tipo do modelo de negócio.',
                    'enum' => config('abvos.business_types', ['tiktok_shop_affiliate', 'dropshipping', 'digital_product', 'content_channel', 'custom']),
                ],
                'niche' => [
                    'type' => 'STRING',
                    'description' => 'Nicho ou segmento de mercado (ex: Utensílios de Cozinha, Automação Residencial, Finanças).',
                ],
                'description' => [
                    'type' => 'STRING',
                    'description' => 'Resumo executivo do modelo de negócio e proposta de valor.',
                ],
                'canvas' => [
                    'type' => 'OBJECT',
                    'description' => 'Business Model Canvas com blocos estratégicos (value_propositions, customer_segments, revenue_streams, cost_structure, key_partners, key_activities, key_resources, customer_relationships, channels).',
                ],
                'brand_rules' => [
                    'type' => 'OBJECT',
                    'description' => 'Diretrizes de marca, tom de voz, chamadas para ação (CTAs) proibidas/recomendadas e identidade.',
                ],
                'goals' => [
                    'type' => 'OBJECT',
                    'description' => 'Metas SMART (ex: videos_per_week, monthly_revenue_target, expected_roi_margin).',
                ],
                'acquisition_channels' => [
                    'type' => 'ARRAY',
                    'items' => ['type' => 'STRING'],
                    'description' => 'Canais primários de tráfego e vendas (ex: tiktok_organic, tiktok_shop, instagram_reels).',
                ],
                'automation_playbook' => [
                    'type' => 'OBJECT',
                    'description' => 'Passo a passo do playbook autônomo e regras de execução do agente.',
                ],
                'kpis' => [
                    'type' => 'OBJECT',
                    'description' => 'Indicadores-chave de desempenho a monitorar.',
                ],
            ],
            'required' => ['name', 'type', 'niche', 'description'],
        ];
    }

    public function execute(array $arguments, ToolExecutionContext $context): array
    {
        try {
            $business = $this->businessService->create(
                $context->user,
                [
                    'name' => $arguments['name'],
                    'type' => $arguments['type'] ?? 'custom',
                    'niche' => $arguments['niche'] ?? null,
                    'description' => $arguments['description'] ?? null,
                    'canvas' => $arguments['canvas'] ?? null,
                    'brand_rules' => $arguments['brand_rules'] ?? null,
                    'goals' => $arguments['goals'] ?? null,
                    'acquisition_channels' => $arguments['acquisition_channels'] ?? null,
                    'automation_playbook' => $arguments['automation_playbook'] ?? null,
                    'kpis' => $arguments['kpis'] ?? null,
                    'ai_summary' => $arguments['description'] ?? null,
                ],
                withDefaultAutomations: true
            );

            return [
                'success' => true,
                'business_id' => $business->id,
                'name' => $business->name,
                'slug' => $business->slug,
                'status' => $business->status->value,
                'type' => $business->type,
                'automations_count' => $business->automations->count(),
                'message' => "Negócio \"{$business->name}\" criado com sucesso e automações base configuradas.",
            ];
        } catch (ValidationException $e) {
            return [
                'success' => false,
                'error' => 'Erro de validação ao criar o negócio.',
                'details' => $e->errors(),
            ];
        } catch (\Throwable $e) {
            return [
                'success' => false,
                'error' => 'Falha inesperada ao registrar o negócio: ' . $e->getMessage(),
            ];
        }
    }
}

