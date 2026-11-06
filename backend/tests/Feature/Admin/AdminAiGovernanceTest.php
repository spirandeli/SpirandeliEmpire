<?php

namespace Tests\Feature\Admin;

use App\Exceptions\GeminiApiException;
use App\Models\AgentConversation;
use App\Models\AiUsageLog;
use App\Models\Business;
use App\Models\User;
use App\Services\GeminiAgentService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class AdminAiGovernanceTest extends TestCase
{
    use RefreshDatabase;

    private User $admin;
    private User $regularUser;

    protected function setUp(): void
    {
        parent::setUp();

        $this->admin = User::factory()->create([
            'email' => 'admin@abvos.internal',
            'is_admin' => true,
            'is_ai_active' => true,
            'monthly_token_limit' => 5000000,
            'tokens_used_this_month' => 150000,
        ]);

        $this->regularUser = User::factory()->create([
            'email' => 'user@abvos.internal',
            'is_admin' => false,
            'is_ai_active' => true,
            'monthly_token_limit' => 1000000,
            'tokens_used_this_month' => 250000,
        ]);
    }

    public function test_non_admin_cannot_access_ai_governance_stats(): void
    {
        $response = $this->actingAs($this->regularUser)
            ->getJson('/api/admin/ai-governance/stats');

        $response->assertStatus(403)
            ->assertJson([
                'error' => 'forbidden',
            ]);
    }

    public function test_guest_cannot_access_admin_routes(): void
    {
        $response = $this->getJson('/api/admin/ai-governance/stats');

        $response->assertStatus(401);
    }

    public function test_admin_can_access_ai_governance_stats_and_metrics(): void
    {
        // Cria alguns logs de consumo
        AiUsageLog::create([
            'user_id' => $this->regularUser->id,
            'model' => 'gemini-3.8',
            'context' => 'chat',
            'prompt_tokens' => 1000,
            'completion_tokens' => 500,
            'total_tokens' => 1500,
            'estimated_cost_usd' => 0.00375,
            'latency_ms' => 450,
        ]);

        $response = $this->actingAs($this->admin)
            ->getJson('/api/admin/ai-governance/stats');

        $response->assertOk()
            ->assertJsonStructure([
                'metrics' => [
                    'monthly_tokens',
                    'monthly_cost_usd',
                    'monthly_cost_brl',
                    'total_users',
                    'active_ai_users',
                    'blocked_users',
                ],
                'users',
                'by_model',
                'by_context',
                'recent_logs',
            ]);
    }

    public function test_admin_can_toggle_kill_switch_for_user(): void
    {
        $this->assertTrue($this->regularUser->is_ai_active);

        // Bloqueia IA do usuário
        $response = $this->actingAs($this->admin)
            ->postJson("/api/admin/ai-governance/users/{$this->regularUser->id}/kill-switch");

        $response->assertOk()
            ->assertJson(['is_ai_active' => false]);

        $this->assertFalse($this->regularUser->fresh()->is_ai_active);

        // Reativa
        $response = $this->actingAs($this->admin)
            ->postJson("/api/admin/ai-governance/users/{$this->regularUser->id}/kill-switch");

        $response->assertOk()
            ->assertJson(['is_ai_active' => true]);

        $this->assertTrue($this->regularUser->fresh()->is_ai_active);
    }

    public function test_admin_can_update_user_monthly_token_limits(): void
    {
        $response = $this->actingAs($this->admin)
            ->patchJson("/api/admin/ai-governance/users/{$this->regularUser->id}/limits", [
                'monthly_token_limit' => 3500000,
            ]);

        $response->assertOk();
        $this->assertEquals(3500000, $this->regularUser->fresh()->monthly_token_limit);
    }

    public function test_admin_can_reset_user_monthly_token_usage(): void
    {
        $this->assertEquals(250000, $this->regularUser->tokens_used_this_month);

        $response = $this->actingAs($this->admin)
            ->postJson("/api/admin/ai-governance/users/{$this->regularUser->id}/reset-usage");

        $response->assertOk()
            ->assertJson(['tokens_used_this_month' => 0]);

        $this->assertEquals(0, $this->regularUser->fresh()->tokens_used_this_month);
    }

    public function test_user_record_ai_usage_persists_log_and_increments_counter(): void
    {
        $log = $this->regularUser->recordAiUsage(
            promptTokens: 2000,
            completionTokens: 800,
            model: 'gemini-3.8',
            context: 'test_call',
            latencyMs: 320
        );

        $this->assertDatabaseHas('ai_usage_logs', [
            'id' => $log->id,
            'user_id' => $this->regularUser->id,
            'total_tokens' => 2800,
            'model' => 'gemini-3.8',
        ]);

        $this->assertEquals(250000 + 2800, $this->regularUser->fresh()->tokens_used_this_month);
    }

    public function test_gemini_service_blocks_execution_when_user_ai_is_inactive(): void
    {
        $this->regularUser->update(['is_ai_active' => false]);

        $conversation = AgentConversation::create([
            'user_id' => $this->regularUser->id,
            'context_type' => 'incubator',
        ]);

        $service = app(GeminiAgentService::class);

        $this->expectException(GeminiApiException::class);
        $this->expectExceptionMessage('O acesso aos serviços de IA foi temporariamente suspenso para este usuário pela administração.');

        $service->orchestrateTurn($conversation);
    }

    public function test_gemini_service_blocks_execution_when_user_exceeds_token_limit(): void
    {
        $this->regularUser->update([
            'is_ai_active' => true,
            'monthly_token_limit' => 100000,
            'tokens_used_this_month' => 150000, // Cota estourada
        ]);

        $conversation = AgentConversation::create([
            'user_id' => $this->regularUser->id,
            'context_type' => 'incubator',
        ]);

        $service = app(GeminiAgentService::class);

        $this->expectException(GeminiApiException::class);
        $this->expectExceptionMessage('Limite mensal de tokens de IA atingido.');

        $service->orchestrateTurn($conversation);
    }
}

