<?php

namespace App\Http\Controllers\Api;

use App\Models\AuditLog;
use App\Models\JeffreyMemory;
use App\Models\User;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Routing\Controller;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\Facades\Redis;
use Illuminate\Support\Facades\Schema;

class AuthController extends Controller
{
    /**
     * Format user object with complete profile data.
     */
    public static function formatUserProfile(User $user): array
    {
        $profileData = [];
        if (Schema::hasColumn('users', 'profile_data') && is_array($user->profile_data)) {
            $profileData = $user->profile_data;
        } else {
            $mem = JeffreyMemory::where('key', "user_profile_{$user->id}")->first();
            if ($mem && is_array($mem->metadata)) {
                $profileData = $mem->metadata;
            }
        }

        return [
            'id' => $user->id,
            'name' => $user->name,
            'email' => $user->email,
            'role' => $user->role,
            'profile' => array_merge([
                'title' => 'Comandante Soberano',
                'bio' => 'Estrategista Digital & Gestor do Ecossistema',
                'telegram_id' => '',
                'preferred_provider' => 'hybrid',
                'focus_business_slug' => 'tiktok-shop-afiliados',
                'daily_goal' => '9 vídeos TikTok Shop + 1 roteiro Dark',
                'custom_instructions' => 'Seja direto, foque em ROI, conversão e execução prática.',
                'level' => 3,
            ], $profileData),
        ];
    }

    /**
     * Persist profile data safely (to users.profile_data column AND JeffreyMemory for AI context).
     */
    protected static function saveUserProfileData(User $user, array $profileData): void
    {
        if (Schema::hasColumn('users', 'profile_data')) {
            $user->profile_data = $profileData;
            $user->save();
        }

        $summary = sprintf(
            "Perfil Ativo [%s - %s]: Negócio Foco=%s | Meta Diária=%s | Diretrizes Pessoais=%s",
            $user->name,
            $profileData['title'] ?? 'Comandante',
            $profileData['focus_business_slug'] ?? 'tiktok-shop-afiliados',
            $profileData['daily_goal'] ?? '',
            $profileData['custom_instructions'] ?? ''
        );

        JeffreyMemory::updateOrCreate(
            ['key' => "user_profile_{$user->id}"],
            [
                'category' => 'preference',
                'content' => $summary,
                'metadata' => $profileData,
                'is_active' => true,
            ]
        );
    }

    /**
     * Check whether initial Commander account setup is required.
     */
    public function status(): JsonResponse
    {
        $userCount = User::count();

        return response()->json([
            'success' => true,
            'setup_required' => $userCount === 0,
            'users_count' => $userCount,
            'default_email' => strtolower(trim(env('ADMIN_EMAIL', 'admin@spirandeliempire.tech'))),
        ]);
    }

    /**
     * Register a new profile/user account.
     * Security: Once the first Commander is registered, creating additional profiles requires
     * either an active authenticated Bearer token OR the existing Commander's password.
     */
    public function register(Request $request): JsonResponse
    {
        $rateKey = 'auth_register:' . $request->ip();
        if (RateLimiter::tooManyAttempts($rateKey, 6)) {
            $seconds = RateLimiter::availableIn($rateKey);
            return response()->json([
                'success' => false,
                'error' => "Muitas tentativas. Aguarde {$seconds} segundos antes de tentar novamente.",
            ], 429);
        }

        $request->validate([
            'name' => 'required|string|max:120',
            'email' => 'required|email|max:180',
            'password' => 'required|string|min:6',
            'commander_password' => 'nullable|string',
            'title' => 'nullable|string|max:100',
            'focus_business_slug' => 'nullable|string|max:100',
            'daily_goal' => 'nullable|string|max:255',
            'custom_instructions' => 'nullable|string|max:1000',
            'profile' => 'nullable|array',
        ]);

        // Prevent unauthenticated takeover if at least one user already exists
        if (User::count() > 0) {
            $authenticatedUser = self::verifySignedToken($request->bearerToken());
            $commanderPassword = (string) $request->input('commander_password', '');
            $authorizedByPassword = false;

            if (!$authenticatedUser && $commanderPassword !== '') {
                $existingAdmins = User::all();
                foreach ($existingAdmins as $adm) {
                    if (Hash::check($commanderPassword, $adm->password)) {
                        $authorizedByPassword = true;
                        break;
                    }
                }
            }

            if (!$authenticatedUser && !$authorizedByPassword) {
                RateLimiter::hit($rateKey, 60);
                return response()->json([
                    'success' => false,
                    'error' => 'Acesso bloqueado: Para cadastrar um novo perfil na tela de login, informe a Senha Mestra do Comandante atual (ou cadastre por dentro do painel já autenticado).',
                ], 403);
            }
        }

        $email = trim(strtolower($request->input('email')));
        if (User::where('email', $email)->exists()) {
            return response()->json([
                'success' => false,
                'error' => 'Já existe um perfil cadastrado com este e-mail.',
            ], 422);
        }

        $user = User::create([
            'name' => trim($request->input('name')),
            'email' => $email,
            'password' => Hash::make($request->input('password')),
            'role' => 'administrator',
        ]);

        $profileInput = is_array($request->input('profile')) ? $request->input('profile') : [];
        self::saveUserProfileData($user, array_merge([
            'title' => $request->input('title', $request->input('profile.title', 'Comandante Soberano')),
            'bio' => $request->input('bio', $request->input('profile.bio', 'Gestor de Negócios Digitais')),
            'telegram_id' => $request->input('telegram_id', $request->input('profile.telegram_id', '')),
            'preferred_provider' => $request->input('preferred_provider', $request->input('profile.preferred_provider', 'hybrid')),
            'focus_business_slug' => $request->input('focus_business_slug', $request->input('profile.focus_business_slug', 'tiktok-shop-afiliados')),
            'daily_goal' => $request->input('daily_goal', $request->input('profile.daily_goal', '9 vídeos TikTok Shop + 1 roteiro Dark')),
            'custom_instructions' => $request->input('custom_instructions', $request->input('profile.custom_instructions', 'Foque em execução prática, produtos virais e alta conversão.')),
            'level' => 3,
        ], $profileInput));

        RateLimiter::clear($rateKey);
        $token = self::issueSignedToken($user);

        return response()->json([
            'success' => true,
            'message' => 'Perfil cadastrado com sucesso!',
            'token' => $token,
            'user' => self::formatUserProfile($user->fresh()),
        ], 201);
    }

    /**
     * User Login or First-Time Commander Setup (Protected by Brute-Force Rate Limiter).
     */
    public function login(Request $request): JsonResponse
    {
        $rateKey = 'auth_login:' . $request->ip();
        if (RateLimiter::tooManyAttempts($rateKey, 6)) {
            $seconds = RateLimiter::availableIn($rateKey);
            return response()->json([
                'success' => false,
                'error' => "Proteção Anti-Brute-Force ativada: Muitas tentativas incorretas. Aguarde {$seconds} segundos.",
            ], 429);
        }

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
            if (strlen($password) < 6) {
                return response()->json([
                    'success' => false,
                    'error' => 'A senha inicial deve ter no mínimo 6 caracteres.',
                ], 422);
            }
            $user = User::create([
                'name' => $name,
                'email' => $email,
                'password' => Hash::make($password),
                'role' => 'administrator',
            ]);
            self::saveUserProfileData($user, [
                'title' => $request->input('title', 'Comandante Soberano'),
                'focus_business_slug' => $request->input('focus_business_slug', 'tiktok-shop-afiliados'),
                'daily_goal' => $request->input('daily_goal', '3 vídeos virais TikTok Shop'),
                'custom_instructions' => $request->input('custom_instructions', ''),
                'preferred_provider' => 'hybrid',
            ]);
        }

        if (!$user || !Hash::check($password, $user->password)) {
            RateLimiter::hit($rateKey, 60);
            try {
                AuditLog::create([
                    'user_id' => $user?->id,
                    'action' => 'failed_login_attempt',
                    'resource_type' => 'security',
                    'resource_id' => $email,
                    'ip_address' => $request->ip(),
                    'details' => ['email' => $email],
                ]);
            } catch (\Exception $e) {}

            return response()->json([
                'success' => false,
                'error' => 'Credenciais inválidas. Verifique seu e-mail e senha de Comandante.',
            ], 401);
        }

        RateLimiter::clear($rateKey);
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
            'user' => self::formatUserProfile($user),
        ]);
    }

    /**
     * Update authenticated user's profile and preferences.
     */
    public function updateProfile(Request $request): JsonResponse
    {
        $user = $request->user();
        if (!$user) {
            return response()->json(['error' => 'Não autenticado'], 401);
        }

        $validated = $request->validate([
            'name' => 'nullable|string|max:120',
            'email' => 'nullable|email|max:180',
            'role' => 'nullable|string|max:60',
            'profile' => 'nullable|array',
        ]);

        if (!empty($validated['name'])) {
            $user->name = trim($validated['name']);
        }
        if (!empty($validated['email']) && $validated['email'] !== $user->email) {
            $newEmail = trim(strtolower($validated['email']));
            if (User::where('email', $newEmail)->where('id', '!=', $user->id)->exists()) {
                return response()->json(['success' => false, 'error' => 'Este e-mail já está em uso por outro perfil.'], 422);
            }
            $user->email = $newEmail;
        }
        if (!empty($validated['role'])) {
            $user->role = $validated['role'];
        }
        $user->save();

        $currentFormatted = self::formatUserProfile($user);
        $mergedProfile = array_merge($currentFormatted['profile'], $validated['profile'] ?? []);
        self::saveUserProfileData($user, $mergedProfile);

        return response()->json([
            'success' => true,
            'message' => 'Informações do perfil salvas e sincronizadas com o Jeffrey!',
            'user' => self::formatUserProfile($user->fresh()),
            'token' => self::issueSignedToken($user),
        ]);
    }

    /**
     * List all registered profiles in the Empire OS.
     */
    public function listProfiles(): JsonResponse
    {
        $users = User::orderBy('id', 'asc')->get();
        return response()->json([
            'success' => true,
            'profiles' => $users->map(fn (User $u) => self::formatUserProfile($u)),
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
            'user' => self::formatUserProfile($user),
            'system' => [
                'app_name' => config('app.name', 'SpirandeliEmpire OS'),
                'version' => '3.0.0',
                'env' => config('app.env', 'production'),
            ],
        ]);
    }

    /**
     * User Logout — revokes token signature in Redis so it cannot be reused.
     */
    public function logout(Request $request): JsonResponse
    {
        $token = $request->bearerToken();
        if ($token && str_contains($token, '.')) {
            [, $sig] = explode('.', $token, 2);
            try {
                Redis::setex("empire:auth:revoked:{$sig}", 86400 * 30, '1');
            } catch (\Exception $e) {}
        }

        return response()->json([
            'success' => true,
            'message' => 'Sessão encerrada e token revogado com sucesso.',
        ]);
    }

    /**
     * Issue stateless HMAC-SHA256 signed bearer token (no extra table required).
     */
    public static function issueSignedToken(User $user): string
    {
        $secret = self::getSigningSecret();
        $payload = [
            'uid' => $user->id,
            'email' => $user->email,
            'role' => $user->role,
            'iat' => time(),
            'exp' => time() + (86400 * 30), // 30 days
            'jti' => bin2hex(random_bytes(8)),
            'phash' => substr(hash_hmac('sha256', (string) $user->password, $secret), 0, 16),
        ];

        $payloadB64 = rtrim(strtr(base64_encode(json_encode($payload)), '+/', '-_'), '=');
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

        try {
            if (Redis::get("empire:auth:revoked:{$sig}")) {
                return null;
            }
        } catch (\Exception $e) {}

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

        // Invalidate token automatically if user changed their password (supports both new HMAC phash and legacy md5 phash)
        $expectedHmacPhash = substr(hash_hmac('sha256', (string) $user->password, $secret), 0, 16);
        $legacyMd5Phash = substr(md5((string) $user->password), 0, 10);
        if (!empty($data['phash'])) {
            $providedPhash = (string) $data['phash'];
            if (!hash_equals($expectedHmacPhash, $providedPhash) && !hash_equals($legacyMd5Phash, $providedPhash)) {
                return null;
            }
        }

        return $user;
    }

    protected static function getSigningSecret(): string
    {
        return (string) (config('app.key') ?: env('APP_KEY') ?: 'spirandeli-empire-sovereign-key-2026');
    }
}
