<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::dropIfExists('language_vocabulary_vault');
        Schema::dropIfExists('language_daily_sessions');
        Schema::dropIfExists('language_profiles');

        // 1. Perfis de Aprendizado de Idiomas do Usuário
        Schema::create('language_profiles', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->string('target_language', 50)->default('Inglês');
            $table->string('learning_focus', 100)->default('business'); // business, general, dev, travel
            $table->string('cefr_level', 10)->default('UNSET'); // UNSET, A1, A2, B1, B2, C1, C2
            $table->json('study_days')->nullable(); // ["MON","WED","FRI"] ou ["ALL"]
            $table->string('preferred_time', 10)->default('07:30'); // Ex: 07:30
            $table->unsignedInteger('daily_duration_minutes')->default(15);
            $table->unsignedInteger('streak_days')->default(0);
            $table->date('last_activity_date')->nullable();
            $table->json('calendar_sync_ids')->nullable(); // { "google_event_id": "...", "apple_uid": "..." }
            $table->json('weaknesses_diagnosis')->nullable(); // Pontos cegos detectados pelo Gemini 3.8 Flash
            $table->boolean('is_active')->default(true);
            $table->timestamps();

            $table->index(['user_id', 'is_active']);
        });

        // 2. Sessões Diárias de 15 Minutos
        Schema::create('language_daily_sessions', function (Blueprint $table) {
            $table->id();
            $table->foreignId('language_profile_id')->constrained('language_profiles')->cascadeOnDelete();
            $table->date('scheduled_date');
            $table->string('status', 30)->default('ready'); // pending_test, ready, in_progress, completed, missed
            $table->json('lesson_payload')->nullable(); // Conteúdo estruturado dos 3 blocos ou teste
            $table->json('user_answers')->nullable(); // Respostas enviadas pelo usuário
            $table->json('ai_feedback')->nullable(); // Correções do Gemini 3.8 Flash
            $table->unsignedInteger('score')->nullable(); // 0 a 100
            $table->unsignedInteger('time_spent_seconds')->default(0);
            $table->timestamp('completed_at')->nullable();
            $table->timestamps();

            $table->index(['language_profile_id', 'scheduled_date'], 'lang_daily_session_date_idx');
            $table->index('status');
        });

        // 3. Cofre de Vocabulário & Repetição Espaçada (SRS)
        Schema::create('language_vocabulary_vault', function (Blueprint $table) {
            $table->id();
            $table->foreignId('language_profile_id')->constrained('language_profiles')->cascadeOnDelete();
            $table->string('term_or_phrase', 255);
            $table->string('translation', 255);
            $table->text('context_example')->nullable();
            $table->unsignedTinyInteger('mastery_level')->default(1); // 1 a 5
            $table->date('next_review_date');
            $table->timestamps();

            $table->index(['language_profile_id', 'next_review_date'], 'lang_vault_profile_review_idx');
            $table->index(['language_profile_id', 'term_or_phrase'], 'lang_vault_profile_term_idx');
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('language_vocabulary_vault');
        Schema::dropIfExists('language_daily_sessions');
        Schema::dropIfExists('language_profiles');
    }
};
