<?php

namespace Tests\Feature\Api;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class AuthTest extends TestCase
{
    use RefreshDatabase;

    private const PASSWORD = 'SenhaForte123';

    private function payload(array $override = []): array
    {
        return array_merge([
            'name' => 'Ana Operadora',
            'email' => 'ana@example.com',
            'password' => self::PASSWORD,
            'password_confirmation' => self::PASSWORD,
            'device_name' => 'testes',
        ], $override);
    }

    public function test_register_with_device_name_returns_bearer_token(): void
    {
        $this->postJson('/api/auth/register', $this->payload())
            ->assertCreated()
            ->assertJsonStructure(['user' => ['id', 'email'], 'token', 'token_type'])
            ->assertJsonMissingPath('user.password');

        $this->assertDatabaseHas('users', ['email' => 'ana@example.com']);
    }

    public function test_register_rejects_weak_password_and_duplicate_email(): void
    {
        $this->postJson('/api/auth/register', $this->payload(['password' => 'curta', 'password_confirmation' => 'curta']))
            ->assertUnprocessable()->assertJsonValidationErrors('password');

        User::factory()->create(['email' => 'ana@example.com']);
        $this->postJson('/api/auth/register', $this->payload())
            ->assertUnprocessable()->assertJsonValidationErrors('email');
    }

    public function test_registration_can_be_disabled(): void
    {
        config(['abvos.registration_enabled' => false]);

        $this->postJson('/api/auth/register', $this->payload())->assertForbidden();
    }

    public function test_login_me_and_logout_with_token(): void
    {
        User::factory()->create(['email' => 'ana@example.com', 'password' => self::PASSWORD]);

        $token = $this->postJson('/api/auth/login', [
            'email' => 'ana@example.com', 'password' => self::PASSWORD, 'device_name' => 'testes',
        ])->assertOk()->json('token');

        $this->withToken($token)->getJson('/api/auth/me')
            ->assertOk()->assertJsonPath('data.email', 'ana@example.com');

        $this->withToken($token)->postJson('/api/auth/logout')->assertOk();
        $this->assertDatabaseCount('personal_access_tokens', 0);
    }

    public function test_login_with_wrong_password_fails_and_is_rate_limited(): void
    {
        User::factory()->create(['email' => 'ana-wrong@example.com', 'password' => self::PASSWORD]);
        $body = ['email' => 'ana-wrong@example.com', 'password' => 'errada', 'device_name' => 'testes'];

        for ($i = 0; $i < 5; $i++) {
            $this->postJson('/api/auth/login', $body)->assertUnprocessable();
        }

        $this->postJson('/api/auth/login', $body)->assertStatus(429);
    }

    public function test_login_without_token_or_session_is_rejected(): void
    {
        User::factory()->create(['email' => 'ana-notoken@example.com', 'password' => self::PASSWORD]);

        $this->postJson('/api/auth/login', ['email' => 'ana-notoken@example.com', 'password' => self::PASSWORD])
            ->assertUnprocessable();
    }

    public function test_spa_cookie_login_from_stateful_domain(): void
    {
        User::factory()->create(['email' => 'ana-spa@example.com', 'password' => self::PASSWORD]);

        // Request de domínio stateful: sessão + CSRF (o token vem do cookie XSRF-TOKEN no navegador).
        $this->withHeaders(['Referer' => 'http://localhost', 'X-CSRF-TOKEN' => 'csrf-de-teste'])
            ->withSession(['_token' => 'csrf-de-teste'])
            ->postJson('/api/auth/login', ['email' => 'ana-spa@example.com', 'password' => self::PASSWORD])
            ->assertOk()->assertJsonPath('user.email', 'ana-spa@example.com');

        $this->assertAuthenticated('web');
    }

    public function test_protected_routes_require_authentication_with_json_401(): void
    {
        $this->getJson('/api/businesses')->assertUnauthorized();
        $this->getJson('/api/auth/me')->assertUnauthorized();
    }

    public function test_user_can_toggle_agent_kill_switch(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user, 'sanctum')
            ->putJson('/api/auth/profile', ['agent_enabled' => false, 'timezone' => 'America/Sao_Paulo'])
            ->assertOk()->assertJsonPath('data.agent_enabled', false);
    }
}
