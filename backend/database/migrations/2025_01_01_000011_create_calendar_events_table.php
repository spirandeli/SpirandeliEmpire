<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Cache local da Agenda Unificada (Google Calendar/Tasks + Apple CalDAV).
        // Alimenta o widget do Dashboard e a tool `get_user_schedule` sem bater na API a cada chamada.
        Schema::create('calendar_events', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();
            $table->foreignId('user_integration_id')->nullable()->constrained()->nullOnDelete();
            $table->foreignId('task_id')->nullable()->constrained()->nullOnDelete();

            $table->string('provider', 16);          // google | apple
            $table->string('kind', 16)->default('event'); // event | reminder | task
            $table->string('external_id', 255);
            $table->string('calendar_id', 255)->nullable();
            $table->string('etag', 128)->nullable();

            $table->string('title', 500);
            $table->text('description')->nullable();
            $table->string('location', 500)->nullable();
            $table->timestamp('starts_at')->nullable();
            $table->timestamp('ends_at')->nullable();
            $table->boolean('all_day')->default(false);
            $table->string('status', 16)->default('confirmed'); // confirmed | tentative | cancelled
            $table->boolean('is_completed')->default(false);
            $table->boolean('created_by_agent')->default(false);

            $table->json('raw')->nullable();
            $table->timestamp('synced_at')->nullable();
            $table->timestamps();

            $table->unique(['user_id', 'provider', 'external_id'], 'calendar_events_unique_external');
            $table->index(['user_id', 'starts_at', 'ends_at']);
            $table->index(['user_id', 'kind', 'is_completed']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('calendar_events');
    }
};
