<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class EnsureUserIsAdmin
{
    /**
     * Garante que apenas usuários com `is_admin = true` possam acessar as rotas de governança.
     */
    public function handle(Request $request, Closure $next): Response
    {
        $user = $request->user();

        if (! $user || ! $user->isAdmin()) {
            return response()->json([
                'message' => 'Acesso negado. Esta área requer privilégios de Administrador do Sistema.',
                'error' => 'forbidden',
            ], Response::HTTP_FORBIDDEN);
        }

        return $next($request);
    }
}

