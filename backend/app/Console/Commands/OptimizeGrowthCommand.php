<?php

namespace App\Console\Commands;

use App\Jobs\AutonomousGrowthOptimizerJob;
use App\Models\Business;
use Illuminate\Console\Command;

class OptimizeGrowthCommand extends Command
{
    protected $signature = 'abvos:optimize-growth {business_id? : ID específico do negócio para otimização}';

    protected $description = 'Dispara o ciclo OODA de auto-otimização de ROI e escala autônoma pelo Gemini 3.8';

    public function handle(): int
    {
        $businessId = $this->argument('business_id');

        if ($businessId) {
            $business = Business::find($businessId);
            if (!$business) {
                $this->error("Negócio ID #{$businessId} não encontrado.");
                return self::FAILURE;
            }

            $this->info("Disparando otimização para [{$business->name}] (ID #{$business->id})...");
            AutonomousGrowthOptimizerJob::dispatchSync($business);
            $this->info("Otimização concluída com sucesso!");
            return self::SUCCESS;
        }

        $businesses = Business::autonomous()->get();
        if ($businesses->isEmpty()) {
            $this->warn("Nenhum negócio autônomo ativo encontrado.");
            return self::SUCCESS;
        }

        $this->info("Encontrados {$businesses->count()} negócios autônomos para ciclo OODA.");
        foreach ($businesses as $business) {
            $this->line("-> Otimizando [{$business->name}]...");
            AutonomousGrowthOptimizerJob::dispatch($business);
        }

        $this->info("Todos os jobs de otimização foram enfileirados!");
        return self::SUCCESS;
    }
}

