<?php

namespace App\Jobs;

use App\Enums\LogLevel;
use App\Models\AgentLog;
use App\Models\ApprovalQueue;
use App\Services\TikTokShopService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldBeUnique;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;

class ProcessApprovalRevisionJob implements ShouldQueue, ShouldBeUnique
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 2;
    public int $timeout = 180;
    public array $backoff = [10, 30];
    public int $uniqueFor = 300;

    public function __construct(
        public readonly ApprovalQueue $approval,
        public readonly string $feedback,
        public readonly ?string $section = null,
    ) {
        $this->onQueue('agent');
    }

    public function uniqueId(): string
    {
        return 'revision_item_' . $this->approval->id;
    }

    public function handle(TikTokShopService $tikTokService): void
    {
        try {
            $tikTokService->revisePackageSection(
                $this->approval,
                $this->feedback,
                $this->section
            );
        } catch (\Throwable $e) {
            Log::error('Erro ao processar revisão de entrega com o Gemini', [
                'approval_id' => $this->approval->id,
                'feedback' => $this->feedback,
                'section' => $this->section,
                'error' => $e->getMessage(),
            ]);

            throw $e;
        }
    }

    public function failed(\Throwable $e): void
    {
        Log::critical('ProcessApprovalRevisionJob falhou após tentativas', [
            'approval_id' => $this->approval->id,
            'feedback' => $this->feedback,
            'error' => $e->getMessage(),
        ]);

        AgentLog::record(
            $this->approval->business->user_id,
            'revision_job_failed',
            "Falha ao processar reescrita com a IA para a entrega \"{$this->approval->title}\": {$e->getMessage()}",
            LogLevel::Error,
            ['approval_id' => $this->approval->id],
            ['business_id' => $this->approval->business_id]
        );
    }
}
