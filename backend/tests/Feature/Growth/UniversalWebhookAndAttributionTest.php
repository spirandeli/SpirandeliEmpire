<?php

namespace Tests\Feature\Growth;

use App\Enums\BusinessStatus;
use App\Jobs\HandleFunnelRecoveryJob;
use App\Models\Business;
use App\Models\ContentAsset;
use App\Models\ConversionEvent;
use App\Models\OptimizationCycle;
use App\Models\Task;
use App\Models\User;
use App\Services\GeminiAgentService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Queue;
use Tests\TestCase;

class UniversalWebhookAndAttributionTest extends TestCase
{
    use RefreshDatabase;

    private User $user;
    private Business $business;
    private ContentAsset $asset;

    protected function setUp(): void
    {
        parent::setUp();

        $this->user = User::factory()->create(['is_ai_active' => true]);
        $this->business = Business::create([
            'user_id' => $this->user->id,
            'name' => 'TikTok Glow Store',
            'slug' => 'tiktok-glow-store',
            'type' => Business::TYPE_TIKTOK_SHOP_AFFILIATE,
            'archetype' => Business::ARCHETYPE_AFFILIATE_TIKTOK,
            'status' => BusinessStatus::Active,
            'automation_enabled' => true,
        ]);

        $this->asset = ContentAsset::create([
            'business_id' => $this->business->id,
            'tracking_code' => 'AST-8492A',
            'type' => ContentAsset::TYPE_VIDEO_SCRIPT,
            'title' => 'Vídeo Viral Iluminador LED',
            'angle_category' => 'dor_direta',
            'funnel_stage' => ContentAsset::STAGE_TOF_ATTRACTION,
            'total_views' => 1200,
            'total_clicks' => 80,
            'status' => 'approved',
        ]);
    }

    public function test_webhook_rejects_invalid_secret_token(): void
    {
        $response = $this->postJson('/api/webhooks/in/token_invalido_123', [
            'event' => 'PURCHASE_APPROVED',
        ]);

        $response->assertStatus(404)
            ->assertJsonPath('error', 'Webhook secret token inválido ou não cadastrado.');
    }

    public function test_hotmart_webhook_normalizes_and_attributes_to_content_asset(): void
    {
        $payload = [
            'event' => 'PURCHASE_APPROVED',
            'hottok' => 'hotmart_token_sec',
            'data' => [
                'purchase' => [
                    'transaction' => 'HP123456789',
                    'order_date' => 1700000000000,
                    'price' => ['value' => 197.00],
                    'commission' => ['value' => 150.00],
                    'tracking' => [
                        'source' => 'AST-8492A',
                    ],
                ],
                'buyer' => [
                    'name' => 'Carlos Silva',
                    'email' => 'carlos@example.com',
                ],
            ],
        ];

        $response = $this->postJson("/api/webhooks/in/{$this->business->webhook_secret_token}", $payload);

        $response->assertOk()
            ->assertJsonPath('status', 'success')
            ->assertJsonPath('event_type', 'sale_approved')
            ->assertJsonPath('attributed_asset_id', $this->asset->id)
            ->assertJsonPath('tracking_code', 'AST-8492A');

        $this->assertDatabaseHas('conversion_events', [
            'business_id' => $this->business->id,
            'content_asset_id' => $this->asset->id,
            'source_platform' => 'hotmart',
            'event_type' => 'sale_approved',
            'external_transaction_id' => 'HP123456789',
            'gross_amount' => 197.00,
        ]);

        $this->asset->refresh();
        $this->assertEquals(1, $this->asset->total_sales_count);
        $this->assertEquals(197.00, (float) $this->asset->total_revenue_brl);
        $this->assertGreaterThan(0, (float) $this->asset->roi_score);
    }

    public function test_kiwify_webhook_normalizes_and_converts_cents(): void
    {
        $payload = [
            'order_id' => 'kw_order_9988',
            'order_status' => 'paid',
            'Commissions' => [
                'charge_amount' => 29700, // em centavos
                'my_commission' => 25000,
            ],
            'Customer' => [
                'full_name' => 'Mariana Oliveira',
                'email' => 'mariana@example.com',
            ],
            'TrackingParameters' => [
                'src' => 'AST-8492A',
            ],
        ];

        $response = $this->postJson("/api/webhooks/in/{$this->business->webhook_secret_token}", $payload);

        $response->assertOk()
            ->assertJsonPath('gross_amount', 297);

        $this->assertDatabaseHas('conversion_events', [
            'business_id' => $this->business->id,
            'source_platform' => 'kiwify',
            'external_transaction_id' => 'kw_order_9988',
            'gross_amount' => 297.00,
        ]);
    }

    public function test_abandoned_checkout_triggers_recovery_job(): void
    {
        Queue::fake([HandleFunnelRecoveryJob::class]);

        $payload = [
            'order_id' => 'kw_abandoned_55',
            'order_status' => 'waiting_payment',
            'payment_method' => 'pix',
            'Commissions' => [
                'charge_amount' => 97.00,
            ],
            'Customer' => [
                'full_name' => 'Roberto Carlos',
                'email' => 'roberto@example.com',
            ],
            'TrackingParameters' => [
                'src' => 'AST-8492A',
            ],
        ];

        $this->postJson("/api/webhooks/in/{$this->business->webhook_secret_token}", $payload)
            ->assertOk();

        Queue::assertPushed(HandleFunnelRecoveryJob::class);
    }

    public function test_handle_funnel_recovery_job_creates_urgent_kanban_task(): void
    {
        $event = ConversionEvent::create([
            'business_id' => $this->business->id,
            'content_asset_id' => $this->asset->id,
            'source_platform' => 'kiwify',
            'event_type' => ConversionEvent::EVENT_PIX_GENERATED,
            'external_transaction_id' => 'tx_pix_44',
            'gross_amount' => 197.00,
            'net_amount' => 170.00,
            'customer_metadata' => ['name' => 'Juliana Costa', 'email' => 'juliana@test.com'],
            'payload_raw' => [],
            'occurred_at' => now(),
        ]);

        $job = new HandleFunnelRecoveryJob($event);
        $job->handle();

        $this->assertDatabaseHas('tasks', [
            'business_id' => $this->business->id,
            'priority' => 'urgent',
        ]);

        $task = Task::where('business_id', $this->business->id)->latest('id')->first();
        $this->assertStringContainsString('Juliana Costa', $task->title);
    }

    public function test_growth_metrics_endpoint_returns_aggregated_funnel(): void
    {
        $this->actingAs($this->user, 'sanctum');

        ConversionEvent::create([
            'business_id' => $this->business->id,
            'content_asset_id' => $this->asset->id,
            'source_platform' => 'hotmart',
            'event_type' => ConversionEvent::EVENT_SALE_APPROVED,
            'external_transaction_id' => 'tx_metric_1',
            'gross_amount' => 250.00,
            'occurred_at' => now(),
        ]);

        $response = $this->getJson("/api/businesses/{$this->business->id}/growth-metrics");

        $response->assertOk()
            ->assertJsonPath('funnel.total_sales', 1)
            ->assertJsonPath('funnel.total_revenue', 250)
            ->assertJsonPath('business.archetype', 'affiliate_tiktok');
    }

    public function test_optimize_growth_command_runs_ooda_cycle(): void
    {
        // Garante que o ativo tenha métricas vencedoras
        $this->asset->update([
            'total_sales_count' => 10,
            'total_revenue_brl' => 1500.00,
            'roi_score' => 85.00,
        ]);

        ConversionEvent::create([
            'business_id' => $this->business->id,
            'content_asset_id' => $this->asset->id,
            'source_platform' => 'tiktok_shop',
            'event_type' => ConversionEvent::EVENT_CHECKOUT_ABANDONED,
            'external_transaction_id' => 'ab_1',
            'gross_amount' => 99.00,
            'occurred_at' => now(),
        ]);

        $this->artisan('abvos:optimize-growth', ['business_id' => $this->business->id])
            ->assertSuccessful();

        // Verifica se o ciclo OODA foi registrado
        $this->assertDatabaseHas('optimization_cycles', [
            'business_id' => $this->business->id,
        ]);

        // Verifica se novas variações foram criadas para o vencedor
        $this->assertDatabaseHas('content_assets', [
            'business_id' => $this->business->id,
            'parent_id' => $this->asset->id,
        ]);

        // Verifica se o aprendizado foi registrado
        $this->assertDatabaseHas('agent_learnings', [
            'business_id' => $this->business->id,
        ]);
    }
}
