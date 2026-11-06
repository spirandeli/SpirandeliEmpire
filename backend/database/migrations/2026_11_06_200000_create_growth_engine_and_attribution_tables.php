<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('businesses', function (Blueprint $table) {
            $table->string('archetype', 48)->default('affiliate_tiktok')->after('type');
            $table->string('north_star_metric', 48)->default('commission_volume')->after('archetype');
            $table->decimal('target_kpi_value', 12, 2)->default(0.00)->after('north_star_metric');
            $table->string('webhook_secret_token', 64)->nullable()->unique()->after('target_kpi_value');
        });

        Schema::table('content_assets', function (Blueprint $table) {
            $table->string('tracking_code', 32)->nullable()->unique()->after('id');
            $table->string('funnel_stage', 32)->default('tof_attraction')->after('is_selected');
            $table->string('angle_category', 64)->nullable()->after('funnel_stage');
            $table->unsignedInteger('total_views')->default(0)->after('angle_category');
            $table->unsignedInteger('total_clicks')->default(0)->after('total_views');
            $table->unsignedInteger('total_leads')->default(0)->after('total_clicks');
            $table->unsignedInteger('total_sales_count')->default(0)->after('total_leads');
            $table->decimal('total_revenue_brl', 12, 2)->default(0.00)->after('total_sales_count');
            $table->decimal('roi_score', 5, 2)->default(0.00)->after('total_revenue_brl');

            $table->index(['business_id', 'roi_score'], 'content_assets_biz_roi_idx');
            $table->index(['business_id', 'funnel_stage'], 'content_assets_biz_stage_idx');
        });

        Schema::create('conversion_events', function (Blueprint $table) {
            $table->id();
            $table->foreignId('business_id')->constrained()->cascadeOnDelete();
            $table->foreignId('content_asset_id')->nullable()->constrained('content_assets')->nullOnDelete();
            $table->string('source_platform', 32); // tiktok_shop, hotmart, kiwify, stripe, shopify, custom_webhook
            $table->string('event_type', 48); // click, lead, checkout_abandoned, pix_generated, sale_approved, refund, subscription_canceled
            $table->string('external_transaction_id', 128)->nullable();
            $table->decimal('gross_amount', 12, 2)->default(0.00);
            $table->decimal('net_amount', 12, 2)->default(0.00);
            $table->json('customer_metadata')->nullable();
            $table->json('payload_raw')->nullable();
            $table->timestamp('occurred_at')->useCurrent();
            $table->timestamps();

            $table->index(['business_id', 'event_type', 'occurred_at'], 'conv_events_biz_type_time_idx');
            $table->index(['content_asset_id', 'event_type'], 'conv_events_asset_type_idx');
            $table->index(['business_id', 'source_platform', 'external_transaction_id'], 'conv_events_biz_plat_tx_idx');
        });

        Schema::create('optimization_cycles', function (Blueprint $table) {
            $table->id();
            $table->foreignId('business_id')->constrained()->cascadeOnDelete();
            $table->timestamp('period_start')->nullable();
            $table->timestamp('period_end')->nullable();
            $table->json('winning_assets_summary')->nullable();
            $table->json('losing_assets_summary')->nullable();
            $table->longText('ai_diagnosis')->nullable();
            $table->json('actions_taken')->nullable();
            $table->timestamps();

            $table->index(['business_id', 'created_at'], 'opt_cycles_biz_created_idx');
        });

        Schema::create('agent_learnings', function (Blueprint $table) {
            $table->id();
            $table->foreignId('business_id')->constrained()->cascadeOnDelete();
            $table->string('topic', 128);
            $table->text('insight');
            $table->unsignedSmallInteger('confidence_score')->default(80);
            $table->string('data_source', 64)->nullable();
            $table->json('metadata')->nullable();
            $table->timestamps();

            $table->index(['business_id', 'topic'], 'agent_learnings_biz_topic_idx');
            $table->index(['business_id', 'confidence_score'], 'agent_learnings_biz_conf_idx');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('agent_learnings');
        Schema::dropIfExists('optimization_cycles');
        Schema::dropIfExists('conversion_events');

        Schema::table('content_assets', function (Blueprint $table) {
            $table->dropIndex('content_assets_biz_roi_idx');
            $table->dropIndex('content_assets_biz_stage_idx');
            $table->dropColumn([
                'tracking_code',
                'funnel_stage',
                'angle_category',
                'total_views',
                'total_clicks',
                'total_leads',
                'total_sales_count',
                'total_revenue_brl',
                'roi_score',
            ]);
        });

        Schema::table('businesses', function (Blueprint $table) {
            $table->dropColumn([
                'archetype',
                'north_star_metric',
                'target_kpi_value',
                'webhook_secret_token',
            ]);
        });
    }
};
