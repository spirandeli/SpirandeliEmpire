<?php

namespace Tests\Feature\Api;

use App\Models\Business;
use App\Models\Task;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class TaskTest extends TestCase
{
    use RefreshDatabase;

    private User $user;

    private Business $business;

    protected function setUp(): void
    {
        parent::setUp();

        $this->user = User::factory()->create();
        $this->business = $this->user->businesses()->create(['name' => 'Op']);
        $this->actingAs($this->user, 'sanctum');
    }

    private function create(array $data = []): array
    {
        return $this->postJson('/api/tasks', array_merge([
            'business_id' => $this->business->id,
            'title' => 'Tarefa',
        ], $data))->assertCreated()->json('data');
    }

    public function test_status_defaults_follow_the_assignee(): void
    {
        $this->assertSame('todo_user', $this->create(['assignee' => 'user'])['status']);
        $this->assertSame('backlog', $this->create(['assignee' => 'agent'])['status']);
    }

    public function test_cannot_create_task_in_another_users_business(): void
    {
        $other = User::factory()->create()->businesses()->create(['name' => 'Alheio']);

        $this->postJson('/api/tasks', ['business_id' => $other->id, 'title' => 'x'])
            ->assertUnprocessable()->assertJsonValidationErrors('business_id');
    }

    public function test_move_between_valid_columns_and_reorder(): void
    {
        $a = $this->create(['assignee' => 'user']);
        $b = $this->create(['assignee' => 'user']);

        $this->patchJson("/api/tasks/{$a['id']}/move", ['status' => 'done'])
            ->assertOk()->assertJsonPath('data.status', 'done');
        $this->assertNotNull(Task::find($a['id'])->completed_at);

        // reabrir limpa completed_at
        $this->patchJson("/api/tasks/{$a['id']}/move", ['status' => 'todo_user', 'position' => 0])->assertOk();
        $this->assertNull(Task::find($a['id'])->completed_at);

        // `a` entrou na posição 0 -> `b` foi empurrada
        $this->assertSame(0, Task::find($a['id'])->position);
        $this->assertGreaterThan(0, Task::find($b['id'])->position);
    }

    public function test_invalid_moves_are_rejected(): void
    {
        $human = $this->create(['assignee' => 'user']);
        $agent = $this->create(['assignee' => 'agent']);

        // humano não pode ir para a coluna do worker nem para "supervisão"
        $this->patchJson("/api/tasks/{$human['id']}/move", ['status' => 'in_progress_agent'])->assertUnprocessable();
        $this->patchJson("/api/tasks/{$human['id']}/move", ['status' => 'awaiting_supervision'])->assertUnprocessable();
        // ninguém (via API) coloca tarefa do agente em execução
        $this->patchJson("/api/tasks/{$agent['id']}/move", ['status' => 'in_progress_agent'])->assertUnprocessable();
        // tarefa do agente não vai para "A Fazer (Humano)"
        $this->patchJson("/api/tasks/{$agent['id']}/move", ['status' => 'todo_user'])->assertUnprocessable();
        // valor inválido
        $this->patchJson("/api/tasks/{$agent['id']}/move", ['status' => 'xyz'])->assertUnprocessable();
    }

    public function test_reassigning_moves_task_to_a_valid_column(): void
    {
        $task = $this->create(['assignee' => 'user']);
        $this->assertSame('todo_user', $task['status']);

        $this->putJson("/api/tasks/{$task['id']}", ['assignee' => 'agent'])
            ->assertOk()
            ->assertJsonPath('data.assignee', 'agent')
            ->assertJsonPath('data.status', 'backlog');
    }

    public function test_board_returns_five_columns_and_filters(): void
    {
        $this->create(['assignee' => 'user']);
        $this->create(['assignee' => 'agent']);
        $this->create(['assignee' => 'agent']);

        $board = $this->getJson('/api/tasks/board')->assertOk()->json('data');
        $this->assertSame(
            ['backlog', 'in_progress_agent', 'awaiting_supervision', 'todo_user', 'done'],
            array_column($board, 'status'),
        );
        $this->assertSame(2, collect($board)->firstWhere('status', 'backlog')['count']);
        $this->assertSame(1, collect($board)->firstWhere('status', 'todo_user')['count']);

        $this->getJson('/api/tasks?assignee=agent')->assertOk()->assertJsonCount(2, 'data');
        $this->getJson("/api/tasks?business_id={$this->business->id}&assignee=user")->assertOk()->assertJsonCount(1, 'data');
    }

    public function test_isolation_between_users(): void
    {
        $task = $this->create();

        $this->actingAs(User::factory()->create(), 'sanctum');
        $this->getJson("/api/tasks/{$task['id']}")->assertNotFound();
        $this->patchJson("/api/tasks/{$task['id']}/move", ['status' => 'done'])->assertNotFound();
        $this->deleteJson("/api/tasks/{$task['id']}")->assertNotFound();
        $this->getJson('/api/tasks')->assertOk()->assertJsonCount(0, 'data');
    }

    public function test_delete_task(): void
    {
        $task = $this->create();

        $this->deleteJson("/api/tasks/{$task['id']}")->assertNoContent();
        $this->assertSoftDeleted('tasks', ['id' => $task['id']]);
    }

    public function test_agent_logs_endpoint_supports_incremental_polling(): void
    {
        $this->create(); // não gera log; criamos manualmente
        foreach (range(1, 3) as $i) {
            \App\Models\AgentLog::record($this->user->id, 'tool_call', "log {$i}", \App\Enums\LogLevel::Info, [], ['business_id' => $this->business->id]);
        }

        $first = $this->getJson('/api/agent/logs')->assertOk();
        $first->assertJsonCount(3, 'data');
        $lastId = $first->json('meta.last_id');

        \App\Models\AgentLog::record($this->user->id, 'tool_result', 'log 4');

        $this->getJson("/api/agent/logs?after_id={$lastId}")
            ->assertOk()->assertJsonCount(1, 'data')->assertJsonPath('data.0.message', 'log 4');
    }
}

