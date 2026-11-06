<?php

namespace App\Jobs;

use App\Enums\LogLevel;
use App\Models\AgentLog;
use App\Models\Business;
use App\Models\BusinessAutomation;
use App\Models\TikTokProduct;
use App\Services\TikTokShopService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldBeUnique;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;

class GenerateAffiliateContentJob implements ShouldQueue, ShouldBeUnique
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 3;
    public int $timeout = 240;
    public array $backoff = [15, 60, 180];
    public int $uniqueFor = 300;

    public function __construct(
        public readonly Business $business,
        public readonly TikTokProduct $product,
    ) {
        $this->onQueue('tiktok');
    }

    public function uniqueId(): string
    {
        return 'gen_content_prod_' . $this->product->id;
    }

    public function handle(TikTokShopService $tikTokService): void
    {
        $user = $this->business->user;

        if (! $this->business->automation_enabled || $this->business->status->value !== 'active') {
            return;
        }

        if (! $user->agent_enabled) {
            return;
        }

        // Governança FinOps: Bloqueio Preventivo se IA inativa ou limite de tokens atingido
        if (! $user->isAiActive() || $user->hasExceededMonthlyTokenLimit()) {
            Log::info('GenerateAffiliateContentJob cancelado preventivamente: usuário sem cota ou com IA pausada pelo admin.', [
                'user_id' => $user->id,
                'product_id' => $this->product->id,
            ]);
            return;
        }

        $automation = $this->business->automations()
            ->where('type', BusinessAutomation::TYPE_CONTENT_GENERATION)
            ->first();

        try {
            $automation?->markRunning();

            $tikTokService->generateAffiliateContentPackage($this->business, $this->product);

            $automation?->markSuccess();
        } catch (\Throwable $e) {
            Log::error('Erro ao executar GenerateAffiliateContentJob', [
                'business_id' => $this->business->id,
                'product_id' => $this->product->id,
                'error' => $e->getMessage(),
            ]);

            $automation?->markFailed($e->getMessage());

            throw $e;
        }
    }

    public function failed(\Throwable $e): void
    {
        Log::critical('GenerateAffiliateContentJob falhou definitivamente após todas as tentativas', [
            'business_id' => $this->business->id,
            'product_id' => $this->product->id,
            'error' => $e->getMessage(),
        ]);

        AgentLog::record(
            $this->business->user_id,
            'content_generation_failed',
            "Falha definitiva ao gerar roteiro para o produto \"{$this->product->title}\": {$e->getMessage()}",
            LogLevel::Error,
            ['business_id' => $this->business->id, 'product_id' => $this->product->id],
            ['business_id' => $this->business->id]
        );
    }
}
