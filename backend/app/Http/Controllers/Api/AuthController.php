<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Requests\Auth\LoginRequest;
use App\Http\Requests\Auth\RegisterRequest;
use App\Http\Requests\Auth\UpdateProfileRequest;
use App\Http\Resources\UserResource;
use App\Models\User;
use App\Services\UserOnboardingService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Laravel\Sanctum\PersonalAccessToken;

/**
 * Dois modos (Sanctum):
 *  - SPA (cookie): requests vindos de SANCTUM_STATEFUL_DOMAINS, após GET /sanctum/csrf-cookie.
 *  - Token: enviando `device_name`, devolve Bearer token (apps, Atalhos, CLI).
 */
class AuthController extends Controller
{
    public function register(RegisterRequest $request): JsonResponse
    {
        $user = User::create($request->safe()->only(['name', 'email', 'password', 'timezone']));

        try {
            app(UserOnboardingService::class)->provisionStarterKit($user);
        } catch (\Throwable $e) {
            \Illuminate\Support\Facades\Log::warning("Falha ao provisionar starter kit no registro: {$e->getMessage()}");
        }

        return $this->authenticated($request, $user, 201);
    }

    public function login(LoginRequest $request): JsonResponse
    {
        $user = $request->authenticate();

        if ($user->businesses()->count() === 0) {
            try {
                app(UserOnboardingService::class)->provisionStarterKit($user);
            } catch (\Throwable $e) {
                \Illuminate\Support\Facades\Log::warning("Falha ao provisionar starter kit no login: {$e->getMessage()}");
            }
        }

        return $this->authenticated($request, $user, 200);
    }

    public function provisionShowcase(Request $request): JsonResponse
    {
        $business = app(UserOnboardingService::class)->provisionStarterKit($request->user());

        return response()->json([
            'message' => 'Showcase de demonstração provisionado com sucesso!',
            'business' => new \App\Http\Resources\BusinessResource($business),
        ], 201);
    }

    public function me(Request $request): UserResource
    {
        return new UserResource($request->user());
    }

    public function updateProfile(UpdateProfileRequest $request): UserResource
    {
        $user = $request->user();
        $user->update($request->validated());

        return new UserResource($user->refresh());
    }

    public function logout(Request $request): JsonResponse
    {
        $token = $request->user()->currentAccessToken();

        if ($token instanceof PersonalAccessToken) {
            $token->delete();
        }

        if ($request->hasSession()) {
            Auth::guard('web')->logout();
            $request->session()->invalidate();
            $request->session()->regenerateToken();
        }

        return response()->json(['message' => 'Sessão encerrada.']);
    }

    private function authenticated(Request $request, User $user, int $status): JsonResponse
    {
        $user->forceFill(['last_login_at' => now()])->save();

        if ($request->filled('device_name')) {
            return response()->json([
                'user' => new UserResource($user),
                'token' => $user->createToken($request->string('device_name')->toString())->plainTextToken,
                'token_type' => 'Bearer',
            ], $status);
        }

        if (! $request->hasSession()) {
            return response()->json([
                'message' => 'Informe device_name para autenticação por token ou use o fluxo SPA (/sanctum/csrf-cookie).',
            ], 422);
        }

        Auth::guard('web')->login($user, $request->boolean('remember'));
        $request->session()->regenerate();

        return response()->json(['user' => new UserResource($user)], $status);
    }
}

