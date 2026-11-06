<?php

use App\Exceptions\StateTransitionException;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        // Sanctum SPA: cookies de sessão + CSRF para requests vindos de SANCTUM_STATEFUL_DOMAINS;
        // requests sem esse Origin/Referer (apps, Atalhos, testes) usam Bearer token.
        $middleware->statefulApi();

        $middleware->alias([
            'admin' => \App\Http\Middleware\EnsureUserIsAdmin::class,
        ]);
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        // A API sempre responde JSON (401 em vez de redirect para /login).
        $exceptions->shouldRenderJsonWhen(
            fn (Request $request) => $request->is('api/*') || $request->expectsJson()
        );

        // Transições inválidas (ex.: aprovar item já descartado) => 409 Conflict.
        $exceptions->render(function (StateTransitionException $e, Request $request) {
            return response()->json(['message' => $e->getMessage()], 409);
        });
    })->create();

