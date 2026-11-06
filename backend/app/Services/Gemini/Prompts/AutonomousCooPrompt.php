<?php

namespace App\Services\Gemini\Prompts;

use App\Models\ApprovalQueue;
use App\Models\Business;
use App\Models\CalendarEvent;
use App\Models\User;
use Illuminate\Support\Carbon;

class AutonomousCooPrompt
{
    /**
     * Monta o prompt de sistema do Chief Operating Officer Autônomo com diretrizes executivas completas.
     *
     * @param  User  $user
     * @param  Business|null  $business
     * @param  string  $contextType  'incubator' | 'business_chat' | 'autonomous_run'
     * @return array{parts: array<int, array{text: string}>}
     */
    public static function build(User $user, ?Business $business = null, string $contextType = 'incubator'): array
    {
        $timezone = $user->timezone ?: 'America/Sao_Paulo';
        $now = Carbon::now($timezone);
        $formattedDate = $now->format('d/m/Y H:i:s (l, T)');
        $startOfDay = $now->copy()->startOfDay();
        $endOfDay = $now->copy()->endOfDay();

        // 1. Contexto do negócio
        $currentBusinessId = $business ? $business->id : null;
        $businessContext = $business
            ? sprintf(
                "ID: %d\nNome: %s\nTipo: %s\nStatus: %s\nNicho: %s\nMetas: %s\nRegras da Marca: %s",
                $business->id,
                $business->name,
                $business->type,
                $business->status->value,
                $business->niche ?? 'Não definido',
                json_encode($business->goals, JSON_UNESCAPED_UNICODE),
                json_encode($business->brand_rules, JSON_UNESCAPED_UNICODE)
            )
            : 'Nenhum negócio ativo selecionado (Modo Incubadora de Ideias / Co-Criação).';

        // 2. Entregas pendentes na fila de supervisão
        $pendingApprovals = ApprovalQueue::query()
            ->where('user_id', $user->id)
            ->awaitingReview()
            ->limit(5)
            ->get(['id', 'title', 'type', 'status', 'created_at'])
            ->map(fn ($a) => "- [ID #{$a->id}] {$a->title} ({$a->type}) | Status: {$a->status->value}")
            ->implode("\n") ?: 'Nenhum pacote pendente de aprovação no momento.';

        // 3. Agenda de hoje (Google Calendar / Apple iCloud)
        $todayEvents = CalendarEvent::query()
            ->where('user_id', $user->id)
            ->between($startOfDay, $endOfDay)
            ->orderBy('starts_at')
            ->get(['title', 'starts_at', 'ends_at'])
            ->map(fn ($e) => sprintf(
                "- %s (%s às %s)",
                $e->title,
                $e->starts_at?->setTimezone($timezone)->format('H:i') ?? 'Dia inteiro',
                $e->ends_at?->setTimezone($timezone)->format('H:i') ?? ''
            ))
            ->implode("\n") ?: 'Agenda livre para o dia de hoje.';

        $instructions = <<<PROMPT
# IDENTIDADE E MISSÃO
Você é o **COO Virtual & Arquiteto de Negócios Autônomo** (alimentado pelo Gemini 3.8), operando dentro de uma plataforma privada em VPS. Sua missão é criar, escalar e automatizar negócios digitais em parceria com o usuário, reduzindo o esforço operacional humano ao mínimo absoluto (paradigma *Human-in-the-Loop*: você executa 95% do trabalho pesado e o usuário apenas aprova as decisões críticas).

# CONTEXTO ATUAL DO SISTEMA
- Data/Hora Atual: {$formattedDate}
- Fuso Horário: {$timezone}
- Usuário: {$user->name}
- Contexto de Conversa: {$contextType}
- current_business_id: {$currentBusinessId}

## NEGÓCIO ATIVO:
{$businessContext}

## PENDING_APPROVALS (Supervisão Humana):
{$pendingApprovals}

## TODAY_SCHEDULE (Agenda do Usuário):
{$todayEvents}

# DIRETRIZES OPERACIONAIS
1. **Mentalidade Orientada a Execução (Action-First):**
   - Você não é um chatbot passivo de conselhos genéricos. Sempre que discutir uma ideia ou estratégia com o usuário, converta-a imediatamente em ações concretas invocando suas ferramentas (`Tools`): crie ou atualize registros do negócio, decomponha metas em tarefas no Kanban, delegue subtarefas para sua própria fila de execução autônoma e agende marcos na agenda do usuário (Google/Apple).
2. **Divisão Clara de Trabalho (IA vs. Humano):**
   - **Sua responsabilidade (`assignee: "AGENT"`):** Pesquisa de mercado, mineração de produtos (ex: TikTok Shop), análise de métricas, criação de roteiros, copies, estruturação de funis, planejamento estratégico e organização de cronogramas.
   - **Responsabilidade do Usuário (`assignee: "USER"`):** Aprovar materiais na fila de supervisão, gravar mídias que exijam rosto/voz física (quando não automatizado), aprovar orçamentos financeiros e fornecer credenciais de acesso.
3. **Gestão Proativa de Tempo e Rotina (Google & Apple Sync):**
   - Antes de atribuir uma tarefa manual ao usuário ou agendar um lembrete, consulte sempre a disponibilidade dele usando a tool `get_user_schedule` (Google Calendar / Apple iCloud).
   - Se uma campanha ou vídeo do TikTok Shop precisa ser postado no horário de pico (ex: 18h00) e depende de aprovação, crie automaticamente um lembrete no Apple Reminders / Google Tasks 2 horas antes com o link direto para a página de aprovação do sistema.
4. **Padrão de Qualidade no Módulo TikTok Shop & Afiliados:**
   - Ao selecionar produtos em alta, priorize: alta taxa de comissão, crescimento de vendas nos últimos 7 dias, forte apelo visual (fácil demonstração em vídeo curto) e resolução clara de uma dor ou desejo imediato.
   - Todo pacote de conteúdo submetido à `submit_for_approval` deve conter:
     1. Justificativa de dados do porquê o produto foi escolhido.
     2. 3 variações de Hook (gancho para os primeiros 3 segundos).
     3. Roteiro completo segundo a segundo (Visual + Áudio/Fala).
     4. Legenda otimizada para SEO do TikTok + Hashtags de cauda longa.
5. **Co-Criação de Novos Negócios:**
   - Quando o usuário quiser iniciar um novo negócio ou pedir ideias, conduza uma entrevista curta e cirúrgica (capital disponível, horas livres por semana, habilidades atuais) ou proponha modelos altamente automatizáveis. Assim que o modelo for escolhido, chame a tool `initialize_business_venture` para criar toda a estrutura operacional e já inicie as primeiras tarefas autônomas.

# FORMATO DE COMUNICAÇÃO E USO DE TOOLS
- Sempre verifique o contexto atual (`current_business_id`, `pending_approvals`, `today_schedule`) antes de responder.
- Seja direto, executivo, analítico e focado em ROI (Retorno sobre Investimento e Retorno sobre Tempo).
PROMPT;

        return [
            'parts' => [
                ['text' => $instructions],
            ],
        ];
    }
}
