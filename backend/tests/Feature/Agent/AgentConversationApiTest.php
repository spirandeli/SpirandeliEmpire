<?php

namespace Tests\Feature\Agent;

use App\Models\AgentConversation;
use App\Models\Business;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class AgentConversationApiTest extends TestCase
{
    use RefreshDatabase;

    private User $user;

    protected function setUp(): void
    {
        parent::setUp();
        $this->user = User::factory()->create();
        config(['services.gemini.api_key' => 'FAKE-KEY-TESTING']);
        $this->actingAs($this->user, 'sanctum');
    }

    public function test_create_conversation_for_incubator(): void
    {
        $response = $this->postJson('/api/agent/conversations', [
            'context_type' => 'incubator',
            'title' => 'Sessão Estratégica Q4',
        ])->assertCreated()
            ->assertJsonPath('data.title', 'Sessão Estratégica Q4')
            ->assertJsonPath('data.context_type', 'incubator')
            ->assertJsonPath('data.status', 'active');

        $this->assertDatabaseHas('agent_conversations', [
            'user_id' => $this->user->id,
            'title' => 'Sessão Estratégica Q4',
        ]);
    }

    public function test_create_conversation_linked_to_business(): void
    {
        $business = $this->user->businesses()->create(['name' => 'Empresa Alfa']);

        $response = $this->postJson('/api/agent/conversations', [
            'business_id' => $business->id,
        ])->assertCreated()
            ->assertJsonPath('data.business_id', $business->id)
            ->assertJsonPath('data.context_type', 'business_chat');
    }

    public function test_list_and_show_conversations(): void
    {
        $c1 = $this->user->agentConversations()->create(['title' => 'C1']);
        $c2 = $this->user->agentConversations()->create(['title' => 'C2']);

        $this->getJson('/api/agent/conversations')
            ->assertOk()
            ->assertJsonCount(2, 'data');

        $this->getJson("/api/agent/conversations/{$c1->uuid}")
            ->assertOk()
            ->assertJsonPath('data.title', 'C1')
            ->assertJsonPath('data.uuid', $c1->uuid);
    }

    public function test_send_message_via_api(): void
    {
        Http::fake([
            'generativelanguage.googleapis.com/*' => Http::response([
                'candidates' => [
                    [
                        'finishReason' => 'STOP',
                        'content' => [
                            'role' => 'model',
                            'parts' => [
                                ['text' => 'Plano traçado com sucesso.'],
                            ],
                        ],
                    ],
                ],
                'usageMetadata' => ['promptTokenCount' => 80, 'candidatesTokenCount' => 15],
            ], 200),
        ]);

        $conversation = $this->user->agentConversations()->create(['title' => 'Chat']);

        $response = $this->postJson("/api/agent/conversations/{$conversation->uuid}/messages", [
            'message' => 'Qual é o próximo passo?',
        ])->assertOk()
            ->assertJsonPath('data.content', 'Plano traçado com sucesso.')
            ->assertJsonPath('data.role', 'model')
            ->assertJsonCount(2, 'new_messages'); // 1 do user + 1 do model

        $this->assertDatabaseHas('agent_messages', [
            'agent_conversation_id' => $conversation->id,
            'content' => 'Qual é o próximo passo?',
        ]);
    }

    public function test_user_cannot_access_or_message_another_users_conversation(): void
    {
        $otherUser = User::factory()->create();
        $otherConversation = $otherUser->agentConversations()->create(['title' => 'Privado']);

        $this->getJson("/api/agent/conversations/{$otherConversation->uuid}")
            ->assertNotFound();

        $this->postJson("/api/agent/conversations/{$otherConversation->uuid}/messages", [
            'message' => 'Invadindo conversa',
        ])->assertNotFound();
    }
}

