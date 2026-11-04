<?php

namespace App\Http\Controllers\Api;

use App\Models\AuditLog;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\ValidationException;

class AuthController extends Controller
{
    /**
     * User Login / Token Issuance.
     * If database is fresh and matches initial admin config, auto-seeds the admin account.
     */
    public function login(Request $request): JsonResponse
    {
        $request->validate([
            'email' => 'required|email',
            'password' => 'required|string',
        ]);

        $email = trim(strtolower($request->input('email')));
        $password = $request->input('password');

        $user = User::where('email', $email)->first();

        // Bootstrapping: Auto-provision initial administrator if users table is empty
        if (!$user && User::count() === 0) {
            $adminEmail = trim(strtolower(env('ADMIN_EMAIL', 'admin@spirandeliempire.tech')));
            $adminInitialPass = env('ADMIN_INITIAL_PASSWORD', 'ChangeMeOnFirstLogin!2026');

            if ($email === $adminEmail && $password === $adminInitialPass) {
                $user = User::create([
                    'name' => 'Comandante Soberano',
                    'email' => $adminEmail,
                    'password' => Hash::make($adminInitialPass),
                    'role' => 'administrator',
                ]);
            }
        }

        if (!$user || !Hash::check($password, $user->password)) {
            throw ValidationException::withMessages([
                'email' => ['As credenciais fornecidas não conferem com os registros do SpirandeliEmpire OS.'],
            ]);
        }

        // Issue Sanctum token
        $token = $user->createToken('empire-os-session')->plainTextToken;

        AuditLog::create([
            'user_id' => $user->id,
            'action' => 'user_login',
            'resource_type' => 'user',
            'resource_id' => (string) $user->id,
            'ip_address' => $request->ip(),
            'details' => ['email' => $user->email],
        ]);

        return response()->json([
            'success' => true,
            'token' => $token,
            'user' => [
                'id' => $user->id,
                'name' => $user->name,
                'email' => $user->email,
                'role' => $user->role,
            ],
        ]);
    }

    /**
     * Register new user (only administrators or bootstrapping).
     */
    public function register(Request $request): JsonResponse
    {
        $request->validate([
            'name' => 'required|string|max:255',
            'email' => 'required|string|email|max:255|unique:users',
            'password' => 'required|string|min:8',
            'role' => 'nullable|string|in:administrator,operator,analyst',
        ]);

        $user = User::create([
            'name' => $request->name,
            'email' => strtolower($request->email),
            'password' => Hash::make($request->password),
            'role' => $request->role ?? 'administrator',
        ]);

        $token = $user->createToken('empire-os-session')->plainTextToken;

        return response()->json([
            'success' => true,
            'token' => $token,
            'user' => [
                'id' => $user->id,
                'name' => $user->name,
                'email' => $user->email,
                'role' => $user->role,
            ],
        ], 201);
    }

    /**
     * Get authenticated user profile.
     */
    public function me(Request $request): JsonResponse
    {
        $user = $request->user();

        if (!$user) {
            return response()->json(['error' => 'Não autenticado'], 401);
        }

        return response()->json([
            'user' => [
                'id' => $user->id,
                'name' => $user->name,
                'email' => $user->email,
                'role' => $user->role,
            ],
            'system' => [
                'app_name' => config('app.name', 'SpirandeliEmpire OS'),
                'version' => '3.0.0',
                'env' => config('app.env', 'production'),
            ],
        ]);
    }

    /**
     * User Logout / Revoke Token.
     */
    public function logout(Request $request): JsonResponse
    {
        if ($request->user()) {
            $request->user()->currentAccessToken()->delete();
        }

        return response()->json([
            'success' => true,
            'message' => 'Sessão encerrada com sucesso.',
        ]);
    }
}
