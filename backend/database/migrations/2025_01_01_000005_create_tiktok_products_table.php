<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('tiktok_products', function (Blueprint $table) {
            $table->id();
            $table->foreignId('business_id')->constrained()->cascadeOnDelete();

            $table->string('external_id', 64)->comment('ID do produto na TikTok Shop');
            $table->string('source', 32)->default('api'); // api | scraper | webhook | manual
            $table->string('title', 500);
            $table->string('category')->nullable();
            $table->string('shop_name')->nullable();
            $table->text('image_url')->nullable();
            $table->text('product_url')->nullable();
            $table->text('affiliate_link')->nullable();

            $table->decimal('price', 12, 2)->default(0);
            $table->char('currency', 3)->default('BRL');
            $table->decimal('commission_rate', 5, 2)->default(0)->comment('% de comissão');
            $table->decimal('commission_value', 12, 2)->default(0)->comment('Comissão estimada por venda');
            $table->unsignedInteger('sales_count')->default(0);
            $table->decimal('sales_velocity', 10, 2)->default(0)->comment('Vendas/dia (janela recente)');
            $table->decimal('rating', 3, 2)->nullable();
            $table->unsignedInteger('reviews_count')->default(0);

            // Scores 0-100 (calculados pelo serviço + refinados pelo Gemini)
            $table->unsignedTinyInteger('margin_score')->default(0);
            $table->unsignedTinyInteger('velocity_score')->default(0);
            $table->unsignedTinyInteger('viral_score')->default(0);
            $table->unsignedTinyInteger('overall_score')->default(0);

            // mined | analyzing | selected | content_ready | published | discarded
            $table->string('status', 24)->default('mined');
            $table->json('raw_data')->nullable()->comment('Payload bruto da fonte');
            $table->json('ai_analysis')->nullable()->comment('Racional do Gemini: ângulo, público, riscos');
            $table->timestamp('mined_at')->nullable();
            $table->timestamp('selected_at')->nullable();
            $table->timestamps();

            $table->unique(['business_id', 'external_id']);
            $table->index(['business_id', 'status', 'overall_score']);
            $table->index(['business_id', 'mined_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('tiktok_products');
    }
};
