<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('approval_queues', function (Blueprint $table) {
            $table->id();
            $table->foreignId('business_id')->constrained()->cascadeOnDelete();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->foreignId('task_id')->nullable()->constrained()->nullOnDelete();
            $table->nullableMorphs('approvable'); // ex.: TikTokProduct

            // tiktok_content_package | business_plan | strategy_change | calendar_action | generic
            $table->string('type', 48)->default('generic');
            $table->string('title');
            $table->text('summary')->nullable();

            // Pacote entregue pelo agente. Para TikTok:
            // { product, hooks[3], script, visual_prompts[], caption, hashtags[], cta, seo_keywords[] }
            $table->json('payload');

            // pending | revision_requested | revising | approved | scheduled | rejected | expired
            $table->string('status', 32)->default('pending');
            $table->string('priority', 16)->default('medium');
            $table->decimal('agent_confidence', 4, 3)->nullable()->comment('0.000 - 1.000');

            $table->text('reviewer_feedback')->nullable()->comment('Último pedido de ajuste / motivo de rejeição');
            $table->unsignedSmallInteger('revision_count')->default(0);
            $table->json('revision_history')->nullable()->comment('[{at, feedback, section, previous_payload_hash}]');

            $table->timestamp('reviewed_at')->nullable();
            $table->timestamp('scheduled_for')->nullable()->comment('Data/hora de postagem aprovada');
            $table->timestamp('expires_at')->nullable();
            $table->timestamps();

            $table->index(['user_id', 'status', 'created_at']);
            $table->index(['business_id', 'status']);
            $table->index(['type', 'status']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('approval_queues');
    }
};
