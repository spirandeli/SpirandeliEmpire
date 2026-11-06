<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('agent_conversations', function (Blueprint $table) {
            $table->id();
            $table->uuid('uuid')->unique();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->foreignId('business_id')->nullable()->constrained()->cascadeOnDelete();

            $table->string('title')->nullable();
            // incubator (co-criação) | business_chat (operacional) | autonomous_run (jobs em background)
            $table->string('context_type', 24)->default('incubator');
            $table->string('status', 16)->default('active'); // active | archived
            $table->string('model', 64)->default('gemini-3.8');

            $table->json('context')->nullable()->comment('Snapshot de contexto injetado no system prompt');
            $table->unsignedBigInteger('prompt_tokens')->default(0);
            $table->unsignedBigInteger('completion_tokens')->default(0);
            $table->unsignedInteger('messages_count')->default(0);
            $table->timestamp('last_message_at')->nullable();
            $table->timestamps();

            $table->index(['user_id', 'context_type', 'last_message_at']);
            $table->index(['business_id', 'last_message_at']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('agent_conversations');
    }
};
