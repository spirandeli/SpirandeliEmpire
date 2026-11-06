<?php

namespace App\Services\Playbooks;

use App\Models\Business;
use App\Services\Playbooks\Contracts\BusinessPlaybookInterface;

class AffiliateTikTokPlaybook implements BusinessPlaybookInterface
{
    public function getArchetypeName(): string
    {
        return Business::ARCHETYPE_AFFILIATE_TIKTOK;
    }

    public function getDisplayName(): string
    {
        return 'Afiliados & TikTok Shop Viral';
    }

    public function getRecommendedNorthStarMetric(): string
    {
        return 'commission_volume';
    }

    public function getFunnelStages(): array
    {
        return [
            'tof_attraction' => 'Gancho Viral / Demonstração Hipnótica (0-3s)',
            'mof_conversion' => 'Quebra de Ceticismo & Benefício Prático (3-20s)',
            'bof_retention' => 'Chamada com Cupom / Carrinho Laranja (20-30s)',
        ];
    }

    public function getAngles(): array
    {
        return [
            'curiosidade' => 'Revelação de produto desconhecido que resolve problema comum',
            'dor_direta' => 'Apresentação agressiva de um incômodo diário e alívio imediato',
            'prova_social' => '"Por que todo mundo no TikTok está comprando isso?"',
            'contraintuitivo' => 'Dizer que o método convencional está errado e apresentar o produto',
            'transformacao_antes_depois' => 'Contraste visual chocante em menos de 2 segundos',
            'humor_situacional' => 'Situação cômica relacionável resolvida pelo item',
        ];
    }

    public function getSystemPromptExtension(): string
    {
        return <<<PROMPT
# PLAYBOOK ATIVO: AFILIADOS & TIKTOK SHOP (ARQUÉTIPO VIRAL)
- Foco absoluto em GMV, taxa de retenção nos primeiros 3 segundos e comissão por pedido.
- Toda sugestão criativa DEVE conter:
  1. Gancho de padrão quebrado (Visual Hook) de 0 a 3s sem introduções lentas.
  2. Apresentação do produto em uso contínuo (UGC style, gravado com câmera de celular).
  3. Chamada de Ação (CTA) clara apontando para o botão da vitrine ("clique na sacola aqui embaixo antes que acabe o lote").
- Identifique ângulos com alto ROI score e descarte criativos sem vendas após 100 cliques.
PROMPT;
    }

    public function getOptimizationGuidance(array $metrics): string
    {
        $cvr = $metrics['conversion_rate'] ?? 0;
        if ($cvr < 1.5) {
            return "Taxa de conversão baixa ({$cvr}%). Recomenda-se trocar o CTA final e enfatizar a escassez de estoque ou cupom de frete grátis.";
        }
        return "Taxa de conversão saudável ({$cvr}%). Recomenda-se criar variações de Hooks para os 3 primeiros segundos para escalar o volume de visualizações.";
    }
}
