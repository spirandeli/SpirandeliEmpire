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

        // 2. Initial Four Strategic Businesses
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
        ];

        foreach ($memories as $mem) {
            JeffreyMemory::firstOrCreate(['key' => $mem['key']], $mem);
        }
    }
}

