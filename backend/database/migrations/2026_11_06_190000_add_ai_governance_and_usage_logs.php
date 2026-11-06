<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // 1. Campos de Governança de IA na tabela `users`
        Schema::table('users', function (Blueprint $table) {
            $table->boolean('is_admin')->default(false)->after('agent_enabled');
            $table->boolean('is_ai_active')->default(true)->after('is_admin');
            $table->unsignedBigInteger('monthly_token_limit')->default(2000000)->after('is_ai_active');
            $table->unsignedBigInteger('tokens_used_this_month')->default(0)->after('monthly_token_limit');
        });

        // 2. Tabela de rastreamento de custos e consumo de tokens por chamada
        Schema::create('ai_usage_logs', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->foreignId('business_id')->nullable()->constrained()->nullOnDelete();
            $table->foreignId('agent_conversation_id')->nullable()->constrained()->nullOnDelete();
            $table->string('model', 60)->default('gemini-3.8');
            $table->string('context', 60)->default('chat');
            $table->unsignedInteger('prompt_tokens')->default(0);
            $table->unsignedInteger('completion_tokens')->default(0);
            $table->unsignedInteger('total_tokens')->default(0);
            $table->decimal('estimated_cost_usd', 10, 6)->default(0.000000);
            $table->unsignedInteger('latency_ms')->default(0);
            $table->timestamps();

            $table->index(['user_id', 'created_at']);
            $table->index(['business_id', 'created_at']);
            $table->index(['model', 'created_at']);
        });

        // 3. Índice complementar em approval_queues para busca por status e prioridade
        Schema::table('approval_queues', function (Blueprint $table) {
            $table->index(['status', 'priority'], 'approval_queues_status_priority_idx');
        });
    }

    public function down(): void
    {
        Schema::table('approval_queues', function (Blueprint $table) {
            $table->dropIndex('approval_queues_status_priority_idx');
        });

        Schema::dropIfExists('ai_usage_logs');

        Schema::table('users', function (Blueprint $table) {
            $table->dropColumn([
                'is_admin',
                'is_ai_active',
                'monthly_token_limit',
                'tokens_used_this_month',
            ]);
        });
    }
};
