<?php

namespace Database\Seeders;

use App\Enums\ApprovalStatus;
use App\Enums\BusinessStatus;
use App\Enums\TaskAssignee;
use App\Enums\TaskStatus;
use App\Models\ApprovalQueue;
use App\Models\Business;
use App\Models\BusinessAutomation;
use App\Models\ContentAsset;
use App\Models\ConversionEvent;
use App\Models\Task;
use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        // 1. Usuário Administrador Executivo
        $admin = User::firstOrCreate(
            ['email' => 'admin@spirandeli.com'],
            [
                'name' => 'Alexander Spirandeli (Admin)',
                'password' => Hash::make('Spirandeli2026!'),
                'timezone' => 'America/Sao_Paulo',
                'agent_enabled' => true,
                'is_admin' => true,
                'is_ai_active' => true,
                'monthly_token_limit' => 10000000,
                'tokens_used_this_month' => 42000,
            ]
        );

        // 2. Negócio 1: Afiliados TikTok Shop
        $tiktokBiz = Business::firstOrCreate(
            ['user_id' => $admin->id, 'slug' => 'tiktok-viral-gadgets'],
            [
                'name' => 'TikTok Viral Gadgets',
                'type' => Business::TYPE_TIKTOK_SHOP_AFFILIATE,
                'archetype' => Business::ARCHETYPE_AFFILIATE_TIKTOK,
                'status' => BusinessStatus::Active,
                'niche' => 'Tecnologia & Utilidades Virais',
                'description' => 'Operação de alta escala minerando produtos hipnóticos para a TikTok Shop Brasil.',
                'automation_enabled' => true,
                'north_star_metric' => 'commission_volume',
                'target_kpi_value' => 15000.00,
                'canvas' => [
                    'value_propositions' => ['Demonstração hipnótica de produtos que solucionam dores imediatas.'],
                    'customer_segments' => ['Público jovem e adulto entre 18 e 35 anos que consome compras por impulso.'],
                    'channels' => ['TikTok Orgânico', 'TikTok Shop Vitrine', 'Shorts / Reels'],
                    'revenue_streams' => ['Comissão direta por venda (15% a 25%).'],
                ],
                'brand_rules' => [
                    'tone_of_voice' => 'Enérgico, dinâmico, autêntico e focado em demonstrar o benefício em 3 segundos.',
                    'target_audience' => 'Compradores de novidades virais no Brasil.',
                ],
            ]
        );

        // Automações padrão do negócio
        BusinessAutomation::firstOrCreate(
            ['business_id' => $tiktokBiz->id, 'type' => BusinessAutomation::TYPE_TIKTOK_MINING],
            [
                'name' => 'Mineração de Produtos Virais (6 em 6 horas)',
                'cron_expression' => '0 */6 * * *',
                'is_enabled' => true,
            ]
        );

        // 3. Negócio 2: Infoproduto de Alta Conversão
        $infoBiz = Business::firstOrCreate(
            ['user_id' => $admin->id, 'slug' => 'mecanismo-funil-lucrativo'],
            [
                'name' => 'Mecanismo Funil Lucrativo',
                'type' => 'custom',
                'archetype' => Business::ARCHETYPE_INFOPRODUCT,
                'status' => BusinessStatus::Active,
                'niche' => 'Marketing & Vendas Digitais',
                'description' => 'Infoproduto ticket médio (R$ 197) com VSL e recuperação via WhatsApp.',
                'automation_enabled' => true,
                'north_star_metric' => 'roas',
                'target_kpi_value' => 3.50,
            ]
        );

        // 4. Criativos e Ativos com Atribuição de ROI
        $winnerAsset = ContentAsset::firstOrCreate(
            ['business_id' => $tiktokBiz->id, 'tracking_code' => 'AST-GLOW01'],
            [
                'type' => ContentAsset::TYPE_VIDEO_SCRIPT,
                'platform' => 'tiktok',
                'title' => 'Vídeo Viral: Fita LED Inteligente com Sensor',
                'body' => 'Demonstração de 20s mostrando a instalação instantânea e iluminação sincronizada com música.',
                'funnel_stage' => ContentAsset::STAGE_TOF_ATTRACTION,
                'angle_category' => 'dor_direta',
                'total_views' => 14500,
                'total_clicks' => 920,
                'total_leads' => 0,
                'total_sales_count' => 18,
                'total_revenue_brl' => 3546.00,
                'roi_score' => 86.50,
                'status' => 'approved',
            ]
        );

        $secondAsset = ContentAsset::firstOrCreate(
            ['business_id' => $tiktokBiz->id, 'tracking_code' => 'AST-CLEAN02'],
            [
                'type' => ContentAsset::TYPE_VIDEO_SCRIPT,
                'platform' => 'tiktok',
                'title' => 'Vídeo Review: Mini Aspirador Portátil para Carro',
                'body' => 'Hook de quebra de padrão com poeira no teclado de notebook e assento do carro.',
                'funnel_stage' => ContentAsset::STAGE_TOF_ATTRACTION,
                'angle_category' => 'curiosidade',
                'total_views' => 6200,
                'total_clicks' => 310,
                'total_leads' => 0,
                'total_sales_count' => 5,
                'total_revenue_brl' => 495.00,
                'roi_score' => 52.00,
                'status' => 'approved',
            ]
        );

        // 5. Ledger de Conversões
        ConversionEvent::firstOrCreate(
            ['business_id' => $tiktokBiz->id, 'external_transaction_id' => 'SEED-TX-001'],
            [
                'content_asset_id' => $winnerAsset->id,
                'source_platform' => 'kiwify',
                'event_type' => ConversionEvent::EVENT_SALE_APPROVED,
                'gross_amount' => 197.00,
                'net_amount' => 157.60,
                'customer_metadata' => ['name' => 'Guilherme Ferreira', 'email' => 'guilherme@email.com'],
                'occurred_at' => now()->subHours(2),
            ]
        );

        ConversionEvent::firstOrCreate(
            ['business_id' => $tiktokBiz->id, 'external_transaction_id' => 'SEED-TX-002'],
            [
                'content_asset_id' => $winnerAsset->id,
                'source_platform' => 'hotmart',
                'event_type' => ConversionEvent::EVENT_SALE_APPROVED,
                'gross_amount' => 197.00,
                'net_amount' => 157.60,
                'customer_metadata' => ['name' => 'Beatriz Santos', 'email' => 'beatriz@email.com'],
                'occurred_at' => now()->subHours(5),
            ]
        );

        // 6. Tarefas no Kanban
        Task::firstOrCreate(
            ['business_id' => $tiktokBiz->id, 'title' => 'Gravar 2 variações do produto AST-GLOW01'],
            [
                'user_id' => $admin->id,
                'description' => 'Gravar com a câmera do celular no ambiente escuro mostrando o reflexo da fita LED atrás do monitor.',
                'assignee' => TaskAssignee::User,
                'status' => TaskStatus::TodoUser,
                'priority' => 'high',
            ]
        );

        Task::firstOrCreate(
            ['business_id' => $tiktokBiz->id, 'title' => 'Mineração algorítmica de fornecedores nacionais'],
            [
                'user_id' => $admin->id,
                'description' => 'Filtrar lojas brasileiras com estoque local em São Paulo e envio em até 24 horas.',
                'assignee' => TaskAssignee::Agent,
                'status' => TaskStatus::InProgressAgent,
                'priority' => 'medium',
            ]
        );

        // 7. Entrega Pendente na Fila de Supervisão (Human-in-the-Loop)
        ApprovalQueue::firstOrCreate(
            ['business_id' => $tiktokBiz->id, 'title' => '⚡ Escalação de Vencedor: AST-GLOW01 (ROI: 86.5)'],
            [
                'user_id' => $admin->id,
                'type' => 'roi_scaling',
                'status' => ApprovalStatus::Pending,
                'priority' => 'high',
                'agent_confidence' => 0.96,
                'summary' => 'O ativo AST-GLOW01 gerou R$ 3.546,00 em faturamento com 18 vendas. O Gemini 3.8 formulou 3 novos ganchos para escala viral.',
                'payload' => [
                    'badge' => 'Auto-Otimização de ROI',
                    'parent_tracking_code' => 'AST-GLOW01',
                    'parent_roi_score' => 86.50,
                    'parent_revenue_brl' => 3546.00,
                    'new_hooks' => [
                        'Hook 1: "O que acontece se você colocar essa fita atrás da TV sem usar tomada?"',
                        'Hook 2: "99% das pessoas compram luz comum cara, mas esse truque de R$ 49 muda seu quarto."',
                        'Hook 3: "Se você joga videogame no escuro, seus olhos precisam desse acessório agora."',
                    ],
                    'script_summary' => 'Gravação rápida de 18 segundos com troca de cores via aplicativo no smartphone.',
                ],
            ]
        );
    }
}
