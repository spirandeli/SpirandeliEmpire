<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (Schema::hasTable('users') && !Schema::hasColumn('users', 'profile_data')) {
            Schema::table('users', function (Blueprint $table) {
                $table->jsonb('profile_data')->nullable()->after('role');
            });
        }

        if (Schema::hasTable('businesses')) {
            Schema::table('businesses', function (Blueprint $table) {
                if (!Schema::hasColumn('businesses', 'accounts')) {
                    $table->jsonb('accounts')->nullable()->after('settings');
                }
                if (!Schema::hasColumn('businesses', 'automation_params')) {
                    $table->jsonb('automation_params')->nullable()->after('settings');
                }
            });
        }
    }

    public function down(): void
    {
        if (Schema::hasTable('users') && Schema::hasColumn('users', 'profile_data')) {
            Schema::table('users', function (Blueprint $table) {
                $table->dropColumn('profile_data');
            });
        }

        if (Schema::hasTable('businesses')) {
            Schema::table('businesses', function (Blueprint $table) {
                if (Schema::hasColumn('businesses', 'accounts')) {
                    $table->dropColumn('accounts');
                }
                if (Schema::hasColumn('businesses', 'automation_params')) {
                    $table->dropColumn('automation_params');
                }
            });
        }
    }
};

