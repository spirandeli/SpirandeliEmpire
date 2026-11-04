<?php

namespace App\Http\Middleware;

use App\Http\Controllers\Api\AuthController;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class EmpireAuthMiddleware
{
    /**
     * Handle an incoming request and enforce Commander authentication.
     */
    public function handle(Request $request, Closure $next): Response
    {
        // Allow internal Telegram Bot & Worker container requests on /api/v1/jeffrey/* and /api/v1/tasks*
        if ($request->is('api/v1/jeffrey/*') || $request->is('api/v1/tasks*')) {
            $internalSecret = env('INTERNAL_API_SECRET');
            $providedSecret = $request->header('X-Internal-Secret') ?: $request->input('internal_secret');
            $internalHeader = $request->header('X-Jeffrey-Internal');

            if ($internalSecret && $providedSecret && hash_equals($internalSecret, (string) $providedSecret)) {
                return $next($request);
            }

            // Fallback when INTERNAL_API_SECRET is not set: require internal Docker IP + explicit internal bot header
            $ip = (string) $request->ip();
            $isPrivateIp = str_starts_with($ip, '172.') || str_starts_with($ip, '10.') || $ip === '127.0.0.1';
            if (empty($internalSecret) && $isPrivateIp && $internalHeader === 'telegram-bot') {
                return $next($request);
            }
        }

        $token = $request->bearerToken();
        $user = AuthController::verifySignedToken($token);

        if (!$user) {
            return response()->json([
                'success' => false,
                'unauthenticated' => true,
                'error' => 'Acesso restrito ao Comandante. Autentique-se para acessar o SpirandeliEmpire OS.',
            ], 401);
        }

        $request->setUserResolver(fn () => $user);

        return $next($request);
    }
}

