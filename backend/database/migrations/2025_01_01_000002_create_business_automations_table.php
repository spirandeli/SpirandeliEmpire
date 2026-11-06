<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('business_automations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('business_id')->constrained()->cascadeOnDelete();
            // tiktok_product_mining | affiliate_content_generation | calendar_sync | performance_review | custom
            $table->string('type', 64);
            $table->string('name');
            $table->string('cron_expression', 64)->default('0 */6 * * *');
            $table->string('timezone', 64)->default('America/Sao_Paulo');
            $table->boolean('is_enabled')->default(true);
            $table->json('config')->nullable()->comment('Parâmetros: categorias, min_commission, max_items, etc.');

            $table->timestamp('last_run_at')->nullable();
            $table->timestamp('next_run_at')->nullable();
            $table->string('last_status', 24)->nullable(); // success | failed | running | skipped
            $table->text('last_error')->nullable();
            $table->unsignedInteger('run_count')->default(0);
            $table->unsignedInteger('failure_count')->default(0);
            $table->timestamps();

            $table->unique(['business_id', 'type', 'name']);
            $table->index(['is_enabled', 'next_run_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('business_automations');
    }
};
