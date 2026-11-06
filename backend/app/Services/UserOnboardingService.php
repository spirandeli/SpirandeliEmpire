<?php

namespace App\Services;

use App\Enums\ApprovalStatus;
use App\Enums\BusinessStatus;
use App\Enums\LogLevel;
use App\Enums\TaskAssignee;
use App\Enums\TaskStatus;
use App\Models\AgentConversation;
use App\Models\AgentLog;
use App\Models\AgentMessage;
use App\Models\ApprovalQueue;
use App\Models\Business;
use App\Models\BusinessAutomation;
use App\Models\ContentAsset;
use App\Models\ConversionEvent;
use App\Models\Task;
use App\Models\TikTokProduct;
use App\Models\User;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

/**
 * Provisiona instantaneamente um Venture completo de alta fidelidade
 * para qualquer usuário (Admin ou Não-Admin) que acabe de se registrar,
 * faça login sem negócios ou solicite carregar dados de apresentação/demonstração.
 */
class UserOnboardingService
{
    public function provisionStarterKit(User $user): Business
    {
        return DB::transaction(function () use ($user) {
            $userFirstName = explode(' ', trim($user->name ?: 'Showcase'))[0];
            $randomSuffix = strtolower(Str::random(4));

            // 1. Cria o Negócio Modelo TikTok Shop de Alta Performance
            $business = Business::create([
                'user_id' => $user->id,
                'name' => "TikTok Shop Viral · {$userFirstName}",
                'slug' => "tiktok-viral-{$user->id}-{$randomSuffix}",
                'type' => Business::TYPE_TIKTOK_SHOP_AFFILIATE,
                'archetype' => Business::ARCHETYPE_AFFILIATE_TIKTOK,
                'status' => BusinessStatus::Active,
                'niche' => 'Tecnologia & Utilidades Virais',
                'description' => 'Operação automatizada de alta performance na TikTok Shop Brasil operada pelo Gemini 3.8 Co-Pilot.',
                'automation_enabled' => true,
                'north_star_metric' => 'commission_volume',
                'target_kpi_value' => 12000.00,
                'webhook_secret_token' => Str::random(40),
                'canvas' => [
                    'value_propositions' => [
                        'Demonstração hipnótica de produtos que solucionam dores imediatas em menos de 30 segundos.',
                        'Recomendações curadas com alta pontuação de viralidade e pronta entrega nacional.',
                    ],
                    'customer_segments' => [
                        'Público jovem e adulto (18-35 anos) que consome vídeos curtos e compra por impulso.',
                    ],
                    'channels' => [
                        'TikTok Shop Vitrine & Vídeos Orgânicos',
                        'Instagram Reels & YouTube Shorts',
                    ],
                    'revenue_streams' => [
                        'Comissões diretas de afiliado TikTok Shop (20% a 25% por venda concluída).',
                    ],
                ],
                'brand_rules' => [
                    'tone_of_voice' => 'Enérgico, dinâmico, autêntico e focado em demonstrar o benefício em 3 segundos.',
                    'target_audience' => 'Consumidores de compras por impulso e amantes de novidades tecnológicas no Brasil.',
                ],
                'activated_at' => now(),
            ]);

            // 2. Automação Padrão de Mineração Ativa
            BusinessAutomation::create([
                'business_id' => $business->id,
                'type' => BusinessAutomation::TYPE_TIKTOK_MINING,
                'name' => 'Mineração de Produtos Virais (6 em 6 horas)',
                'cron_expression' => '0 */6 * * *',
                'is_enabled' => true,
                'next_run_at' => now()->addHours(6),
                'config' => [
                    'categories' => ['Eletrônicos', 'Casa & Cozinha'],
                    'min_commission_rate' => 15,
                    'min_price' => 50,
                    'max_items_per_run' => 20,
                    'min_overall_score' => 70,
                ],
            ]);

            // 3. Produtos Minerados Reais na TikTok Shop
            $prod1 = TikTokProduct::create([
                'business_id' => $business->id,
                'external_id' => 'TTS-PROJ-' . strtoupper(Str::random(6)),
                'source' => 'api',
                'title' => 'Mini Projetor Portátil 4K Smart Cinema (Wi-Fi 6 & Bluetooth)',
                'category' => 'Eletrônicos & Casa Conectada',
                'shop_name' => 'TechShop Global Direct',
                'image_url' => 'https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=500&auto=format&fit=crop&q=60',
                'product_url' => 'https://shop.tiktok.com/view/product/demo-projector',
                'affiliate_link' => 'https://shop.tiktok.com/affiliate/demo-projector',
                'price' => 289.90,
                'currency' => 'BRL',
                'commission_rate' => 22.00,
                'commission_value' => 63.78,
                'sales_count' => 3840,
                'sales_velocity' => 142.50,
                'rating' => 4.85,
                'reviews_count' => 912,
                'margin_score' => 85,
                'velocity_score' => 92,
                'viral_score' => 89,
                'overall_score' => 89,
            ]);

            $prod2 = TikTokProduct::create([
                'business_id' => $business->id,
                'external_id' => 'TTS-FONE-' . strtoupper(Str::random(6)),
                'source' => 'api',
                'title' => 'Fones de Ouvido Noise-Cancelling Pro com Visor Digital LCD',
                'category' => 'Áudio & Acessórios',
                'shop_name' => 'Acoustics Brasil',
                'image_url' => 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop&q=60',
                'product_url' => 'https://shop.tiktok.com/view/product/demo-headphones',
                'affiliate_link' => 'https://shop.tiktok.com/affiliate/demo-headphones',
                'price' => 149.90,
                'currency' => 'BRL',
                'commission_rate' => 20.00,
                'commission_value' => 29.98,
                'sales_count' => 5120,
                'sales_velocity' => 115.00,
                'rating' => 4.78,
                'reviews_count' => 1450,
                'margin_score' => 80,
                'velocity_score' => 88,
                'viral_score' => 84,
                'overall_score' => 84,
            ]);

            // 4. Criativos Campeões com Rastreamento de ROI (AST-XXXX)
            $assetCode1 = 'AST-PROJ-' . strtoupper(Str::random(4));
            $assetCode2 = 'AST-FONE-' . strtoupper(Str::random(4));

            $winnerAsset = ContentAsset::create([
                'business_id' => $business->id,
                'tracking_code' => $assetCode1,
                'type' => ContentAsset::TYPE_VIDEO_SCRIPT,
                'platform' => 'tiktok',
                'title' => 'Vídeo Viral: Mini Projetor 4K - Transformando o Quarto num Cinema',
                'body' => 'Demonstração de 20s no quarto escuro mostrando projeção de 120 polegadas no teto.',
                'funnel_stage' => ContentAsset::STAGE_TOF_ATTRACTION,
                'angle_category' => 'dor_direta',
                'total_views' => 16200,
                'total_clicks' => 1150,
                'total_leads' => 0,
                'total_sales_count' => 24,
                'total_revenue_brl' => 6957.60,
                'roi_score' => 89.40,
                'status' => 'approved',
            ]);

            $secondAsset = ContentAsset::create([
                'business_id' => $business->id,
                'tracking_code' => $assetCode2,
                'type' => ContentAsset::TYPE_VIDEO_SCRIPT,
                'platform' => 'tiktok',
                'title' => 'Vídeo Review: Fone Noise-Cancelling vs Barulho do Dia a Dia',
                'body' => 'Gancho de quebra de padrão com secador de cabelo e isolamento acústico instantâneo.',
                'funnel_stage' => ContentAsset::STAGE_TOF_ATTRACTION,
                'angle_category' => 'curiosidade',
                'total_views' => 7400,
                'total_clicks' => 380,
                'total_leads' => 0,
                'total_sales_count' => 8,
                'total_revenue_brl' => 1199.20,
                'roi_score' => 61.50,
                'status' => 'approved',
            ]);

            // 5. Ledger de Conversões em Tempo Real
            ConversionEvent::create([
                'business_id' => $business->id,
                'content_asset_id' => $winnerAsset->id,
                'source_platform' => 'kiwify',
                'event_type' => ConversionEvent::EVENT_SALE_APPROVED,
                'external_transaction_id' => 'TX-DEMO-' . Str::upper(Str::random(8)),
                'gross_amount' => 289.90,
                'net_amount' => 63.78,
                'customer_metadata' => ['name' => 'Felipe Oliveira', 'email' => 'felipe.demo@example.com'],
                'occurred_at' => now()->subHours(1),
            ]);

            ConversionEvent::create([
                'business_id' => $business->id,
                'content_asset_id' => $winnerAsset->id,
                'source_platform' => 'tiktok_shop',
                'event_type' => ConversionEvent::EVENT_SALE_APPROVED,
                'external_transaction_id' => 'TX-DEMO-' . Str::upper(Str::random(8)),
                'gross_amount' => 289.90,
                'net_amount' => 63.78,
                'customer_metadata' => ['name' => 'Mariana Silveira', 'email' => 'mariana.demo@example.com'],
                'occurred_at' => now()->subHours(3),
            ]);

            ConversionEvent::create([
                'business_id' => $business->id,
                'content_asset_id' => $winnerAsset->id,
                'source_platform' => 'hotmart',
                'event_type' => ConversionEvent::EVENT_SALE_APPROVED,
                'external_transaction_id' => 'TX-DEMO-' . Str::upper(Str::random(8)),
                'gross_amount' => 289.90,
                'net_amount' => 63.78,
                'customer_metadata' => ['name' => 'Carlos Eduardo', 'email' => 'carlos.demo@example.com'],
                'occurred_at' => now()->subHours(6),
            ]);

            // 6. Tarefas no Kanban Híbrido
            Task::create([
                'business_id' => $business->id,
                'user_id' => $user->id,
                'title' => 'Mapear 3 fornecedores com envio nacional em 24h',
                'description' => 'Filtrar distribuidores oficiais com estoque em São Paulo para garantir entrega ultrarrápida.',
                'assignee' => TaskAssignee::Agent,
                'status' => TaskStatus::Backlog,
                'priority' => 'medium',
            ]);

            Task::create([
                'business_id' => $business->id,
                'user_id' => $user->id,
                'title' => 'IA gerando 5 novas variações de hooks para o ativo AST-PROJ01',
                'description' => 'O Gemini 3.8 está processando os padrões virais para criar variações de primeiros 3 segundos.',
                'assignee' => TaskAssignee::Agent,
                'status' => TaskStatus::InProgressAgent,
                'priority' => 'high',
            ]);

            Task::create([
                'business_id' => $business->id,
                'user_id' => $user->id,
                'title' => 'Gravar demonstração de 15 segundos do projetor ligado no quarto',
                'description' => 'Gravar com o celular na horizontal ou vertical no quarto escuro para publicar na vitrine da TikTok Shop.',
                'assignee' => TaskAssignee::User,
                'status' => TaskStatus::TodoUser,
                'priority' => 'high',
            ]);

            Task::create([
                'business_id' => $business->id,
                'user_id' => $user->id,
                'title' => 'Configuração inicial da vitrine TikTok Shop e diretrizes de marca',
                'description' => 'Definição das cores, tom de voz e configuração das categorias prioritárias.',
                'assignee' => TaskAssignee::Agent,
                'status' => TaskStatus::Done,
                'priority' => 'medium',
            ]);

            // 7. Fila de Supervisão (Human-in-the-Loop) com Badge de Auto-Otimização
            ApprovalQueue::create([
                'business_id' => $business->id,
                'user_id' => $user->id,
                'title' => "⚡ Escalação de Vencedor: {$assetCode1} (ROI: 89.4)",
                'type' => 'roi_scaling',
                'status' => ApprovalStatus::Pending,
                'priority' => 'high',
                'agent_confidence' => 0.98,
                'summary' => "O criativo {$assetCode1} atingiu R$ 6.957,60 em faturamento com ROI 89.4. O Gemini 3.8 desenhou 3 novos ganchos para escala viral instantânea.",
                'payload' => [
                    'badge' => 'Auto-Otimização de ROI',
                    'parent_tracking_code' => $assetCode1,
                    'parent_roi_score' => 89.40,
                    'parent_revenue_brl' => 6957.60,
                    'rationale' => 'O ativo apresentou CTR 32% acima da média e taxa de retenção de 68% nos primeiros 5 segundos. Escalando variações com foco em economia de espaço e experiência de cinema em casa.',
                    'hooks' => [
                        [
                            'hook' => 'Você ainda paga R$ 50 no ingresso de cinema? Fiz essa tela de 120 polegadas no meu quarto.',
                            'angle' => 'Dor Financeira & Economia',
                        ],
                        [
                            'hook' => 'Descobri o segredo das pessoas que transformam qualquer parede em uma TV 4K por menos de R$ 300.',
                            'angle' => 'Curiosidade Viral',
                        ],
                        [
                            'hook' => 'Se você joga videogame ou assiste filmes na cama, você PRECISA conhecer esse projetor.',
                            'angle' => 'Desejo & Conforto',
                        ],
                    ],
                    'script' => [
                        'scenes' => [
                            [
                                'time' => '0:00 - 0:03',
                                'visual' => 'Apaga a luz do quarto e liga o mini projetor com corte rápido.',
                                'audio' => 'Você ainda gasta fortuna em cinema? Olha o que eu fiz no teto do meu quarto.',
                            ],
                            [
                                'time' => '0:03 - 0:15',
                                'visual' => 'Mostra o tamanho compacto na palma da mão e a imagem 4K gigante no teto.',
                                'audio' => 'Ele conecta direto no Wi-Fi, já vem com Netflix e YouTube instalados e cabe na palma da sua mão.',
                            ],
                            [
                                'time' => '0:15 - 0:25',
                                'visual' => 'Aponta para o botão amarelo da TikTok Shop com selo de frete grátis.',
                                'audio' => 'O lote com desconto de lançamento tá no botão amarelo aqui embaixo. Aproveita antes de zerar o estoque!',
                            ],
                        ],
                    ],
                    'caption' => "Transformei meu quarto em um cinema 4K gastando menos de 300 reais! 🍿✨ Link com frete grátis e cupom exclusivo na sacola amarela abaixo 👇",
                    'hashtags' => ['#miniprojetor', '#cinemacaseiro', '#tiktokmademebuyit', '#achadinhos', '#tecnologia', '#spirandeli'],
                ],
            ]);

            // 8. Conversa Inaugural com o Diretor de Operações IA (Gemini 3.8)
            $conversation = AgentConversation::create([
                'uuid' => Str::uuid()->toString(),
                'user_id' => $user->id,
                'business_id' => $business->id,
                'title' => 'Diretoria Executiva · Gemini 3.8 Co-Pilot',
                'context_type' => 'business_chat',
                'status' => 'active',
                'model' => 'gemini-3.8',
                'context' => [
                    'business_name' => $business->name,
                    'archetype' => $business->archetype,
                    'top_product' => $prod1->title,
                ],
                'messages_count' => 2,
            ]);

            AgentMessage::create([
                'agent_conversation_id' => $conversation->id,
                'role' => 'user',
                'content' => 'Olá! Qual é o status atual da minha nova operação no SpirandeliEmpire?',
            ]);

            AgentMessage::create([
                'agent_conversation_id' => $conversation->id,
                'role' => 'model',
                'content' => "Olá, **{$userFirstName}**! Seja muito bem-vindo ao **SpirandeliEmpire**.\n\nEu sou o seu **Diretor de Operações (COO) Inteligente** baseado no Gemini 3.8. Já montei a infraestrutura da sua operação **{$business->name}** com produtos validados na TikTok Shop e funil de conversão ativo.\n\n📈 **Raio-X da Operação:**\n- **Receita Gerada:** R$ 6.957,60 acumulados através do criativo campeão `{$assetCode1}` (ROI Score: 89.4);\n- **Supervisão Humana:** 1 proposta de escalação com 3 novos hooks aguardando seu clique de aprovação na Fila de Supervisão;\n- **Kanban Ativo:** 4 tarefas distribuídas entre trabalho do agente e suas gravações de 15 segundos;\n- **Webhooks Integrados:** Ledger pronto para receber postbacks da Kiwify, Hotmart, TikTok Shop e Stripe.\n\nComo posso acelerar seus resultados agora? Posso **minerar novos produtos virais**, **gerar mais roteiros de alta conversão** ou **otimizar as métricas do seu funil**!",
            ]);

            // 9. Registro de Log de Auditoria
            AgentLog::record(
                $user->id,
                'starter_kit_provisioned',
                "Venture demonstrativo \"{$business->name}\" provisionado com sucesso para {$user->name}.",
                LogLevel::Success,
                ['archetype' => $business->archetype],
                ['business_id' => $business->id]
            );

            return $business->load(['automations', 'tiktokProducts', 'contentAssets']);
        });
    }
}
