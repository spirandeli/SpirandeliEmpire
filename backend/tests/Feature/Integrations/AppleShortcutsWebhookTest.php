<?php

namespace Tests\Feature\Integrations;

use App\Enums\ApprovalStatus;
use App\Models\ApprovalQueue;
use App\Models\Business;
use App\Models\Task;
use App\Models\User;
use App\Models\UserIntegration;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class AppleShortcutsWebhookTest extends TestCase
{
    use RefreshDatabase;

    private User $user;
    private Business $business;
    private string $plainToken = 'abvos_test_token_secret_1234567890abcdef1234567890abcdef';

    protected function setUp(): void
    {
        parent::setUp();
        $this->user = User::factory()->create();
        $this->business = $this->user->businesses()->create(['name' => 'Operação iPhone']);

        UserIntegration::create([
            'user_id' => $this->user->id,
            'provider' => UserIntegration::PROVIDER_SHORTCUTS,
            'webhook_token_hash' => hash('sha256', $this->plainToken),
            'token_prefix' => substr($this->plainToken, 0, 10),
            'status' => 'connected',
        ]);
    }

    public function test_rejects_missing_or_invalid_webhook_token(): void
    {
        $this->postJson('/api/webhooks/shortcuts', ['action' => 'daily_briefing'])
            ->assertUnauthorized();

        $this->postJson('/api/webhooks/shortcuts', ['action' => 'daily_briefing'], ['X-ABVOS-Token' => 'token-invalido'])
            ->assertForbidden();
    }

    public function test_capture_task_action_creates_task_from_iphone(): void
    {
        $response = $this->postJson('/api/webhooks/shortcuts', [
            'action' => 'capture_task',
            'title' => 'Comprar tripé para gravação de vídeos',
            'priority' => 'high',
            'assignee' => 'user',
        ], ['X-ABVOS-Token' => $this->plainToken]);

        $response->assertCreated()
            ->assertJsonPath('success', true)
            ->assertJsonPath('task.title', 'Comprar tripé para gravação de vídeos');

        $this->assertDatabaseHas('tasks', [
            'user_id' => $this->user->id,
            'title' => 'Comprar tripé para gravação de vídeos',
            'assignee' => 'user',
            'priority' => 'high',
        ]);
    }

    public function test_daily_briefing_returns_spoken_text_and_counts(): void
    {
        ApprovalQueue::create([
            'user_id' => $this->user->id,
            'business_id' => $this->business->id,
            'title' => 'Roteiro Vídeo 1',
            'status' => ApprovalStatus::Pending,
            'payload' => ['sample' => true],
        ]);

        Task::create([
            'user_id' => $this->user->id,
            'business_id' => $this->business->id,
            'title' => 'Gravar cena 1',
            'assignee' => 'user',
            'status' => 'todo_user',
        ]);

        $response = $this->postJson('/api/webhooks/shortcuts', [
            'action' => 'daily_briefing',
        ], ['X-ABVOS-Token' => $this->plainToken]);

        $response->assertOk()
            ->assertJsonPath('pending_approvals_count', 1)
            ->assertJsonStructure(['spoken_text', 'pending_approvals', 'tasks_to_do']);

        $this->assertStringContainsString('1 entrega(s) aguardando', $response->json('spoken_text'));
    }

    public function test_approve_item_action_from_shortcut_widget(): void
    {
        $approval = ApprovalQueue::create([
            'user_id' => $this->user->id,
            'business_id' => $this->business->id,
            'title' => 'Campanha Black Friday',
            'status' => ApprovalStatus::Pending,
            'payload' => ['data' => 123],
        ]);

        $response = $this->postJson('/api/webhooks/shortcuts', [
            'action' => 'approve_item',
            'approval_id' => $approval->id,
        ], ['X-ABVOS-Token' => $this->plainToken]);

        $response->assertOk()
            ->assertJsonPath('success', true)
            ->assertJsonPath('status', 'approved');

        $this->assertSame(ApprovalStatus::Approved, $approval->refresh()->status);
    }
}

