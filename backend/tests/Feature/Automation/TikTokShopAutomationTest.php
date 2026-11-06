<?php

namespace Tests\Feature\Automation;

use App\Enums\ApprovalStatus;
use App\Enums\TaskStatus;
use App\Jobs\GenerateAffiliateContentJob;
use App\Jobs\ProcessApprovalRevisionJob;
use App\Jobs\TikTokShopMinerJob;
use App\Models\ApprovalQueue;
use App\Models\Business;
use App\Models\ContentAsset;
use App\Models\Task;
use App\Models\TikTokProduct;
use App\Models\User;
use App\Services\TikTokShopService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Queue;
use Tests\TestCase;

class TikTokShopAutomationTest extends TestCase
{
    use RefreshDatabase;

    private User $user;
    private Business $business;
    private TikTokShopService $tikTokService;

    protected function setUp(): void
    {
        parent::setUp();
        $this->user = User::factory()->create();
        $this->business = $this->user->businesses()->create([
            'name' => 'Canal Achadinhos Prime',
            'type' => 'tiktok_shop_affiliate',
            'status' => 'active',
            'niche' => 'Cozinha Criativa',
            'automation_enabled' => true,
        ]);

        config(['services.gemini.api_key' => 'FAKE-KEY-TIKTOK-GEMINI']);
        $this->tikTokService = app(TikTokShopService::class);
        $this->actingAs($this->user, 'sanctum');
    }

    public function test_miner_job_finds_products_and_dispatches_content_generation(): void
    {
        Queue::fake([GenerateAffiliateContentJob::class]);

        $job = new TikTokShopMinerJob($this->business, [
            'min_commission_rate' => 15.0,
            'min_overall_score' => 70,
            'auto_generate_content_limit' => 1,
        ]);

        $job->handle($this->tikTokService);

        // Verifica que produtos foram persistidos no banco
        $this->assertDatabaseHas('tiktok_products', [
            'business_id' => $this->business->id,
            'status' => TikTokProduct::STATUS_SELECTED,
        ]);

        // Verifica que o job de geração de conteúdo foi enfileirado para o melhor produto
        Queue::assertPushed(GenerateAffiliateContentJob::class, function ($job) {
            return $job->business->id === $this->business->id && $job->product->overall_score >= 70;
        });

        // Verifica log de execução gravado
        $this->assertDatabaseHas('agent_logs', [
            'business_id' => $this->business->id,
            'event' => 'tiktok_mining_completed',
        ]);
    }

    public function test_generate_affiliate_content_package_creates_assets_and_approval_item(): void
    {
        $product = TikTokProduct::create([
            'business_id' => $this->business->id,
            'external_id' => 'tt_prod_test_100',
            'title' => 'Mini Selador Térmico Portátil',
            'category' => 'Cozinha',
            'price' => 39.90,
            'commission_rate' => 20.00,
            'commission_value' => 7.98,
            'overall_score' => 88,
            'status' => TikTokProduct::STATUS_SELECTED,
        ]);

        $mockGeminiResponse = [
            'data_justification' => 'Produto com alta margem de 20% e forte apelo visual para demonstração de 5 segundos.',
            'target_audience' => 'Donas de casa e praticantes de culinária rápida.',
            'hooks' => [
                'Você nunca mais vai comer salgadinho murcho!',
                'O produto de 30 reais que mudou a minha despensa.',
                'Testei o selador viral do TikTok e me surpreendi!',
            ],
            'script' => "Cena 1 (0-3s): Mostre o saco aberto.\nCena 2 (3-8s): Passe o selador deslizando.\nCena 3 (8-15s): Mostre que não vaza nem água. Chame para o link.",
            'visual_prompts' => [
                'Macro do fecho selando o plástico',
                'Teste da água virando de ponta cabeça',
            ],
            'caption' => 'Adeus salgadinho murcho! Garanta o seu com desconto no botão abaixo.',
            'hashtags' => ['#tiktokshop', '#achadinhos', '#cozinha', '#utilidades'],
            'cta' => 'Compre agora pelo carrinho laranja antes que acabe a promoção!',
            'suggested_posting_time' => '18:30',
            'ai_analysis' => [
                'core_pain_points' => ['Alimentos perdendo a crocância'],
                'hook_angles' => ['Demonstração de choque'],
            ],
        ];

        Http::fake([
            'generativelanguage.googleapis.com/*' => Http::response([
                'candidates' => [
                    [
                        'finishReason' => 'STOP',
                        'content' => [
                            'role' => 'model',
                            'parts' => [
                                ['text' => json_encode($mockGeminiResponse)],
                            ],
                        ],
                    ],
                ],
            ], 200),
        ]);

        $job = new GenerateAffiliateContentJob($this->business, $product);
        $job->handle($this->tikTokService);

        // Verifica se a entrega foi criada na fila de aprovação
        $approval = ApprovalQueue::where('business_id', $this->business->id)
            ->where('approvable_id', $product->id)
            ->first();

        $this->assertNotNull($approval);
        $this->assertSame(ApprovalStatus::Pending, $approval->status);
        $this->assertSame(3, count($approval->payload['hooks']));
        $this->assertSame('18:30', $approval->payload['suggested_posting_time']);

        // Verifica se os 4 tipos de ContentAssets foram criados e associados
        $this->assertSame(3, ContentAsset::where('approval_queue_id', $approval->id)->where('type', ContentAsset::TYPE_HOOK)->count());
        $this->assertSame(1, ContentAsset::where('approval_queue_id', $approval->id)->where('type', ContentAsset::TYPE_VIDEO_SCRIPT)->count());
        $this->assertSame(1, ContentAsset::where('approval_queue_id', $approval->id)->where('type', ContentAsset::TYPE_VISUAL_PROMPT)->count());
        $this->assertSame(1, ContentAsset::where('approval_queue_id', $approval->id)->where('type', ContentAsset::TYPE_CAPTION)->count());

        // Verifica se a tarefa no Kanban foi movida para awaiting_supervision
        $task = Task::where('business_id', $this->business->id)->latest('id')->first();
        $this->assertSame(TaskStatus::AwaitingSupervision, $task->status);
    }

    public function test_process_approval_revision_job_rewrites_section(): void
    {
        $approval = ApprovalQueue::create([
            'business_id' => $this->business->id,
            'user_id' => $this->user->id,
            'title' => 'Vídeo Fritadeira Elétrica',
            'type' => ApprovalQueue::TYPE_TIKTOK_CONTENT_PACKAGE,
            'status' => ApprovalStatus::RevisionRequested,
            'payload' => [
                'hooks' => ['Hook antigo 1', 'Hook antigo 2', 'Hook antigo 3'],
                'script' => 'Roteiro antigo',
                'visual_prompts' => ['prompt 1'],
                'caption' => 'Legenda',
                'hashtags' => ['#tiktok'],
            ],
        ]);

        $revisedResponse = [
            'hooks' => [
                'NOVO HOOK 1: Mais agressivo e focado em economia de energia!',
                'NOVO HOOK 2: Se você gasta gás de cozinha, pare agora!',
                'NOVO HOOK 3: O segredo que as marcas não querem que você saiba.',
            ],
            'script' => 'Roteiro antigo mantido',
            'visual_prompts' => ['prompt 1'],
            'caption' => 'Legenda',
            'hashtags' => ['#tiktok'],
        ];

        Http::fake([
            'generativelanguage.googleapis.com/*' => Http::response([
                'candidates' => [
                    [
                        'finishReason' => 'STOP',
                        'content' => [
                            'role' => 'model',
                            'parts' => [
                                ['text' => json_encode($revisedResponse)],
                            ],
                        ],
                    ],
                ],
            ], 200),
        ]);

        $job = new ProcessApprovalRevisionJob($approval, 'Hooks muito fracos, quero ganchos mais apelativos', 'hooks');
        $job->handle($this->tikTokService);

        $approval->refresh();
        $this->assertSame(ApprovalStatus::Pending, $approval->status);
        $this->assertStringContainsString('NOVO HOOK 1', $approval->payload['hooks'][0]);
    }
}

