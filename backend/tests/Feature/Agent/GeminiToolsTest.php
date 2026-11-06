<?php

namespace Tests\Feature\Agent;

use App\Models\Business;
use App\Models\CalendarEvent;
use App\Models\Task;
use App\Models\TikTokProduct;
use App\Models\User;
use App\Services\ApprovalService;
use App\Services\BusinessService;
use App\Services\Gemini\Tools\CheckUserScheduleTool;
use App\Services\Gemini\Tools\CreateBusinessVentureTool;
use App\Services\Gemini\Tools\CreateTaskTool;
use App\Services\Gemini\Tools\SaveTikTokProductStrategyTool;
use App\Services\Gemini\Tools\SubmitForHumanApprovalTool;
use App\Services\Gemini\Tools\ToolExecutionContext;
use App\Services\TaskService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class GeminiToolsTest extends TestCase
{
    use RefreshDatabase;

    private User $user;

    protected function setUp(): void
    {
        parent::setUp();
        $this->user = User::factory()->create(['timezone' => 'America/Sao_Paulo']);
    }

    public function test_create_business_venture_tool_creates_business_with_automations(): void
    {
        $tool = new CreateBusinessVentureTool(app(BusinessService::class));
        $context = new ToolExecutionContext($this->user);

        $result = $tool->execute([
            'name' => 'Canal Dark Finanças',
            'type' => 'content_channel',
            'niche' => 'Investimentos & Cripto',
            'description' => 'Canal focado em cortes e vídeos explicativos.',
            'canvas' => ['value_proposition' => 'Educação financeira ágil'],
        ], $context);

        $this->assertTrue($result['success']);
        $this->assertDatabaseHas('businesses', [
            'user_id' => $this->user->id,
            'name' => 'Canal Dark Finanças',
            'type' => 'content_channel',
        ]);
    }

    public function test_create_task_tool_creates_agent_and_user_tasks(): void
    {
        $business = $this->user->businesses()->create(['name' => 'Biz']);
        $tool = new CreateTaskTool(app(TaskService::class));
        $context = new ToolExecutionContext($this->user, $business);

        // Tarefa para o agente
        $resAgent = $tool->execute([
            'title' => 'Minerar top 10 produtos',
            'assignee' => 'agent',
            'priority' => 'high',
            'agent_action' => 'mine_products',
        ], $context);

        $this->assertTrue($resAgent['success']);
        $this->assertDatabaseHas('tasks', [
            'business_id' => $business->id,
            'title' => 'Minerar top 10 produtos',
            'assignee' => 'agent',
            'status' => 'backlog',
        ]);

        // Tarefa para o humano
        $resUser = $tool->execute([
            'title' => 'Gravar vídeo do produto X',
            'assignee' => 'user',
            'priority' => 'urgent',
        ], $context);

        $this->assertTrue($resUser['success']);
        $this->assertDatabaseHas('tasks', [
            'business_id' => $business->id,
            'title' => 'Gravar vídeo do produto X',
            'assignee' => 'user',
            'status' => 'todo_user',
        ]);
    }

    public function test_submit_for_human_approval_tool_registers_delivery_package(): void
    {
        $business = $this->user->businesses()->create(['name' => 'Biz TikTok', 'type' => 'tiktok_shop_affiliate']);
        $tool = new SubmitForHumanApprovalTool(app(ApprovalService::class));
        $context = new ToolExecutionContext($this->user, $business);

        $result = $tool->execute([
            'type' => 'tiktok_content_package',
            'title' => 'Mini Aspirador Portátil - Roteiro Viral',
            'summary' => 'Comissão 20%, alta tração.',
            'agent_confidence' => 0.92,
            'payload' => [
                'product' => ['title' => 'Mini Aspirador'],
                'hooks' => ['Você nunca mais vai limpar o teclado assim!', 'O achado mais útil do TikTok'],
                'script' => 'Cena 1: close na poeira. Cena 2: aspirando em 3 segundos.',
                'visual_prompts' => ['Macro shot do teclado limpo'],
                'caption' => 'Link na bio para garantir com frete grátis!',
                'hashtags' => ['#achadinhos', '#tiktokshop', '#limpeza'],
                'cta' => 'Compre agora na loja oficial',
            ],
        ], $context);

        $this->assertTrue($result['success']);
        $this->assertDatabaseHas('approval_queues', [
            'business_id' => $business->id,
            'title' => 'Mini Aspirador Portátil - Roteiro Viral',
            'status' => 'pending',
        ]);
    }

    public function test_check_user_schedule_tool_detects_events(): void
    {
        CalendarEvent::create([
            'user_id' => $this->user->id,
            'provider' => 'google',
            'kind' => 'event',
            'external_id' => 'evt_1',
            'title' => 'Reunião de Alinhamento',
            'starts_at' => now()->addHours(2),
            'ends_at' => now()->addHours(3),
            'status' => 'confirmed',
        ]);

        $tool = new CheckUserScheduleTool();
        $context = new ToolExecutionContext($this->user);

        $result = $tool->execute([
            'from' => now()->toIso8601String(),
            'to' => now()->addHours(10)->toIso8601String(),
        ], $context);

        $this->assertTrue($result['success']);
        $this->assertSame(1, $result['busy_events_count']);
        $this->assertSame('Reunião de Alinhamento', $result['busy_events'][0]['title']);
    }

    public function test_save_tiktok_product_strategy_tool(): void
    {
        $business = $this->user->businesses()->create(['name' => 'TikTok Store', 'type' => 'tiktok_shop_affiliate']);
        $tool = new SaveTikTokProductStrategyTool();
        $context = new ToolExecutionContext($this->user, $business);

        $result = $tool->execute([
            'external_id' => 'tt_prod_999',
            'title' => 'Escova Giratória 5 em 1',
            'category' => 'Beleza',
            'price' => 150.00,
            'commission_rate' => 15.00,
            'sales_velocity' => 85.00,
            'margin_score' => 80,
            'velocity_score' => 90,
            'viral_score' => 95,
            'ai_analysis' => [
                'target_audience' => 'Mulheres 18-35 anos',
                'core_pain_points' => ['Demora para secar', 'Cabelo com frizz'],
            ],
        ], $context);

        $this->assertTrue($result['success']);
        $this->assertSame(22.5, $result['commission_value']);

        $product = TikTokProduct::where('external_id', 'tt_prod_999')->first();
        $this->assertNotNull($product);
        $this->assertSame(150.0, (float) $product->price);
        $this->assertSame(22.5, (float) $product->commission_value);
        $this->assertGreaterThan(80, $product->overall_score);
    }
}

