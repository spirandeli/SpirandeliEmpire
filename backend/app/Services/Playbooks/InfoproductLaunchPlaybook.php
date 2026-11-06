<?php

namespace App\Services\Playbooks;

use App\Models\Business;
use App\Services\Playbooks\Contracts\BusinessPlaybookInterface;

class InfoproductLaunchPlaybook implements BusinessPlaybookInterface
{
    public function getArchetypeName(): string
    {
        return Business::ARCHETYPE_INFOPRODUCT;
    }

    public function getDisplayName(): string
    {
        return 'Infoprodutos & Lançamentos Digitais';
    }

    public function getRecommendedNorthStarMetric(): string
    {
        return 'roas';
    }

    public function getFunnelStages(): array
    {
        return [
            'tof_attraction' => 'Isca Digital / Conteúdo Educacional de Alto Valor',
            'mof_conversion' => 'VSL / Aula Magna / Quebra de Crenças Limitantes',
            'bof_retention' => 'Abertura de Carrinho, Garantia Incondicional & Bônus',
        ];
    }

    public function getAngles(): array
    {
        return [
            'mecanismo_unico' => 'Apresentação do método exclusivo que elimina a causa raiz do problema',
            'estudo_de_caso' => 'História real de um aluno comum que atingiu o resultado em X dias',
            'quebra_de_objecao' => 'Desmontando por que outras tentativas anteriores falharam',
            'segredo_revelado' => '"O que os gurus nunca te contam sobre..."',
            'urgencia_vagas' => 'Contagem regressiva de encerramento da turma com suporte',
        ];
    }

    public function getSystemPromptExtension(): string
    {
        return <<<PROMPT
# PLAYBOOK ATIVO: INFOPRODUTOS & LANÇAMENTOS (ARQUÉTIPO DIRETO AO PONTO)
- Foco em ROAS, Custo por Lead (CPL) e Recuperação Imediata de Carrinho Abandonado / PIX.
- Toda estratégia deve estruturar:
  1. Promessa ousada porém crível (Big Idea + Mecanismo Único).
  2. Estrutura de VSL com Hook nos primeiros 15s, História de Origem, Revelação do Método e Empilhamento de Oferta Irresistível.
  3. Sequência de e-mails/WhatsApp de urgência para as últimas 24 horas de carrinho aberto.
PROMPT;
    }

    public function getOptimizationGuidance(array $metrics): string
    {
        $abandoned = $metrics['abandoned_checkouts'] ?? 0;
        $sales = $metrics['total_sales'] ?? 0;
        if ($abandoned > $sales) {
            return "Mais abandono de carrinho ({$abandoned}) do que vendas pagas ({$sales}). Recomenda-se disparar copy de recuperação por WhatsApp oferecendo suporte a dúvidas e parcelamento inteligente.";
        }
        return "Funil com boa absorção. Escalar investimento nos anúncios de topo de funil com maior CTR.";
    }
}
