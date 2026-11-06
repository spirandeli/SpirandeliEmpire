<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('user_integrations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('user_id')->constrained()->cascadeOnDelete();

            // gemini | google | apple_caldav | shortcuts_webhook | tiktok_shop
            $table->string('provider', 32);
            $table->string('label')->default('default')->comment('NOT NULL: garante a unicidade (user, provider, label) no MySQL');
            // connected | disconnected | error | expired
            $table->string('status', 24)->default('connected');

            // Cofre: cast `encrypted:array` (AES-256-CBC via APP_KEY). NUNCA em texto plano.
            // gemini: {api_key} | google: {access_token, refresh_token, id_token}
            // apple_caldav: {apple_id, app_password} | tiktok_shop: {app_key, app_secret, access_token}
            $table->longText('credentials')->nullable();

            $table->json('meta')->nullable()->comment('Não sensível: e-mail da conta, calendários, URLs CalDAV, modelo');
            $table->json('scopes')->nullable();

            // Webhook Apple Shortcuts: guardamos apenas o hash SHA-256 do token (exibido uma única vez)
            $table->string('token_prefix', 12)->nullable();
            $table->char('webhook_token_hash', 64)->nullable()->unique();

            $table->timestamp('expires_at')->nullable();
            $table->timestamp('last_synced_at')->nullable();
            $table->timestamp('last_used_at')->nullable();
            $table->text('last_error')->nullable();
            $table->timestamps();

            $table->unique(['user_id', 'provider', 'label']);
            $table->index(['user_id', 'provider', 'status']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('user_integrations');
    }
};
