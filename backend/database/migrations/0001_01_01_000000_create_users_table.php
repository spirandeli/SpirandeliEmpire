<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

/**
 * Substitui a migration padrão do skeleton (sessões ficam no Redis, sem tabela `sessions`).
 */
return new class extends Migration
{
    public function up(): void
    {
        Schema::create('users', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('email')->unique();
            $table->timestamp('email_verified_at')->nullable();
            $table->string('password');
            $table->string('timezone', 64)->default('America/Sao_Paulo');
            $table->string('locale', 8)->default('pt_BR');
            $table->boolean('agent_enabled')->default(true)->comment('Kill-switch global dos workers autônomos do usuário');
            $table->json('settings')->nullable()->comment('Preferências: horário de trabalho, janelas de gravação, notificações');
            $table->timestamp('last_login_at')->nullable();
            $table->rememberToken();
            $table->timestamps();
        });

        Schema::create('password_reset_tokens', function (Blueprint $table) {
            $table->string('email')->primary();
            $table->string('token');
            $table->timestamp('created_at')->nullable();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('password_reset_tokens');
        Schema::dropIfExists('users');
    }
};
