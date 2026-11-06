<?php

namespace App\Console\Commands;

use App\Models\User;
use App\Services\UserOnboardingService;
use Illuminate\Console\Command;

class ProvisionStarterKitsCommand extends Command
{
    protected $signature = 'abvos:provision-starter-kits {--user-id= : ID do usuário específico} {--force : Força o provisionamento mesmo se já tiver negócios}';

    protected $description = 'Provisiona o Starter Kit executivo de demonstração com dados de TikTok Shop e ROI para usuários.';

    public function handle(UserOnboardingService $onboardingService): int
    {
        $userId = $this->option('user-id');
        $force = (bool) $this->option('force');

        $query = User::query();
        if ($userId) {
            $query->where('id', $userId);
        }

        $users = $query->get();

        if ($users->isEmpty()) {
            $this->warn('Nenhum usuário encontrado.');
            return self::SUCCESS;
        }

        $provisionedCount = 0;
        foreach ($users as $user) {
            $businessCount = $user->businesses()->count();

            if ($businessCount > 0 && ! $force) {
                $this->line("Usuário #{$user->id} ({$user->email}) já possui {$businessCount} negócio(s). Pulando.");
                continue;
            }

            $this->info("Provisionando Starter Kit para #{$user->id} ({$user->email})...");
            try {
                $biz = $onboardingService->provisionStarterKit($user);
                $this->info(" -> Criado negócio \"{$biz->name}\" com tarefas, criativos de ROI e aprovações.");
                $provisionedCount++;
            } catch (\Throwable $e) {
                $this->error(" -> Erro ao provisionar para #{$user->id}: {$e->getMessage()}");
            }
        }

        $this->info("Concluído! {$provisionedCount} usuário(s) provisionado(s) com sucesso.");

        return self::SUCCESS;
    }
}
