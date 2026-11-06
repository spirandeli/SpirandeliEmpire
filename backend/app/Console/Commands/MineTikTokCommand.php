<?php

namespace App\Console\Commands;

use App\Jobs\TikTokShopMinerJob;
use App\Models\Business;
use Illuminate\Console\Command;

class MineTikTokCommand extends Command
{
    protected $signature = 'abvos:mine-tiktok {business_id : ID do negócio} {--min-score=60}';
    protected $description = 'Dispara a mineração autônoma de produtos do TikTok Shop para um negócio específico';

    public function handle(): int
    {
        $businessId = $this->argument('business_id');
        $business = Business::findOrFail($businessId);

        $this->info("Disparando mineração para o negócio: {$business->name} (ID #{$business->id})");

        TikTokShopMinerJob::dispatchSync($business, [
            'min_overall_score' => (int) $this->option('min-score'),
        ]);

        $this->info('Mineração concluída.');
        return 0;
    }
}

