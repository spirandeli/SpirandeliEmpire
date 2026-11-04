<?php

namespace Database\Seeders;

use App\Models\Business;
use App\Models\JeffreyMemory;
use App\Models\User;
use Illuminate\Database\Seeder;
use Illuminate\Support\Facades\Hash;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        // 1. Initial Admin User
        $adminEmail = env('ADMIN_EMAIL', 'admin@yourdomain.com');
        $adminPassword = env('ADMIN_INITIAL_PASSWORD', 'ChangeMeOnFirstLogin!2026');

        User::firstOrCreate(
            ['email' => $adminEmail],
            [
                'name' => 'Empire Commander',
                'password' => Hash::make($adminPassword),
                'role' => 'administrator',
            ]
        );

        // 2. Initial Strategic Businesses (4 originais + 4 afiliados + 1 automação TikTok)
        $initialBusinesses = [
            [
                'name' => 'RISADA.exe',
                'slug' => 'risada-exe',
                'category' => 'YouTube Dark Channel',
                'description' => 'Canal de histórias bíblicas com animações/ilustrações originais, voz brasileira masculina e roteiros biblicamente fiéis.',
                'status' => 'provisioning',
                'template_used' => 'youtube-dark-bible',
                'storage_path' => 'businesses/risada-exe',
                'budget_limit_brl' => 60.00,
            ],
            [
                'name' => 'KDP Factory',
                'slug' => 'kdp-factory',
                'category' => 'Amazon KDP Publishing',
                'description' => 'Produção e publicação de eBooks, devocionais, planos de leitura bíblica e livros infantis educativos.',
                'status' => 'provisioning',
                'template_used' => 'amazon-kdp-publishing',
                'storage_path' => 'businesses/kdp-factory',
                'budget_limit_brl' => 50.00,
            ],
            [
                'name' => 'Digital Products Factory',
                'slug' => 'digital-products',
                'category' => 'Digital Goods & PDFs',
                'description' => 'Estudos bíblicos em PDF, planners devocionais, quiz bíblico e apostilas de alta qualidade.',
                'status' => 'provisioning',
                'template_used' => 'digital-products-pdf',
                'storage_path' => 'businesses/digital-products',
                'budget_limit_brl' => 40.00,
            ],
            [
                'name' => 'Printable Factory',
                'slug' => 'printable-factory',
                'category' => 'Printables & Art',
                'description' => 'Quadros, cartões, atividades infantis e artes originais de alta resolução para impressão.',
                'status' => 'provisioning',
                'template_used' => 'printable-art',
                'storage_path' => 'businesses/printable-factory',
                'budget_limit_brl' => 30.00,
            ],

            // ── Negócios de Afiliado ──────────────────────────────────────────
            [
                'name' => 'TikTok Shop Afiliados',
                'slug' => 'tiktok-shop-afiliados',
                'category' => 'Affiliate Marketing',
                'description' => 'Pipeline 100% automatizado com IA local para criação de vídeos faceless 9:16 para TikTok Shop Affiliates. Roteiro por Ollama (Llama 3 8B), narração por XTTS v2 com clonagem de voz, renderização vertical via MoviePy + FFmpeg. Orquestrado pelo n8n (cron 3x/dia, máx. 9 vídeos/dia). Comissões de 5–20% por venda.',
                'status' => 'provisioning',
                'template_used' => 'affiliate-tiktok-shop',
                'storage_path' => 'businesses/tiktok-shop-afiliados',
                'budget_limit_brl' => 30.00,
            ],
            [
                'name' => 'Shopee Afiliados',
                'slug' => 'shopee-afiliados',
                'category' => 'Affiliate Marketing',
                'description' => 'Programa de afiliados Shopee: curadoria de produtos com alto potencial de conversão, geração de links rastreáveis, publicação em redes sociais, grupos de WhatsApp e Telegram para maximizar comissões.',
                'status' => 'provisioning',
                'template_used' => 'affiliate-shopee',
                'storage_path' => 'businesses/shopee-afiliados',
                'budget_limit_brl' => 20.00,
            ],
            [
                'name' => 'Amazon Afiliados',
                'slug' => 'amazon-afiliados',
                'category' => 'Affiliate Marketing',
                'description' => 'Programa Amazon Associados: criação de conteúdo de review, comparativos e listas de produtos com links de afiliado, integrado ao canal YouTube e blog para geração de renda passiva via comissões.',
                'status' => 'provisioning',
                'template_used' => 'affiliate-amazon',
                'storage_path' => 'businesses/amazon-afiliados',
                'budget_limit_brl' => 20.00,
            ],
            [
                'name' => 'AliExpress Afiliados',
                'slug' => 'aliexpress-afiliados',
                'category' => 'Affiliate Marketing',
                'description' => 'Programa de afiliados AliExpress (via Admitad ou portal oficial): curadoria de produtos importados, criação de conteúdo de unboxing e reviews, divulgação via redes sociais e newsletters para geração de comissões.',
                'status' => 'provisioning',
                'template_used' => 'affiliate-aliexpress',
                'storage_path' => 'businesses/aliexpress-afiliados',
                'budget_limit_brl' => 20.00,
            ],
        ];

        foreach ($initialBusinesses as $bizData) {
            Business::firstOrCreate(['slug' => $bizData['slug']], $bizData);
        }

        // 3. Operational Memories for Jeffrey AI
        $memories = [
            [
                'category' => 'preference',
                'key' => 'financial_cap',
                'content' => 'O orçamento total da infraestrutura e operações não deve ultrapassar R$ 200,00 por mês sem autorização explícita do proprietário.',
            ],
            [
                'category' => 'preference',
                'key' => 'local_first_policy',
                'content' => 'Priorizar modelos open-source executados localmente (Ollama, Piper TTS, FFmpeg). Nunca contratar APIs externas sem aprovação.',
            ],
            [
                'category' => 'guideline',
                'key' => 'biblical_accuracy',
                'content' => 'Para o canal de histórias bíblicas (RISADA.exe) e KDP: Jamais inventar versículos. Respeitar a fidelidade das Escrituras e verificar direitos autorais.',
            ],
            [
                'category' => 'safety',
                'key' => 'human_approval',
                'content' => 'Ações críticas, despesas financeiras, publicação de conteúdos e deleção de dados exigem aprovação humana prévia.',
            ],
            [
                'category' => 'guideline',
                'key' => 'tiktok_shop_guardrails',
                'content' => 'TikTok Shop Afiliados: máximo 9 vídeos/dia (anti-shadowban). Todo vídeo publicado deve conter #parceria ou disclosure de afiliado. Nenhum roteiro pode fazer afirmações médicas, jurídicas ou de ganho garantido. XTTS v2 requer arquivo de referência de voz em assets/voice_reference.wav. Fallback para Piper TTS se XTTS indisponível.',
            ],
        ];

        foreach ($memories as $mem) {
            JeffreyMemory::firstOrCreate(['key' => $mem['key']], $mem);
        }
    }
}

