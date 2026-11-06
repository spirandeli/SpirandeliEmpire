<?php

namespace App\Services\Playbooks;

use App\Models\Business;
use App\Services\Playbooks\Contracts\BusinessPlaybookInterface;

class EcommerceDropPlaybook implements BusinessPlaybookInterface
{
    public function getArchetypeName(): string
    {
        return Business::ARCHETYPE_ECOMMERCE;
    }

    public function getDisplayName(): string
    {
        return 'E-commerce & Dropshipping Direto';
    }

    public function getRecommendedNorthStarMetric(): string
    {
        return 'roas';
    }

    public function getFunnelStages(): array
    {
        return [
            'tof_attraction' => 'UGC / Apresentação do Produto / Vídeo Efeito Wow',
            'mof_conversion' => 'Página do Produto com Avaliações com Fotos / Tabela de Tamanhos',
            'bof_retention' => 'Checkout Transparente com Order Bump / Frete Sedex com Desconto',
        ];
    }

    public function getAngles(): array
    {
        return [
            'gadget_inovador' => '"O produto que você não sabia que precisava até ver este vídeo"',
            'solucao_domestica' => 'Economize tempo na cozinha/faxina com esse acessório prático',
            'oferta_compre_1_leve_2' => 'Oferta de lançamento com 50% de desconto por tempo limitado',
            'unboxing_emocional' => 'Experiência sensorial de abrir a embalagem e primeira impressão real',
        ];
    }

    public function getSystemPromptExtension(): string
    {
        return <<<PROMPT
# PLAYBOOK ATIVO: E-COMMERCE & DROPSHIPPING (ARQUÉTIPO DE PRODUTO FÍSICO)
- Foco em ROAS, Ticket Médio (AOV) e Margem Líquida após frete e custos do produto.
- Invista pesado em gatilhos visuais de escassez e order bumps no checkout para elevar o AOV em pelo menos 25%.
PROMPT;
    }

    public function getOptimizationGuidance(array $metrics): string
    {
        return "Monitore o custo de aquisição (CAC). Se o ROAS estiver abaixo de 2.0x, teste novos ângulos visuais de topo de funil.";
    }
}
