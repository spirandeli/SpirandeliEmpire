<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('tasks', function (Blueprint $table) {
            $table->id();
            $table->foreignId('business_id')->constrained()->cascadeOnDelete();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->foreignId('parent_id')->nullable()->constrained('tasks')->nullOnDelete();

            $table->string('title');
            $table->text('description')->nullable();

            // Executor: 'agent' (Gemini worker) | 'user' (humano)
            $table->string('assignee', 16)->default('user');
            // Kanban: backlog | in_progress_agent | awaiting_supervision | todo_user | done
            $table->string('status', 32)->default('backlog');
            $table->string('priority', 16)->default('medium'); // low | medium | high | urgent
            $table->string('source', 16)->default('user');      // user | agent
            $table->unsignedInteger('position')->default(0)->comment('Ordenação dentro da coluna do Kanban');

            $table->timestamp('due_at')->nullable();
            $table->timestamp('scheduled_at')->nullable()->comment('Início agendado (ex.: gravação)');
            $table->timestamp('started_at')->nullable();
            $table->timestamp('completed_at')->nullable();

            $table->string('agent_action', 64)->nullable()->comment('Handler do worker: mine_products, generate_content...');
            $table->json('payload')->nullable()->comment('Parâmetros de execução para o agente');
            $table->json('result')->nullable()->comment('Resultado estruturado da execução');
            $table->text('failure_reason')->nullable();
            $table->unsignedTinyInteger('attempts')->default(0);

            // Referências para eventos/lembretes externos criados pelo agente
            $table->string('external_calendar_provider', 24)->nullable(); // google | apple
            $table->string('external_calendar_id')->nullable();

            $table->timestamps();
            $table->softDeletes();

            $table->index(['business_id', 'status', 'position']);
            $table->index(['user_id', 'assignee', 'status']);
            $table->index(['assignee', 'status', 'due_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('tasks');
    }
};
