<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('content_assets', function (Blueprint $table) {
            $table->id();
            $table->foreignId('business_id')->constrained()->cascadeOnDelete();
            $table->foreignId('tiktok_product_id')->nullable()->constrained('tiktok_products')->nullOnDelete();
            $table->foreignId('approval_queue_id')->nullable()->constrained('approval_queues')->nullOnDelete();
            $table->foreignId('parent_id')->nullable()->constrained('content_assets')->nullOnDelete()
                ->comment('Versão anterior (revisões pedidas pelo usuário)');

            // hook | video_script | visual_prompt | caption | hashtags | cta | thumbnail_prompt
            $table->string('type', 32);
            $table->string('platform', 24)->default('tiktok');
            $table->string('title')->nullable();
            $table->longText('body')->nullable();
            $table->json('content')->nullable()->comment('Estrutura: cenas, timings, variações de hooks');
            $table->unsignedSmallInteger('version')->default(1);
            $table->boolean('is_selected')->default(false)->comment('Hook/variação escolhida');

            // draft | pending_approval | approved | rejected | published | superseded
            $table->string('status', 24)->default('draft');
            $table->timestamp('scheduled_at')->nullable();
            $table->timestamp('published_at')->nullable();
            $table->string('external_url')->nullable();
            $table->json('metadata')->nullable()->comment('Modelo usado, tokens, métricas de performance');
            $table->timestamps();

            $table->index(['business_id', 'type', 'status']);
            $table->index(['tiktok_product_id', 'type']);
            $table->index('approval_queue_id');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('content_assets');
    }
};
