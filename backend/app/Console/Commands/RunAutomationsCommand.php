<?php

namespace App\Console\Commands;

use App\Jobs\GenerateAffiliateContentJob;
use App\Jobs\SyncAppleCalDavJob;
use App\Jobs\SyncGoogleCalendarJob;
use App\Jobs\TikTokShopMinerJob;
use App\Models\BusinessAutomation;
use App\Models\TikTokProduct;
use Illuminate\Console\Command;

class RunAutomationsCommand extends Command
{
    protected $signature = 'abvos:run-automations {--force : Executa mesmo se a automação não estiver devida}';
    protected $description = 'Varre e despacha todas as automações de negócios digitais devidas no momento';

    public function handle(): int
    {
        $query = BusinessAutomation::query()
            ->with(['business.user'])
            ->whereHas('business', fn ($q) => $q->where('status', 'active')->where('automation_enabled', true))
            ->whereHas('business.user', fn ($q) => $q->where('agent_enabled', true));

        if (! $this->option('force')) {
            $query->due();
        } else {
            $query->where('is_enabled', true);
        }

        $automations = $query->get();

        if ($automations->isEmpty()) {
            $this->info('Nenhuma automação devida para execução no momento.');
            return 0;
        }

        $this->info("Encontrada(s) {$automations->count()} automação(ões) para disparo.");

        foreach ($automations as $automation) {
            $business = $automation->business;
            $this->line("-> Disparando: [{$automation->type}] {$automation->name} (Negócio #{$business->id}: {$business->name})");

            match ($automation->type) {
                BusinessAutomation::TYPE_TIKTOK_MINING => TikTokShopMinerJob::dispatch($business),
                BusinessAutomation::TYPE_CONTENT_GENERATION => $this->dispatchContentGeneration($business),
                BusinessAutomation::TYPE_CALENDAR_SYNC => $this->dispatchCalendarSync($business),
                default => $this->warn("Tipo de automação não mapeado: {$automation->type}"),
            };

            // Atualiza next_run_at para evitar disparos em duplicidade no próximo minuto
            $automation->forceFill([
                'last_run_at' => now(),
                'next_run_at' => $automation->computeNextRun(),
            ])->save();
        }

        $this->info('Todas as automações devidas foram despachadas para as filas do worker.');
        return 0;
    }

    private function dispatchContentGeneration($business): void
    {
        // Pega o produto minerado com maior score geral que ainda não tenha conteúdo pronto
        $product = TikTokProduct::query()
            ->where('business_id', $business->id)
            ->whereIn('status', [TikTokProduct::STATUS_SELECTED, TikTokProduct::STATUS_MINED])
            ->orderByDesc('overall_score')
            ->first();

        if ($product) {
            GenerateAffiliateContentJob::dispatch($business, $product);
        } else {
            // Se não houver produto aguardando conteúdo, dispara a mineração primeiro
            TikTokShopMinerJob::dispatch($business, ['auto_generate_content_limit' => 1]);
        }
    }

    private function dispatchCalendarSync($business): void
    {
        SyncGoogleCalendarJob::dispatch($business->user);
        SyncAppleCalDavJob::dispatch($business->user);
    }
}

