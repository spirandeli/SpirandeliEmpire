<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Users
        Schema::create('users', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('email')->unique();
            $table->timestamp('email_verified_at')->nullable();
            $table->string('password');
            $table->string('role')->default('administrator');
            $table->rememberToken();
            $table->timestamps();
        });

        // Businesses (RISADA.exe, KDP Factory, etc.)
        Schema::create('businesses', function (Blueprint $table) {
            $table->id();
            $table->string('name');
            $table->string('slug')->unique();
            $table->string('category');
            $table->text('description')->nullable();
            $table->string('status')->default('provisioning'); // active, paused, provisioning, archived
            $table->string('template_used')->nullable();
            $table->jsonb('settings')->nullable();
            $table->string('storage_path')->nullable();
            $table->decimal('budget_limit_brl', 10, 2)->default(50.00);
            $table->decimal('current_month_cost_brl', 10, 2)->default(0.00);
            $table->decimal('total_revenue_brl', 10, 2)->default(0.00);
            $table->timestamps();
        });

        // Jeffrey Operational Memory
        Schema::create('jeffrey_memories', function (Blueprint $table) {
            $table->id();
            $table->foreignId('business_id')->nullable()->constrained('businesses')->onDelete('cascade');
            $table->string('category'); // context, decision, preference, architecture, issue
            $table->string('key');
            $table->text('content');
            $table->jsonb('metadata')->nullable();
            $table->boolean('is_active')->default(true);
            $table->timestamps();

            $table->index(['category', 'key']);
        });

        // Agent Decisions & Audit Log
        Schema::create('agent_decisions', function (Blueprint $table) {
            $table->id();
            $table->string('agent_name');
            $table->foreignId('business_id')->nullable()->constrained('businesses')->onDelete('cascade');
            $table->string('action_type');
            $table->text('justification');
            $table->jsonb('input_payload')->nullable();
            $table->jsonb('output_payload')->nullable();
            $table->decimal('estimated_cost_brl', 10, 2)->default(0.00);
            $table->string('status')->default('proposed'); // proposed, approved, executed, rejected
            $table->timestamps();
        });

        // Human Approval Requests (Safety Gate)
        Schema::create('approval_requests', function (Blueprint $table) {
            $table->id();
            $table->string('title');
            $table->text('description');
            $table->string('agent_name');
            $table->foreignId('business_id')->nullable()->constrained('businesses')->onDelete('cascade');
            $table->jsonb('action_payload');
            $table->decimal('financial_impact_brl', 10, 2)->default(0.00);
            $table->string('status')->default('pending'); // pending, approved, rejected
            $table->string('reviewed_by')->nullable();
            $table->timestamp('reviewed_at')->nullable();
            $table->text('rejection_reason')->nullable();
            $table->timestamps();
        });

        // Tasks & Pipeline Execution
        Schema::create('tasks', function (Blueprint $table) {
            $table->id();
            $table->foreignId('business_id')->nullable()->constrained('businesses')->onDelete('cascade');
            $table->string('agent_name');
            $table->string('title');
            $table->string('type');
            $table->string('status')->default('pending'); // pending, in_progress, completed, failed, cancelled
            $table->jsonb('payload')->nullable();
            $table->jsonb('result')->nullable();
            $table->text('error_message')->nullable();
            $table->decimal('estimated_cost_brl', 10, 2)->default(0.00);
            $table->decimal('actual_cost_brl', 10, 2)->default(0.00);
            $table->timestamp('started_at')->nullable();
            $table->timestamp('completed_at')->nullable();
            $table->timestamps();
        });

        // Financial Records (Consolidated Empire Financials)
        Schema::create('financial_records', function (Blueprint $table) {
            $table->id();
            $table->foreignId('business_id')->nullable()->constrained('businesses')->onDelete('set null');
            $table->string('type'); // revenue, infrastructure_expense, ai_cost, platform_fee, other_expense
            $table->string('category');
            $table->string('description');
            $table->decimal('amount_brl', 10, 2);
            $table->boolean('is_confirmed')->default(true);
            $table->timestamp('recorded_at')->useCurrent();
            $table->timestamps();
        });

        // VPS & System Metrics
        Schema::create('system_metrics', function (Blueprint $table) {
            $table->id();
            $table->float('cpu_usage_percent');
            $table->float('ram_usage_percent');
            $table->float('disk_usage_percent');
            $table->integer('active_containers_count')->default(0);
            $table->integer('active_queues_count')->default(0);
            $table->string('gpu_status')->default('idle');
            $table->jsonb('metadata')->nullable();
            $table->timestamp('recorded_at')->useCurrent();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('system_metrics');
        Schema::dropIfExists('financial_records');
        Schema::dropIfExists('tasks');
        Schema::dropIfExists('approval_requests');
        Schema::dropIfExists('agent_decisions');
        Schema::dropIfExists('jeffrey_memories');
        Schema::dropIfExists('businesses');
        Schema::dropIfExists('users');
    }
};

