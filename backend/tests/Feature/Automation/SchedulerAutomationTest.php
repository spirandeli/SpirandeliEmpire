<?php

namespace Tests\Feature\Automation;

use App\Jobs\TikTokShopMinerJob;
use App\Models\Business;
use App\Models\BusinessAutomation;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Queue;
use Tests\TestCase;

class SchedulerAutomationTest extends TestCase
{
    use RefreshDatabase;

    private User $user;
    private Business $business;

    protected function setUp(): void
    {
        parent::setUp();
        $this->user = User::factory()->create();
        $this->business = $this->user->businesses()->create([
            'name' => 'Operação TikTok Scheduler',
            'type' => 'tiktok_shop_affiliate',
            'status' => 'active',
            'automation_enabled' => true,
        ]);
    }

    public function test_run_automations_command_dispatches_due_jobs_and_recalculates_next_run(): void
    {
        Queue::fake([TikTokShopMinerJob::class]);

        $automation = $this->business->automations()->create([
            'type' => BusinessAutomation::TYPE_TIKTOK_MINING,
            'name' => 'Mineração de Produtos 6h',
            'cron_expression' => '0 */6 * * *',
            'is_enabled' => true,
        ]);
        $automation->forceFill(['next_run_at' => now()->subMinute()])->saveQuietly();

        $this->artisan('abvos:run-automations')
            ->expectsOutputToContain('Encontrada(s) 1 automação(ões) para disparo.')
            ->assertSuccessful();

        Queue::assertPushed(TikTokShopMinerJob::class, function ($job) {
            return $job->business->id === $this->business->id;
        });

        $automation->refresh();
        $this->assertNotNull($automation->last_run_at);
        $this->assertTrue($automation->next_run_at->isAfter(now()));
    }

    public function test_scheduler_ignores_disabled_automations_or_paused_businesses(): void
    {
        Queue::fake();

        // Automação desabilitada
        $this->business->automations()->create([
            'type' => BusinessAutomation::TYPE_TIKTOK_MINING,
            'name' => 'Mineração Desligada',
            'cron_expression' => '0 */6 * * *',
            'is_enabled' => false,
            'next_run_at' => now()->subMinute(),
        ]);

        // Negócio pausado
        $pausedBusiness = $this->user->businesses()->create([
            'name' => 'Pausado',
            'status' => 'paused',
            'automation_enabled' => false,
        ]);

        $pausedBusiness->automations()->create([
            'type' => BusinessAutomation::TYPE_TIKTOK_MINING,
            'name' => 'Mineração Pausada',
            'cron_expression' => '0 */6 * * *',
            'is_enabled' => true,
            'next_run_at' => now()->subMinute(),
        ]);

        $this->artisan('abvos:run-automations')
            ->expectsOutputToContain('Nenhuma automação devida para execução no momento.')
            ->assertSuccessful();

        Queue::assertNothingPushed();
    }
}
