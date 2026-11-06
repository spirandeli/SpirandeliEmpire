<?php

namespace Tests\Feature\Api;

use App\Enums\ApprovalStatus;
use App\Enums\TaskStatus;
use App\Events\ApprovalApproved;
use App\Events\ApprovalRejected;
use App\Events\ApprovalRevisionRequested;
use App\Events\ApprovalSubmitted;
use App\Models\ApprovalQueue;
use App\Models\Business;
use App\Models\ContentAsset;
use App\Models\Task;
use App\Models\TikTokProduct;
use App\Models\User;
use App\Services\ApprovalService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Event;
use Illuminate\Validation\ValidationException;
use Tests\TestCase;

class ApprovalFlowTest extends TestCase
{
    use RefreshDatabase;

    private User $user;

    private Business $business;

    private ApprovalService $service;

    protected function setUp(): void
    {
        parent::setUp();

        $this->user = User::factory()->create();
        $this->business = $this->user->businesses()->create(['name' => 'Achadinhos', 'type' => 'tiktok_shop_affiliate']);
        $this->service = app(ApprovalService::class);
        $this->actingAs($this->user, 'sanctum');
    }

    private function package(): array
    {
        return [
            'product' => ['title' => 'Mini processador'],
            'hooks' => ['Hook A', 'Hook B', 'Hook C'],
            'script' => 'Cena 1... Cena 2...',
            'visual_prompts' => ['close na lâmina'],
            'caption' => 'Você precisa disso!',
            'hashtags' => ['#tiktokshop', '#achadinhos'],
        ];
    }

    private function submit(?Task $task = null, array $override = []): ApprovalQueue
    {
        return $this->service->submit($this->business, array_merge([
            'type' => ApprovalQueue::TYPE_TIKTOK_CONTENT_PACKAGE,
            'title' => 'Mini processador - pacote de vídeo',
            'summary' => 'Comissão 18%',
            'payload' => $this->package(),
            'task_id' => $task?->id,
        ], $override));
    }

    private function agentTask(): Task
    {
        return Task::create([
            'business_id' => $this->business->id, 'user_id' => $this->user->id, 'title' => 'Gerar roteiro',
            'assignee' => 'agent', 'status' => TaskStatus::InProgressAgent,
        ]);
    }

    public function test_submit_creates_pending_item_and_moves_task_to_supervision(): void
    {
        Event::fake([ApprovalSubmitted::class]);
        $task = $this->agentTask();

        $approval = $this->submit($task);

        $this->assertSame(ApprovalStatus::Pending, $approval->status);
        $this->assertNotNull($approval->expires_at);
        $this->assertSame(TaskStatus::AwaitingSupervision, $task->refresh()->status);
        Event::assertDispatched(ApprovalSubmitted::class);
        $this->assertDatabaseHas('agent_logs', ['event' => 'approval_submitted', 'user_id' => $this->user->id]);
    }

    public function test_malformed_tiktok_package_is_rejected(): void
    {
        $bad = $this->package();
        unset($bad['hooks']);
        $bad['hashtags'] = [];

        try {
            $this->submit(null, ['payload' => $bad]);
            $this->fail('Deveria ter lançado ValidationException');
        } catch (ValidationException $e) {
            $this->assertArrayHasKey('payload.hooks', $e->errors());
            $this->assertArrayHasKey('payload.hashtags', $e->errors());
        }

        $this->assertDatabaseCount('approval_queues', 0);
    }

    public function test_inbox_lists_awaiting_items_ordered_by_priority_and_summary(): void
    {
        $this->submit(null, ['priority' => 'low', 'title' => 'baixa']);
        $this->submit(null, ['priority' => 'urgent', 'title' => 'urgente']);
        $this->service->reject($this->submit(null, ['title' => 'descartada']));

        $this->getJson('/api/approvals')->assertOk()
            ->assertJsonCount(2, 'data')
            ->assertJsonPath('data.0.title', 'urgente');

        $this->getJson('/api/approvals/summary')->assertOk()
            ->assertJsonPath('data.pending', 2)->assertJsonPath('data.total_awaiting', 2);

        $this->getJson('/api/approvals?status=rejected')->assertOk()->assertJsonCount(1, 'data');
    }

    public function test_approve_with_schedule_and_hook_selection_closes_the_task(): void
    {
        Event::fake([ApprovalApproved::class]);
        $task = $this->agentTask();
        $approval = $this->submit($task);
        foreach ([0, 1, 2] as $i) {
            ContentAsset::create([
                'business_id' => $this->business->id, 'approval_queue_id' => $approval->id,
                'type' => 'hook', 'body' => "Hook {$i}", 'content' => ['index' => $i], 'status' => 'pending_approval',
            ]);
        }

        $when = now()->addDay()->toIso8601String();
        $this->postJson("/api/approvals/{$approval->id}/approve", ['scheduled_for' => $when, 'selected_hook_index' => 1])
            ->assertOk()
            ->assertJsonPath('data.status', 'scheduled')
            ->assertJsonPath('data.payload.selected_hook_index', 1);

        $this->assertSame(TaskStatus::Done, $task->refresh()->status);
        $this->assertSame('approved', $task->result['outcome']);
        $this->assertSame(3, ContentAsset::where('status', 'approved')->count());
        $this->assertTrue(ContentAsset::where('type', 'hook')->get()
            ->firstWhere(fn ($a) => $a->content['index'] === 1)->is_selected);
        Event::assertDispatched(ApprovalApproved::class);
    }

    public function test_approve_rejects_unknown_hook_and_past_schedule(): void
    {
        $approval = $this->submit();

        $this->postJson("/api/approvals/{$approval->id}/approve", ['selected_hook_index' => 9])
            ->assertUnprocessable()->assertJsonValidationErrors('selected_hook_index');
        $this->postJson("/api/approvals/{$approval->id}/approve", ['scheduled_for' => now()->subDay()->toIso8601String()])
            ->assertUnprocessable()->assertJsonValidationErrors('scheduled_for');

        $this->assertSame(ApprovalStatus::Pending, $approval->refresh()->status);
    }

    public function test_request_revision_records_history_and_fires_event(): void
    {
        Event::fake([ApprovalRevisionRequested::class]);
        $approval = $this->submit();

        $this->postJson("/api/approvals/{$approval->id}/revision", ['feedback' => 'O hook 2 está fraco, mais agressivo', 'section' => 'hooks'])
            ->assertOk()
            ->assertJsonPath('data.status', 'revision_requested')
            ->assertJsonPath('data.revision_count', 1)
            ->assertJsonPath('data.revision_history.0.section', 'hooks');

        Event::assertDispatched(ApprovalRevisionRequested::class,
            fn ($e) => $e->section === 'hooks' && str_contains($e->feedback, 'hook 2'));

        // continua na inbox e permite novo ajuste
        $this->getJson('/api/approvals')->assertJsonCount(1, 'data');
        $this->postJson("/api/approvals/{$approval->id}/revision", ['feedback' => 'Ainda não ficou bom'])->assertOk()
            ->assertJsonPath('data.revision_count', 2);
    }

    public function test_revision_cycle_returns_item_to_pending_with_new_payload(): void
    {
        $task = $this->agentTask();
        $approval = $this->submit($task);
        $this->service->requestRevision($approval, 'Reescreva o roteiro', 'script');

        $this->service->markRevising($approval->refresh());
        $this->assertSame(ApprovalStatus::Revising, $approval->refresh()->status);
        $this->assertSame(TaskStatus::InProgressAgent, $task->refresh()->status);

        $new = array_merge($this->package(), ['script' => 'Roteiro v2']);
        $this->service->completeRevision($approval->refresh(), $new, 'v2');

        $approval->refresh();
        $this->assertSame(ApprovalStatus::Pending, $approval->status);
        $this->assertSame('Roteiro v2', $approval->payload['script']);
        $this->assertSame(TaskStatus::AwaitingSupervision, $task->refresh()->status);
    }

    public function test_reject_can_discard_the_product(): void
    {
        Event::fake([ApprovalRejected::class]);
        $product = TikTokProduct::create([
            'business_id' => $this->business->id, 'external_id' => 'p1', 'title' => 'Produto', 'status' => 'content_ready',
        ]);
        $approval = $this->submit(null, ['approvable_type' => 'tiktok_product', 'approvable_id' => $product->id]);

        $this->postJson("/api/approvals/{$approval->id}/reject", ['reason' => 'Não combina', 'discard_product' => true])
            ->assertOk()->assertJsonPath('data.status', 'rejected');

        $this->assertSame('discarded', $product->refresh()->status);
        $this->assertSame('Não combina', $approval->refresh()->reviewer_feedback);
        Event::assertDispatched(ApprovalRejected::class);
    }

    public function test_final_items_cannot_be_decided_again(): void
    {
        $approval = $this->submit();
        $this->postJson("/api/approvals/{$approval->id}/approve")->assertOk();

        $this->postJson("/api/approvals/{$approval->id}/approve")->assertStatus(409);
        $this->postJson("/api/approvals/{$approval->id}/reject")->assertStatus(409);
        $this->postJson("/api/approvals/{$approval->id}/revision", ['feedback' => 'tarde demais'])->assertStatus(409);
    }

    public function test_isolation_between_users(): void
    {
        $approval = $this->submit();

        $this->actingAs(User::factory()->create(), 'sanctum');
        $this->getJson("/api/approvals/{$approval->id}")->assertNotFound();
        $this->postJson("/api/approvals/{$approval->id}/approve")->assertNotFound();
        $this->getJson('/api/approvals')->assertOk()->assertJsonCount(0, 'data');
    }
}

