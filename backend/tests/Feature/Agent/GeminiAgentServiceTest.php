<?php

namespace Tests\Feature\Agent;

use App\Enums\AgentMessageRole;
use App\Models\AgentConversation;
use App\Models\Business;
use App\Models\User;
use App\Services\GeminiAgentService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class GeminiAgentServiceTest extends TestCase
{
    use RefreshDatabase;

    private User $user;

    private GeminiAgentService $service;

    protected function setUp(): void
    {
        parent::setUp();

        $this->user = User::factory()->create();
        config(['services.gemini.api_key' => 'TEST-GEMINI-API-KEY-12345']);

        $this->service = app(GeminiAgentService::class);
    }

    public function test_simple_text_response_without_tools(): void
    {
        Http::fake([
            'generativelanguage.googleapis.com/*' => Http::response([
                'candidates' => [
                    [
                        'finishReason' => 'STOP',
                        'content' => [
                            'role' => 'model',
                            'parts' => [
                                ['text' => 'Olá! Eu sou seu COO Autônomo. Qual modelo de negócio vamos construir hoje?'],
                            ],
                        ],
                    ],
                ],
                'usageMetadata' => [
                    'promptTokenCount' => 120,
                    'candidatesTokenCount' => 25,
                ],
            ], 200),
        ]);

        $conversation = $this->user->agentConversations()->create([
            'title' => 'Incubadora',
            'context_type' => 'incubator',
        ]);

        $reply = $this->service->replyToUser($conversation, 'Olá, como você pode me ajudar?');

        $this->assertSame(AgentMessageRole::Model, $reply->role);
        $this->assertStringContainsString('Olá! Eu sou seu COO Autônomo', $reply->content);
        $this->assertSame(2, $conversation->messages()->count());
        $this->assertSame(120, $conversation->prompt_tokens);
        $this->assertSame(25, $conversation->completion_tokens);
    }

    public function test_full_function_calling_loop(): void
    {
        // Simula uma sequência de 2 requisições:
        // 1ª: Gemini decide chamar a ferramenta `createBusinessVenture`
        // 2ª: Após o PHP executar a ferramenta, Gemini responde com o texto final
        Http::fake([
            'generativelanguage.googleapis.com/*' => Http::sequence()
                ->push([
                    'candidates' => [
                        [
                            'finishReason' => 'STOP',
                            'content' => [
                                'role' => 'model',
                                'parts' => [
                                    [
                                        'functionCall' => [
                                            'name' => 'createBusinessVenture',
                                            'args' => [
                                                'name' => 'Agência de E-commerces TikTok',
                                                'type' => 'tiktok_shop_affiliate',
                                                'niche' => 'Moda & Acessórios',
                                                'description' => 'Operação de vídeos curtos com afiliados.',
                                                'goals' => ['videos_per_week' => 14],
                                            ],
                                        ],
                                    ],
                                ],
                            ],
                        ],
                    ],
                    'usageMetadata' => ['promptTokenCount' => 200, 'candidatesTokenCount' => 40],
                ], 200)
                ->push([
                    'candidates' => [
                        [
                            'finishReason' => 'STOP',
                            'content' => [
                                'role' => 'model',
                                'parts' => [
                                    ['text' => 'Excelente! Acabei de registrar e estruturar o negócio "Agência de E-commerces TikTok" no banco de dados e as automações padrão já foram ativadas.'],
                                ],
                            ],
                        ],
                    ],
                    'usageMetadata' => ['promptTokenCount' => 350, 'candidatesTokenCount' => 30],
                ], 200),
        ]);

        $conversation = $this->user->agentConversations()->create([
            'title' => 'Incubadora TikTok',
            'context_type' => 'incubator',
        ]);

        $reply = $this->service->replyToUser(
            $conversation,
            'Estruture para mim uma operação de TikTok Shop de Moda e cadastre no sistema.'
        );

        // Verifica se a resposta final do modelo é o texto conclusivo
        $this->assertSame(AgentMessageRole::Model, $reply->role);
        $this->assertStringContainsString('Acabei de registrar e estruturar o negócio', $reply->content);

        // Verifica se a tool em PHP foi realmente executada e o negócio foi criado no MySQL
        $this->assertDatabaseHas('businesses', [
            'user_id' => $this->user->id,
            'name' => 'Agência de E-commerces TikTok',
            'type' => 'tiktok_shop_affiliate',
        ]);

        // Verifica a trilha de mensagens no histórico:
        // 1. User: prompt inicial
        // 2. Model: functionCall (createBusinessVenture)
        // 3. Tool: functionResponse com o resultado da execução
        // 4. Model: texto final após processar o resultado da tool
        $messages = $conversation->messages()->orderBy('id')->get();
        $this->assertCount(4, $messages);
        $this->assertSame(AgentMessageRole::User, $messages[0]->role);
        $this->assertSame(AgentMessageRole::Model, $messages[1]->role);
        $this->assertSame(AgentMessageRole::Tool, $messages[2]->role);
        $this->assertSame('createBusinessVenture', $messages[2]->tool_name);
        $this->assertSame(AgentMessageRole::Model, $messages[3]->role);

        // Verifica os logs emitidos no console do agente
        $this->assertDatabaseHas('agent_logs', [
            'event' => 'tool_call',
            'user_id' => $this->user->id,
        ]);
        $this->assertDatabaseHas('agent_logs', [
            'event' => 'tool_result',
            'user_id' => $this->user->id,
        ]);
    }
}

