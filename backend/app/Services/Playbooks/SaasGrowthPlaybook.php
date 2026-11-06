<?php

namespace App\Services\Playbooks;

use App\Models\Business;
use App\Services\Playbooks\Contracts\BusinessPlaybookInterface;

class SaasGrowthPlaybook implements BusinessPlaybookInterface
{
    public function getArchetypeName(): string
    {
        return Business::ARCHETYPE_SAAS;
    }

    public function getDisplayName(): string
    {
        return 'SaaS & Assinaturas Recorrentes';
    }

    public function getRecommendedNorthStarMetric(): string
    {
        return 'mrr';
    }

    public function getFunnelStages(): array
    {
        return [
            'tof_attraction' => 'Benchmark / Comparativo de Mercado / Artigos Técnicos',
            'mof_conversion' => 'Free Trial 7-14 dias / Demonstração Interativa da Ferramenta',
            'bof_retention' => 'Atingimento do "Momento Aha!" / Upgrade para Plano Anual',
        ];
    }

    public function getAngles(): array
    {
        return [
            'produtividade_10x' => 'Economize 15 horas semanais eliminando tarefas manuais repetitivas',
            'substituicao_de_planilhas' => 'Por que sua operação não aguenta mais planilhas confusas do Excel',
            'automacao_sem_codigo' => 'Conecte seus sistemas em 3 cliques sem depender de desenvolvedores',
            'roi_financeiro' => 'A ferramenta se paga já na primeira semana de operação',
        ];
    }

    public function getSystemPromptExtension(): string
    {
        return <<<PROMPT
# PLAYBOOK ATIVO: SAAS & SOFTWARE RECORRENTE (ARQUÉTIPO B2B/B2C)
- Foco em MRR (Receita Mensal Recorrente), Churn Rate, LTV/CAC e Taxa de Ativação do Trial.
- Cada ativo criado deve guiar o lead rapidamente para o "Momento Aha!" dentro do software.
- Reduza atrito: formulários com menos de 3 campos, login social com Google e tour interativo guiado.
PROMPT;
    }

    public function getOptimizationGuidance(array $metrics): string
    {
        return "Para negócios SaaS, priorize ativos que tragam usuários qualificados com dor latente em vez de volume genérico.";
    }
}
