<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('businesses', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->string('name');
            $table->string('slug');
            // tiktok_shop_affiliate | dropshipping | digital_product | content_channel | custom
            $table->string('type', 48)->default('custom');
            $table->string('status', 32)->default('draft'); // draft | planning | active | paused | archived
            $table->string('niche')->nullable();
            $table->text('description')->nullable();

            // Modelagem estruturada pelo Gemini via Function Calling
            $table->json('canvas')->nullable()->comment('Business Model Canvas (9 blocos)');
            $table->json('brand_rules')->nullable()->comment('Tom de voz, proibições, CTAs, identidade');
            $table->json('goals')->nullable()->comment('Metas SMART (receita, vídeos/semana, GMV)');
            $table->json('acquisition_channels')->nullable();
            $table->json('automation_playbook')->nullable()->comment('Passos do playbook autônomo');
            $table->json('kpis')->nullable()->comment('Definição dos KPIs e metas');
            $table->json('metrics')->nullable()->comment('Snapshot atual das métricas');
            $table->text('ai_summary')->nullable();

            $table->boolean('automation_enabled')->default(false);
            $table->timestamp('activated_at')->nullable();
            $table->timestamps();
            $table->softDeletes();

            $table->unique(['user_id', 'slug']);
            $table->index(['user_id', 'status']);
            $table->index(['type', 'status']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('businesses');
    }
};
