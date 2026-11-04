<?php

namespace App\Http\Controllers\Api;

use App\Models\AuditLog;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\Hash;

class AuthController extends Controller
{
    /**
     * Check whether initial Commander account setup is required.
     */
    public function status(): JsonResponse
    {
        $userCount = User::count();

        return response()->json([
            'success' => true,
            'setup_required' => $userCount === 0,
            'default_email' => strtolower(trim(env('ADMIN_EMAIL', 'admin@spirandeliempire.tech'))),
        ]);
    }

    /**
     * User Login or First-Time Commander Setup.
     */
    public function login(Request $request): JsonResponse
    {
        $request->validate([
            'email' => 'required|email',
            'password' => 'required|string|min:4',
            'name' => 'nullable|string|max:120',
        ]);

        $email = trim(strtolower($request->input('email')));
        $password = $request->input('password');
        $name = trim($request->input('name', 'Comandante Spirandeli')) ?: 'Comandante Spirandeli';

        $user = User::where('email', $email)->first();

        // First-time bootstrapping: if no user exists yet in DB, register this Commander account and lock the system
        if (User::count() === 0) {
            $user = User::create([
                'name' => $name,
                'email' => $email,
                'password' => Hash::make($password),
                'role' => 'administrator',
            ]);
        }

        if (!$user || !Hash::check($password, $user->password)) {
            return response()->json([
                'success' => false,
                'error' => 'Credenciais inválidas. Verifique seu e-mail e senha de Comandante.',
            ], 401);
        }

        $token = self::issueSignedToken($user);

        try {
            AuditLog::create([
                'user_id' => $user->id,
                'action' => 'user_login',
                'resource_type' => 'user',
                'resource_id' => (string) $user->id,
                'ip_address' => $request->ip(),
                'details' => ['email' => $user->email],
            ]);
        } catch (\Exception $e) {
            // Ignore audit error if table is busy
        }

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
     * Change Commander password while authenticated.
     */
    public function changePassword(Request $request): JsonResponse
    {
        $request->validate([
            'current_password' => 'required|string',
            'new_password' => 'required|string|min:6',
        ]);

        $user = $request->user();
        if (!$user || !Hash::check($request->input('current_password'), $user->password)) {
            return response()->json([
                'success' => false,
                'error' => 'A senha atual informada está incorreta.',
            ], 422);
        }

        $user->password = Hash::make($request->input('new_password'));
        $user->save();

        return response()->json([
            'success' => true,
            'message' => 'Senha do Comandante atualizada com sucesso!',
            'token' => self::issueSignedToken($user),
        ]);
    }

    /**
     * Get authenticated user profile.
     */
    public function me(Request $request): JsonResponse
    {
        $user = $request->user();

        if (!$user) {
            return response()->json(['error' => 'Não autenticado', 'unauthenticated' => true], 401);
        }

        return response()->json([
            'success' => true,
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
     * User Logout.
     */
    public function logout(Request $request): JsonResponse
    {
        return response()->json([
            'success' => true,
            'message' => 'Sessão encerrada e painel trancado com sucesso.',
        ]);
    }

    /**
     * Issue stateless HMAC-SHA256 signed bearer token (no extra table required).
     */
    public static function issueSignedToken(User $user): string
    {
        $payload = [
            'uid' => $user->id,
            'email' => $user->email,
            'role' => $user->role,
            'iat' => time(),
            'exp' => time() + (86400 * 30), // 30 days
            'phash' => substr( md5((string) $user->password), 0, 10 ),
        ];

        $payloadB64 = rtrim(strtr(base64_encode(json_encode($payload)), '+/', '-_'), '=');
        $secret = self::getSigningSecret();
        $sig = hash_hmac('sha256', $payloadB64, $secret);

        return $payloadB64 . '.' . $sig;
    }

    /**
     * Verify stateless HMAC-SHA256 signed bearer token and return the User.
     */
    public static function verifySignedToken(?string $token): ?User
    {
        if (!$token || !str_contains($token, '.')) {
            return null;
        }

        [$payloadB64, $sig] = explode('.', $token, 2);
        $secret = self::getSigningSecret();
        $expectedSig = hash_hmac('sha256', $payloadB64, $secret);

        if (!hash_equals($expectedSig, $sig)) {
            return null;
        }

        $json = base64_decode(strtr($payloadB64, '-_', '+/'));
        $data = json_decode($json ?: '', true);
        if (!is_array($data) || empty($data['uid']) || empty($data['exp'])) {
            return null;
        }

        if (time() > (int) $data['exp']) {
            return null;
        }

        $user = User::find((int) $data['uid']);
        if (!$user) {
            return null;
        }

        // Invalidate token automatically if user changed their password
        $expectedPhash = substr(md5((string) $user->password), 0, 10);
        if (!empty($data['phash']) && !hash_equals($expectedPhash, (string) $data['phash'])) {
            return null;
        }

        return $user;
    }

    protected static function getSigningSecret(): string
    {
        return (string) (config('app.key') ?: env('APP_KEY') ?: 'spirandeli-empire-sovereign-key-2026');
    }
}
