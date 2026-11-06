<?php

namespace Tests\Feature\Api;

use App\Models\User;
use App\Models\UserIntegration;
use App\Services\IntegrationService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class IntegrationTest extends TestCase
{
    use RefreshDatabase;

    private User $user;

    private const KEY = 'AIzaSyFAKE-KEY-1234567890abcdef';

    protected function setUp(): void
    {
        parent::setUp();

        $this->user = User::factory()->create();
        $this->actingAs($this->user, 'sanctum');
    }

    public function test_gemini_key_is_validated_encrypted_and_never_returned(): void
    {
        Http::fake(['generativelanguage.googleapis.com/*' => Http::response(['models' => []], 200)]);

        $response = $this->putJson('/api/integrations/gemini', ['api_key' => self::KEY, 'model' => 'gemini-3.8'])
            ->assertOk()
            ->assertJsonPath('data.provider', 'gemini')
            ->assertJsonPath('data.connected', true)
            ->assertJsonPath('data.meta.model', 'gemini-3.8');

        $this->assertStringNotContainsString(self::KEY, $response->getContent());
        $this->assertArrayNotHasKey('credentials', $response->json('data'));
        Http::assertSent(fn ($r) => $r->hasHeader('x-goog-api-key', self::KEY));

        // No banco: criptografado (não contém a chave em texto plano) mas legível via cast.
        $raw = DB::table('user_integrations')->value('credentials');
        $this->assertStringNotContainsString(self::KEY, $raw);
        $integration = UserIntegration::first();
        $this->assertSame(self::KEY, $integration->credential('api_key'));
        $this->assertSame(self::KEY, app(IntegrationService::class)->geminiApiKeyFor($this->user));

        // Listagem também não vaza segredos.
        $this->assertStringNotContainsString(self::KEY, $this->getJson('/api/integrations')->assertOk()->getContent());
    }

    public function test_invalid_gemini_key_is_rejected_and_nothing_is_saved(): void
    {
        Http::fake(['generativelanguage.googleapis.com/*' => Http::response(['error' => 'API key not valid'], 400)]);

        $this->putJson('/api/integrations/gemini', ['api_key' => self::KEY])
            ->assertUnprocessable()->assertJsonValidationErrors('api_key');

        $this->assertDatabaseCount('user_integrations', 0);
    }

    public function test_saving_gemini_twice_updates_the_same_row(): void
    {
        Http::fake(['generativelanguage.googleapis.com/*' => Http::response([], 200)]);

        $this->putJson('/api/integrations/gemini', ['api_key' => self::KEY])->assertOk();
        $this->putJson('/api/integrations/gemini', ['api_key' => 'AIzaSyOUTRA-CHAVE-0987654321zzzz'])->assertOk();

        $this->assertDatabaseCount('user_integrations', 1);
        $this->assertSame('AIzaSyOUTRA-CHAVE-0987654321zzzz', UserIntegration::first()->credential('api_key'));
    }

    public function test_apple_caldav_requires_app_specific_password(): void
    {
        $this->putJson('/api/integrations/apple-caldav', ['apple_id' => 'ana@icloud.com', 'app_password' => 'minha-senha-normal'])
            ->assertUnprocessable()->assertJsonValidationErrors('app_password');

        $response = $this->putJson('/api/integrations/apple-caldav', [
            'apple_id' => 'ana@icloud.com', 'app_password' => 'abcd-efgh-ijkl-mnop',
        ])->assertOk()->assertJsonPath('data.provider', 'apple_caldav')
            ->assertJsonPath('data.meta.server_url', 'https://caldav.icloud.com');

        $this->assertStringNotContainsString('abcd-efgh-ijkl-mnop', $response->getContent());
        $this->assertStringNotContainsString('abcd-efgh-ijkl-mnop', DB::table('user_integrations')->value('credentials'));
        $this->assertSame('abcd-efgh-ijkl-mnop', UserIntegration::first()->credential('app_password'));
    }

    public function test_shortcuts_token_is_shown_once_and_only_hash_is_stored(): void
    {
        $response = $this->postJson('/api/integrations/shortcuts/token', ['name' => 'iPhone'])
            ->assertCreated()
            ->assertJsonStructure(['token', 'webhook_url', 'data' => ['token_prefix']]);

        $token = $response->json('token');
        $this->assertStringStartsWith('abvos_', $token);

        $row = DB::table('user_integrations')->first();
        $this->assertNotSame($token, $row->webhook_token_hash);
        $this->assertSame(hash('sha256', $token), $row->webhook_token_hash);
        $this->assertStringNotContainsString($token, json_encode($this->getJson('/api/integrations')->json()));

        $this->assertSame($this->user->id, UserIntegration::findByWebhookToken($token)->user_id);
        $this->assertNull(UserIntegration::findByWebhookToken('abvos_invalido'));

        // Rotação invalida o token anterior.
        $new = $this->postJson('/api/integrations/shortcuts/token')->json('token');
        $this->assertNull(UserIntegration::findByWebhookToken($token));
        $this->assertNotNull(UserIntegration::findByWebhookToken($new));
        $this->assertDatabaseCount('user_integrations', 1);
    }

    public function test_disconnect_deletes_credentials_and_respects_ownership(): void
    {
        $this->postJson('/api/integrations/shortcuts/token')->assertCreated();
        $id = UserIntegration::first()->id;

        $this->actingAs(User::factory()->create(), 'sanctum');
        $this->deleteJson("/api/integrations/{$id}")->assertNotFound();

        $this->actingAs($this->user, 'sanctum');
        $this->deleteJson("/api/integrations/{$id}")->assertNoContent();
        $this->assertDatabaseCount('user_integrations', 0);
    }

    public function test_falls_back_to_system_gemini_key(): void
    {
        config(['services.gemini.api_key' => 'SYSTEM-KEY']);

        $this->assertSame('SYSTEM-KEY', app(IntegrationService::class)->geminiApiKeyFor($this->user));
    }
}

