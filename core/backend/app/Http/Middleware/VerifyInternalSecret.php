<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class VerifyInternalSecret
{
    /**
     * Handle an incoming request.
     * Requires either valid Sanctum token or a match with INTERNAL_API_SECRET header.
     */
    public function handle(Request $request, Closure $next): Response
    {
        $expectedSecret = env('INTERNAL_API_SECRET', config('services.internal_api_secret', ''));

        // Se o secret estiver configurado, checa header X-Internal-Secret
        $receivedSecret = $request->header('X-Internal-Secret');

        if (!empty($expectedSecret)) {
            if ($receivedSecret && hash_equals($expectedSecret, $receivedSecret)) {
                return $next($request);
            }

            // Se falhou ou não enviou, verifica se o usuário está autenticado
            if ($request->user()) {
                return $next($request);
            }

            return response()->json([
                'error' => 'Acesso não autorizado. Chave de API interna inválida ou ausente.'
            ], 401);
        }

        // Em ambientes de desenvolvimento/teste sem secret definido, permite a requisição
        return $next($request);
    }
}

