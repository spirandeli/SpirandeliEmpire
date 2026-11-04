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
        // Allow internal Telegram Bot container requests on /api/v1/jeffrey/chat
        if ($request->is('api/v1/jeffrey/chat')) {
            $internalSecret = env('INTERNAL_API_SECRET');
            $providedSecret = $request->header('X-Internal-Secret') ?: $request->input('internal_secret');
            if (
                ($internalSecret && hash_equals($internalSecret, (string) $providedSecret)) ||
                str_starts_with((string) $request->ip(), '172.') ||
                str_starts_with((string) $request->ip(), '10.') ||
                $request->ip() === '127.0.0.1'
            ) {
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

