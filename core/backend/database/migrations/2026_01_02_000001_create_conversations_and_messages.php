<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Projects table (Workspaces managed by Empire OS)
        if (!Schema::hasTable('projects')) {
            Schema::create('projects', function (Blueprint $table) {
                $table->id();
                $table->string('name');
                $table->string('slug')->unique();
                $table->text('description')->nullable();
                $table->string('path'); // Authorized local workspace path
                $table->string('git_repo')->nullable();
                $table->string('git_branch')->default('main');
                $table->string('status')->default('active'); // active, paused, archived
                $table->string('stack')->nullable(); // laravel, vue, python, node, docker
                $table->jsonb('settings')->nullable();
                $table->timestamps();
            });
        }

        // Conversations table (Persistent chat sessions)
        if (!Schema::hasTable('conversations')) {
            Schema::create('conversations', function (Blueprint $table) {
                $table->id();
                $table->foreignId('user_id')->nullable()->constrained('users')->onDelete('set null');
                $table->string('title')->default('Nova Conversa');
                $table->foreignId('business_id')->nullable()->constrained('businesses')->onDelete('set null');
                $table->foreignId('project_id')->nullable()->constrained('projects')->onDelete('set null');
                $table->boolean('is_pinned')->default(false);
                $table->jsonb('context_metadata')->nullable();
                $table->timestamps();
            });
        }

        // Messages table (Chronological messages in conversations)
        if (!Schema::hasTable('messages')) {
            Schema::create('messages', function (Blueprint $table) {
                $table->id();
                $table->foreignId('conversation_id')->constrained('conversations')->onDelete('cascade');
                $table->string('role'); // user, assistant, system, tool
                $table->text('content');
                $table->string('provider')->nullable(); // gemini, openai, ollama, llama
                $table->string('model')->nullable();
                $table->integer('latency_ms')->default(0);
                $table->jsonb('tokens')->nullable();
                $table->jsonb('tool_calls')->nullable();
                $table->jsonb('tool_results')->nullable();
                $table->text('error_message')->nullable();
                $table->boolean('fallback_used')->default(false);
                $table->string('fallback_reason')->nullable();
                $table->timestamps();

                $table->index('conversation_id');
            });
        }

        // Specialized Agents (Jeffrey, Software Engineer, DevOps, etc.)
        if (!Schema::hasTable('agents')) {
            Schema::create('agents', function (Blueprint $table) {
                $table->id();
                $table->string('name');
                $table->string('slug')->unique();
                $table->string('role');
                $table->text('description')->nullable();
                $table->string('model')->default('llama3.2:3b');
                $table->text('system_prompt')->nullable();
                $table->jsonb('authorized_tools')->nullable();
                $table->jsonb('authorized_projects')->nullable();
                $table->boolean('is_active')->default(true);
                $table->timestamps();
            });
        }

        // Audit Logs (Security & Compliance)
        if (!Schema::hasTable('audit_logs')) {
            Schema::create('audit_logs', function (Blueprint $table) {
                $table->id();
                $table->foreignId('user_id')->nullable()->constrained('users')->onDelete('set null');
                $table->string('action');
                $table->string('resource_type')->nullable();
                $table->string('resource_id')->nullable();
                $table->string('ip_address')->nullable();
                $table->jsonb('details')->nullable();
                $table->timestamps();
            });
        }
    }

    public function down(): void
    {
        Schema::dropIfExists('audit_logs');
        Schema::dropIfExists('agents');
        Schema::dropIfExists('messages');
        Schema::dropIfExists('conversations');
        Schema::dropIfExists('projects');
    }
};
