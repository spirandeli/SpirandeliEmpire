<?php

namespace App\Jobs;

use App\Enums\LogLevel;
use App\Models\AgentLog;
use App\Models\Business;
use App\Models\BusinessAutomation;
use App\Services\TikTokShopService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldBeUnique;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;

class TikTokShopMinerJob implements ShouldQueue, ShouldBeUnique
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 3;
    public int $timeout = 180;
    public array $backoff = [15, 45, 120];
    public int $uniqueFor = 300;

    public function __construct(
        public readonly Business $business,
        public readonly array $overrideConfig = []
    ) {
        $this->onQueue('tiktok');
    }

    public function uniqueId(): string
    {
        return 'miner_biz_' . $this->business->id;
    }

    public function handle(TikTokShopService $tikTokService): void
    {
        $user = $this->business->user;

        // Se o negócio foi desativado ou pausado pelo usuário, ignora a execução
        if (! $this->business->automation_enabled || $this->business->status->value !== 'active') {
            return;
        }

        // Se o usuário desativou o kill-switch global do agente
        if (! $user->agent_enabled) {
            return;
        }

        // Governança FinOps: Bloqueio Preventivo se IA inativa ou limite de tokens atingido
        if (! $user->isAiActive() || $user->hasExceededMonthlyTokenLimit()) {
            Log::info('TikTokShopMinerJob cancelado preventivamente: usuário sem cota ou com IA pausada pelo admin.', [
                'user_id' => $user->id,
                'business_id' => $this->business->id,
            ]);
            return;
        }

        $automation = $this->business->automations()
            ->where('type', BusinessAutomation::TYPE_TIKTOK_MINING)
            ->first();

        $config = array_merge($automation?->config ?? [], $this->overrideConfig);

        try {
            $automation?->markRunning();

            $products = $tikTokService->mineTrendingProducts($this->business, $config);

            $maxContent = (int) ($config['auto_generate_content_limit'] ?? 1);

            // Se a automação estiver configurada para gerar conteúdo imediatamente para os melhores
            $count = 0;
            foreach ($products as $product) {
                if ($count >= $maxContent) {
                    break;
                }

                GenerateAffiliateContentJob::dispatch($this->business, $product);
                $count++;
            }

            $automation?->markSuccess();
        } catch (\Throwable $e) {
            Log::error('Erro ao executar TikTokShopMinerJob', [
                'business_id' => $this->business->id,
                'error' => $e->getMessage(),
            ]);

            $automation?->markFailed($e->getMessage());

            throw $e;
        }
    }

    public function failed(\Throwable $e): void
    {
        Log::critical('TikTokShopMinerJob falhou definitivamente após todas as tentativas', [
            'business_id' => $this->business->id,
            'error' => $e->getMessage(),
        ]);

        AgentLog::record(
            $this->business->user_id,
            'miner_job_failed',
            "Falha definitiva na mineração de produtos para \"{$this->business->name}\": {$e->getMessage()}",
            LogLevel::Error,
            ['business_id' => $this->business->id, 'trace' => mb_substr($e->getTraceAsString(), 0, 1000)],
            ['business_id' => $this->business->id]
        );
    }
}
