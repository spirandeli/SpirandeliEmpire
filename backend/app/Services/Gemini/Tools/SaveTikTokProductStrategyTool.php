<?php

namespace App\Services\Gemini\Tools;

use App\Models\Business;
use App\Models\TikTokProduct;

class SaveTikTokProductStrategyTool extends AbstractTool
{
    public function name(): string
    {
        return 'saveTikTokProductStrategy';
    }

    public function description(): string
    {
        return 'Salva ou refina a análise e estratégia de um produto candidato da TikTok Shop. Registra scores de margem (0-100), velocidade de vendas (0-100), potencial viral (0-100), links de afiliado e o racional da IA (ângulo de abordagem, dores do público, ganchos recomendados).';
    }

    public function parameters(): array
    {
        return [
            'type' => 'OBJECT',
            'properties' => [
                'business_id' => [
                    'type' => 'INTEGER',
                    'description' => 'ID do negócio TikTok Shop Affiliate. Se omitido, utiliza o negócio do contexto.',
                ],
                'external_id' => [
                    'type' => 'STRING',
                    'description' => 'Identificador do produto na TikTok Shop ou código SKU de referência.',
                ],
                'title' => [
                    'type' => 'STRING',
                    'description' => 'Nome completo do produto comercializado.',
                ],
                'category' => [
                    'type' => 'STRING',
                    'description' => 'Categoria do produto (ex: Cozinha & Casa, Beleza & Cuidados, Eletrônicos).',
                ],
                'price' => [
                    'type' => 'NUMBER',
                    'description' => 'Preço de venda ao consumidor final.',
                ],
                'commission_rate' => [
                    'type' => 'NUMBER',
                    'description' => 'Porcentagem de comissão do afiliado (ex: 15.00 para 15%).',
                ],
                'sales_velocity' => [
                    'type' => 'NUMBER',
                    'description' => 'Estimativa de vendas diárias ou velocidade de tração recente.',
                ],
                'margin_score' => [
                    'type' => 'INTEGER',
                    'description' => 'Pontuação de margem financeira (0 a 100).',
                ],
                'velocity_score' => [
                    'type' => 'INTEGER',
                    'description' => 'Pontuação de velocidade de vendas (0 a 100).',
                ],
                'viral_score' => [
                    'type' => 'INTEGER',
                    'description' => 'Potencial de engajamento e viralidade no formato TikTok (0 a 100).',
                ],
                'product_url' => [
                    'type' => 'STRING',
                    'description' => 'URL oficial do produto na TikTok Shop.',
                ],
                'affiliate_link' => [
                    'type' => 'STRING',
                    'description' => 'Link de comissionamento de afiliado.',
                ],
                'ai_analysis' => [
                    'type' => 'OBJECT',
                    'description' => 'Racional analítico do Gemini: { target_audience, core_pain_points: string[], hook_angles: string[], objections: string[], demonstration_ideas: string[] }.',
                ],
                'status' => [
                    'type' => 'STRING',
                    'enum' => ['mined', 'analyzing', 'selected', 'content_ready', 'published', 'discarded'],
                    'description' => 'Status do produto no funil de esteira.',
                ],
            ],
            'required' => ['external_id', 'title'],
        ];
    }

    public function execute(array $arguments, ToolExecutionContext $context): array
    {
        try {
            $businessId = $arguments['business_id'] ?? $context->business?->id;

            if (! $businessId) {
                return [
                    'success' => false,
                    'error' => 'É necessário informar business_id ou ter um negócio ativo no contexto para salvar um produto.',
                ];
            }

            $business = Business::where('user_id', $context->user->id)->findOrFail($businessId);

            $price = isset($arguments['price']) ? (float) $arguments['price'] : 0.0;
            $rate = isset($arguments['commission_rate']) ? (float) $arguments['commission_rate'] : 0.0;
            $commValue = round($price * ($rate / 100), 2);

            $product = TikTokProduct::firstOrNew([
                'business_id' => $business->id,
                'external_id' => $arguments['external_id'],
            ]);

            $marginScore = (int) ($arguments['margin_score'] ?? $product->margin_score ?? 50);
            $velocityScore = (int) ($arguments['velocity_score'] ?? $product->velocity_score ?? 50);
            $viralScore = (int) ($arguments['viral_score'] ?? $product->viral_score ?? 50);

            $product->fill([
                'title' => $arguments['title'],
                'category' => $arguments['category'] ?? $product->category,
                'price' => $price ?: ($product->price ?? 0),
                'commission_rate' => $rate ?: ($product->commission_rate ?? 0),
                'commission_value' => $commValue ?: ($product->commission_value ?? 0),
                'sales_velocity' => $arguments['sales_velocity'] ?? $product->sales_velocity ?? 0,
                'product_url' => $arguments['product_url'] ?? $product->product_url,
                'affiliate_link' => $arguments['affiliate_link'] ?? $product->affiliate_link,
                'margin_score' => $marginScore,
                'velocity_score' => $velocityScore,
                'viral_score' => $viralScore,
                'status' => $arguments['status'] ?? TikTokProduct::STATUS_SELECTED,
                'ai_analysis' => $arguments['ai_analysis'] ?? $product->ai_analysis,
                'selected_at' => now(),
            ]);

            $product->recalculateOverallScore();
            $product->save();

            return [
                'success' => true,
                'product_id' => $product->id,
                'external_id' => $product->external_id,
                'title' => $product->title,
                'overall_score' => $product->overall_score,
                'commission_value' => (float) $product->commission_value,
                'status' => $product->status,
                'message' => "Produto \"{$product->title}\" registrado com Score Geral {$product->overall_score}/100 e comissão estimada de R$ {$product->commission_value}.",
            ];
        } catch (\Throwable $e) {
            return [
                'success' => false,
                'error' => 'Falha ao salvar produto: ' . $e->getMessage(),
            ];
        }
    }
}

