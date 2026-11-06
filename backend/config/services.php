<?php

return [

    'postmark' => [
        'token' => env('POSTMARK_TOKEN'),
    ],

    'ses' => [
        'key' => env('AWS_ACCESS_KEY_ID'),
        'secret' => env('AWS_SECRET_ACCESS_KEY'),
        'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
    ],

    'slack' => [
        'notifications' => [
            'bot_user_oauth_token' => env('SLACK_BOT_USER_OAUTH_TOKEN'),
            'channel' => env('SLACK_BOT_USER_DEFAULT_CHANNEL'),
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Gemini (REST API)
    |--------------------------------------------------------------------------
    | `api_key` é o fallback do sistema; a chave do usuário (user_integrations,
    | provider=gemini, criptografada) tem precedência.
    */
    'gemini' => [
        'base_url' => env('GEMINI_API_BASE', 'https://generativelanguage.googleapis.com/v1beta'),
        'model' => env('GEMINI_MODEL', 'gemini-3.8'),
        'api_key' => env('GEMINI_API_KEY'),
        'timeout' => 120,
    ],

    'google' => [
        'client_id' => env('GOOGLE_CLIENT_ID'),
        'client_secret' => env('GOOGLE_CLIENT_SECRET'),
        'redirect' => env('GOOGLE_REDIRECT_URI'),
        'scopes' => [
            'openid', 'email',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/tasks',
        ],
    ],

];
