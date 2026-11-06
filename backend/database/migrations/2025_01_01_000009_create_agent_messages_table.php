<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('agent_messages', function (Blueprint $table) {
            $table->id();
            $table->foreignId('agent_conversation_id')->constrained()->cascadeOnDelete();

            // user | model | tool  (o service mapeia para os roles da API Gemini)
            $table->string('role', 16);
            $table->longText('content')->nullable()->comment('Texto renderizável no chat');
            $table->json('parts')->nullable()->comment('Parts brutos da API (text, functionCall, functionResponse) para replay fiel');

            $table->string('tool_name', 96)->nullable();
            $table->json('tool_args')->nullable();
            $table->json('tool_result')->nullable();
            $table->boolean('tool_failed')->default(false);

            $table->unsignedInteger('prompt_tokens')->nullable();
            $table->unsignedInteger('completion_tokens')->nullable();
            $table->string('finish_reason', 32)->nullable();
            $table->unsignedInteger('latency_ms')->nullable();
            $table->timestamps();

            $table->index(['agent_conversation_id', 'id']);
            $table->index('tool_name');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('agent_messages');
    }
};
