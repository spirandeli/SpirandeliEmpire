<?php

namespace App\Services;

use App\Enums\ApprovalStatus;
use App\Enums\LogLevel;
use App\Enums\TaskStatus;
use App\Events\ApprovalApproved;
use App\Events\ApprovalRejected;
use App\Events\ApprovalRevisionRequested;
use App\Events\ApprovalSubmitted;
use App\Exceptions\StateTransitionException;
use App\Models\AgentLog;
use App\Models\ApprovalQueue;
use App\Models\Business;
use App\Models\ContentAsset;
use App\Models\Task;
use App\Models\TikTokProduct;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\ValidationException;

/**
 * Fluxo Human-in-the-Loop: submissão pelo agente e decisão do usuário
 * (aprovar / ajustar / descartar). Usado pelos controllers e pela tool `submitForHumanApproval`.
 */
class ApprovalService
{
    // --- Entrada do agente --------------------------------------------------------

    /**
     * @param  array{type?:string,title:string,summary?:string,payload:array,priority?:string,agent_confidence?:float,task_id?:int,approvable_type?:string,approvable_id?:int,expires_in_hours?:int}  $data
     */
    public function submit(Business $business, array $data): ApprovalQueue
    {
        $type = $data['type'] ?? ApprovalQueue::TYPE_GENERIC;
        $this->validatePayload($type, $data['payload'] ?? []);

        $approval = DB::transaction(function () use ($business, $data, $type) {
            $task = null;
            if (! empty($data['task_id'])) {
                $task = Task::where('business_id', $business->id)->findOrFail($data['task_id']);
            }

            $approval = ApprovalQueue::create([
                'business_id' => $business->id,
                'user_id' => $business->user_id,
                'task_id' => $task?->id,
                'approvable_type' => $data['approvable_type'] ?? null,
                'approvable_id' => $data['approvable_id'] ?? null,
                'type' => $type,
                'title' => $data['title'],
                'summary' => $data['summary'] ?? null,
                'payload' => $data['payload'],
                'status' => ApprovalStatus::Pending,
                'priority' => $data['priority'] ?? 'medium',
                'agent_confidence' => $data['agent_confidence'] ?? null,
                'expires_at' => now()->addHours($data['expires_in_hours'] ?? config('abvos.approval_default_expiry_hours')),
            ]);

            $task?->moveTo(TaskStatus::AwaitingSupervision);

            AgentLog::record($business->user_id, 'approval_submitted', "Entrega \"{$approval->title}\" aguardando sua supervisão.",
                LogLevel::Success, ['approval_id' => $approval->id, 'type' => $type],
                ['business_id' => $business->id, 'task_id' => $task?->id]);

            return $approval;
        });

        ApprovalSubmitted::dispatch($approval);

        return $approval;
    }

    // --- Decisões do usuário --------------------------------------------------------

    public function approve(ApprovalQueue $approval, ?Carbon $scheduledFor = null, ?int $selectedHookIndex = null): ApprovalQueue
    {
        $approval = DB::transaction(function () use ($approval, $scheduledFor, $selectedHookIndex) {
            $approval = $this->lockReviewable($approval);

            $payload = $approval->payload;
            if ($selectedHookIndex !== null) {
                $hooks = $payload['hooks'] ?? [];
                if (! isset($hooks[$selectedHookIndex])) {
                    throw ValidationException::withMessages(['selected_hook_index' => 'Hook inexistente neste pacote.']);
                }
                $payload['selected_hook_index'] = $selectedHookIndex;
                $this->markSelectedHook($approval, $selectedHookIndex);
            }

            $approval->forceFill([
                'payload' => $payload,
                'status' => $scheduledFor ? ApprovalStatus::Scheduled : ApprovalStatus::Approved,
                'scheduled_for' => $scheduledFor,
                'reviewed_at' => now(),
            ])->save();

            $approval->contentAssets()->where('status', 'pending_approval')->update([
                'status' => 'approved',
                'scheduled_at' => $scheduledFor,
            ]);

            $this->closeTask($approval, 'approved');

            AgentLog::record($approval->user_id, 'approval_approved', "Você aprovou \"{$approval->title}\".",
                LogLevel::Success, ['approval_id' => $approval->id, 'scheduled_for' => $scheduledFor?->toIso8601String()],
                ['business_id' => $approval->business_id, 'task_id' => $approval->task_id]);

            return $approval;
        });

        ApprovalApproved::dispatch($approval);

        return $approval;
    }

    public function reject(ApprovalQueue $approval, ?string $reason = null, bool $discardProduct = false): ApprovalQueue
    {
        $approval = DB::transaction(function () use ($approval, $reason, $discardProduct) {
            $approval = $this->lockReviewable($approval);

            $approval->forceFill([
                'status' => ApprovalStatus::Rejected,
                'reviewer_feedback' => $reason,
                'reviewed_at' => now(),
            ])->save();

            $approval->contentAssets()->whereIn('status', ['pending_approval', 'draft'])->update(['status' => 'rejected']);

            if ($discardProduct && $approval->approvable instanceof TikTokProduct) {
                $approval->approvable->update(['status' => TikTokProduct::STATUS_DISCARDED]);
            }

            $this->closeTask($approval, 'rejected', $reason);

            AgentLog::record($approval->user_id, 'approval_rejected', "Você descartou \"{$approval->title}\".",
                LogLevel::Warning, ['approval_id' => $approval->id, 'reason' => $reason],
                ['business_id' => $approval->business_id, 'task_id' => $approval->task_id]);

            return $approval;
        });

        ApprovalRejected::dispatch($approval);

        return $approval;
    }

    /** Pede ajuste: o agente reescreve só a seção indicada (listener da Fase 3). */
    public function requestRevision(ApprovalQueue $approval, string $feedback, ?string $section = null): ApprovalQueue
    {
        $approval = DB::transaction(function () use ($approval, $feedback, $section) {
            $approval = $this->lockReviewable($approval);

            $approval->appendRevisionEntry($feedback, $section);
            $approval->forceFill(['status' => ApprovalStatus::RevisionRequested, 'reviewed_at' => now()])->save();

            AgentLog::record($approval->user_id, 'approval_revision_requested', "Ajuste solicitado em \"{$approval->title}\".",
                LogLevel::Info, ['approval_id' => $approval->id, 'section' => $section, 'feedback' => $feedback],
                ['business_id' => $approval->business_id, 'task_id' => $approval->task_id]);

            return $approval;
        });

        ApprovalRevisionRequested::dispatch($approval, $feedback, $section);

        return $approval;
    }

    // --- Ciclo de revisão (chamado pelo agente) ---------------------------------------

    /** O worker começou a reescrever o pacote. */
    public function markRevising(ApprovalQueue $approval): ApprovalQueue
    {
        if ($approval->status !== ApprovalStatus::RevisionRequested) {
            throw new StateTransitionException('Este item não está aguardando revisão do agente.');
        }

        $approval->forceFill(['status' => ApprovalStatus::Revising])->save();
        $approval->task?->moveTo(TaskStatus::InProgressAgent);

        return $approval;
    }

    /** O agente entregou a versão revisada: volta para a Inbox como `pending`. */
    public function completeRevision(ApprovalQueue $approval, array $newPayload, ?string $summary = null): ApprovalQueue
    {
        if (! in_array($approval->status, [ApprovalStatus::RevisionRequested, ApprovalStatus::Revising], true)) {
            throw new StateTransitionException('Este item não está em revisão.');
        }

        $this->validatePayload($approval->type, $newPayload);

        DB::transaction(function () use ($approval, $newPayload, $summary) {
            $approval->forceFill([
                'payload' => $newPayload,
                'summary' => $summary ?? $approval->summary,
                'status' => ApprovalStatus::Pending,
            ])->save();

            $approval->task?->moveTo(TaskStatus::AwaitingSupervision);

            AgentLog::record($approval->user_id, 'approval_revised', "Nova versão de \"{$approval->title}\" pronta para revisão.",
                LogLevel::Success, ['approval_id' => $approval->id, 'revision' => $approval->revision_count],
                ['business_id' => $approval->business_id, 'task_id' => $approval->task_id]);
        });

        return $approval->refresh();
    }

    // --- Utilidades ----------------------------------------------------------------------

    /** @return array{pending:int, revision:int, total_awaiting:int} */
    public function summaryFor(int $userId): array
    {
        $counts = ApprovalQueue::query()
            ->where('user_id', $userId)
            ->awaitingReview()
            ->selectRaw('status, count(*) as total')
            ->groupBy('status')
            ->pluck('total', 'status');

        $pending = (int) ($counts[ApprovalStatus::Pending->value] ?? 0);
        $revision = (int) ($counts[ApprovalStatus::RevisionRequested->value] ?? 0);

        return ['pending' => $pending, 'revision' => $revision, 'total_awaiting' => $pending + $revision];
    }

    private function lockReviewable(ApprovalQueue $approval): ApprovalQueue
    {
        /** @var ApprovalQueue $locked */
        $locked = ApprovalQueue::query()->lockForUpdate()->findOrFail($approval->id);

        if (! $locked->isReviewable()) {
            throw new StateTransitionException("Este item já foi tratado (status: {$locked->status->value}).");
        }

        return $locked;
    }

    private function closeTask(ApprovalQueue $approval, string $outcome, ?string $reason = null): void
    {
        $task = $approval->task;
        if (! $task) {
            return;
        }

        $task->forceFill([
            'result' => array_merge($task->result ?? [], [
                'approval_id' => $approval->id,
                'outcome' => $outcome,
                'reason' => $reason,
            ]),
        ])->save();
        $task->moveTo(TaskStatus::Done);
    }

    /** Convenção da Fase 5: assets do tipo `hook` guardam `content.index`. */
    private function markSelectedHook(ApprovalQueue $approval, int $index): void
    {
        $approval->contentAssets()->where('type', ContentAsset::TYPE_HOOK)->get()
            ->each(fn (ContentAsset $asset) => $asset->update([
                'is_selected' => (int) data_get($asset->content, 'index') === $index,
            ]));
    }

    /** Estrutura mínima do pacote TikTok (também protege contra saídas malformadas do LLM). */
    private function validatePayload(string $type, array $payload): void
    {
        if ($payload === []) {
            throw ValidationException::withMessages(['payload' => 'O payload da entrega não pode ser vazio.']);
        }

        if ($type !== ApprovalQueue::TYPE_TIKTOK_CONTENT_PACKAGE) {
            return;
        }

        $errors = [];
        if (! is_array($payload['hooks'] ?? null) || count($payload['hooks']) < 1) {
            $errors['payload.hooks'] = 'O pacote precisa de ao menos 1 hook (o padrão são 3).';
        }
        foreach (['script', 'caption'] as $key) {
            if (! is_string($payload[$key] ?? null) && ! is_array($payload[$key] ?? null) || empty($payload[$key])) {
                $errors["payload.{$key}"] = "O campo {$key} é obrigatório.";
            }
        }
        if (! is_array($payload['hashtags'] ?? null) || $payload['hashtags'] === []) {
            $errors['payload.hashtags'] = 'Informe as hashtags.';
        }
        if (! is_array($payload['visual_prompts'] ?? null) || $payload['visual_prompts'] === []) {
            $errors['payload.visual_prompts'] = 'Informe os prompts visuais.';
        }

        if ($errors) {
            throw ValidationException::withMessages($errors);
        }
    }
}

