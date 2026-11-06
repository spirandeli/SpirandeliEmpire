<?php

namespace Tests\Feature\Api;

use App\Models\Business;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class BusinessTest extends TestCase
{
    use RefreshDatabase;

    public function test_create_tiktok_business_seeds_default_automations(): void
    {
        $user = User::factory()->create();

        $response = $this->actingAs($user, 'sanctum')->postJson('/api/businesses', [
            'name' => 'Achadinhos TikTok',
            'type' => 'tiktok_shop_affiliate',
            'niche' => 'Casa e cozinha',
            'goals' => ['videos_per_week' => 7],
        ])->assertCreated()
            ->assertJsonPath('data.status', 'draft')
            ->assertJsonPath('data.slug', 'achadinhos-tiktok')
            ->assertJsonCount(2, 'data.automations');

        $this->assertSame(7, $response->json('data.goals.videos_per_week'));
    }

    public function test_slug_is_unique_per_user(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user, 'sanctum');
        $this->postJson('/api/businesses', ['name' => 'Loja X'])->assertCreated();
        $this->postJson('/api/businesses', ['name' => 'Loja X'])->assertCreated()
            ->assertJsonPath('data.slug', 'loja-x-2');
    }

    public function test_validation_errors(): void
    {
        $this->actingAs(User::factory()->create(), 'sanctum')
            ->postJson('/api/businesses', ['type' => 'inexistente'])
            ->assertUnprocessable()->assertJsonValidationErrors(['name', 'type']);
    }

    public function test_user_cannot_access_other_users_business(): void
    {
        $owner = User::factory()->create();
        $intruder = User::factory()->create();
        $business = $owner->businesses()->create(['name' => 'Privado']);

        $this->actingAs($intruder, 'sanctum');
        $this->getJson("/api/businesses/{$business->id}")->assertNotFound();
        $this->putJson("/api/businesses/{$business->id}", ['name' => 'Hack'])->assertNotFound();
        $this->deleteJson("/api/businesses/{$business->id}")->assertNotFound();
        $this->postJson("/api/businesses/{$business->id}/activate")->assertNotFound();
        $this->getJson('/api/businesses')->assertOk()->assertJsonCount(0, 'data');
    }

    public function test_activate_and_pause_toggle_autonomy(): void
    {
        $user = User::factory()->create();
        $this->actingAs($user, 'sanctum');
        $id = $this->postJson('/api/businesses', ['name' => 'Op', 'type' => 'tiktok_shop_affiliate'])->json('data.id');

        $this->postJson("/api/businesses/{$id}/activate")->assertOk()
            ->assertJsonPath('data.status', 'active')
            ->assertJsonPath('data.automation_enabled', true);

        $this->assertNotNull(Business::find($id)->automations()->first()->next_run_at);
        $this->assertSame(1, Business::autonomous()->count());

        $this->postJson("/api/businesses/{$id}/pause")->assertOk()
            ->assertJsonPath('data.status', 'paused')
            ->assertJsonPath('data.automation_enabled', false);
        $this->assertSame(0, Business::autonomous()->count());
    }

    public function test_update_and_soft_delete(): void
    {
        $user = User::factory()->create();
        $this->actingAs($user, 'sanctum');
        $id = $this->postJson('/api/businesses', ['name' => 'Op'])->json('data.id');

        $this->putJson("/api/businesses/{$id}", ['niche' => 'Pets', 'canvas' => ['value_proposition' => 'x']])
            ->assertOk()->assertJsonPath('data.niche', 'Pets');

        $this->deleteJson("/api/businesses/{$id}")->assertNoContent();
        $this->assertSoftDeleted('businesses', ['id' => $id]);
        $this->getJson("/api/businesses/{$id}")->assertNotFound();
    }

    public function test_automation_crud_with_cron_validation(): void
    {
        $user = User::factory()->create();
        $this->actingAs($user, 'sanctum');
        $id = $this->postJson('/api/businesses', ['name' => 'Op'])->json('data.id');

        $this->postJson("/api/businesses/{$id}/automations", [
            'type' => 'calendar_sync', 'name' => 'Sync', 'cron_expression' => 'isto não é cron',
        ])->assertUnprocessable()->assertJsonValidationErrors('cron_expression');

        $autoId = $this->postJson("/api/businesses/{$id}/automations", [
            'type' => 'calendar_sync', 'name' => 'Sync', 'cron_expression' => '*/15 * * * *',
        ])->assertCreated()->assertJsonPath('data.cron_expression', '*/15 * * * *')->json('data.id');

        $this->putJson("/api/businesses/{$id}/automations/{$autoId}", ['cron_expression' => '0 8 * * *', 'is_enabled' => false])
            ->assertOk()->assertJsonPath('data.is_enabled', false);

        $this->deleteJson("/api/businesses/{$id}/automations/{$autoId}")->assertNoContent();
    }
}

