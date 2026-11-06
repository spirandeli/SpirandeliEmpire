<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Console em tempo real do agente (Kanban / Dashboard). Append-only.
        Schema::create('agent_logs', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->foreignId('business_id')->nullable()->constrained()->cascadeOnDelete();
            $table->foreignId('task_id')->nullable()->constrained()->nullOnDelete();
            $table->foreignId('agent_conversation_id')->nullable()->constrained()->nullOnDelete();
            $table->foreignId('business_automation_id')->nullable()->constrained()->nullOnDelete();

            $table->string('level', 16)->default('info'); // debug | info | success | warning | error
            // job_started | job_finished | tool_call | tool_result | gemini_request | approval_submitted | integration | ...
            $table->string('event', 64);
            $table->string('message', 1000);
            $table->json('context')->nullable();
            $table->unsignedInteger('duration_ms')->nullable();
            $table->timestamp('created_at')->useCurrent();

            $table->index(['user_id', 'id']);
            $table->index(['business_id', 'id']);
            $table->index(['task_id', 'id']);
            $table->index(['level', 'created_at']);
            $table->index('event');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('agent_logs');
    }
};
