<?php

return [
    /*
    |--------------------------------------------------------------------------
    | Default AI Provider Strategy
    |--------------------------------------------------------------------------
    |
    | Supported: "hybrid", "gemini", "openai", "ollama"
    | - hybrid: prioritizes Google Gemini Free Tier, falls back to OpenAI,
    |   and gracefully degrades to local Llama (Ollama) with 0 cost.
    |
    */
    'default_provider' => env('AI_PROVIDER', 'hybrid'),

    'fallback_order' => explode(',', env('AI_FALLBACK_ORDER', 'gemini,openai,ollama')),

    'monthly_budget_limit_brl' => (float) env('MONTHLY_BUDGET_LIMIT_BRL', 200.00),
    'alert_budget_percentage' => (float) env('ALERT_BUDGET_PERCENTAGE', 80.0),

    /*
    |--------------------------------------------------------------------------
    | Token Management & Task Delimitation
    |--------------------------------------------------------------------------
    | Smart token-based routing between Llama local and Cloud APIs (Gemini/OpenAI)
    */
    'tokens' => [
        'routing_enabled' => (bool) env('TOKEN_ROUTING_ENABLED', true),
        // Tasks with <= 800 tokens run locally on Llama (saving API quotas)
        'threshold_local_max' => (int) env('TOKEN_THRESHOLD_LOCAL_MAX', 800),
        // Tasks with > 3500 tokens route to Gemini 1.5 Flash (1M token window)
        'threshold_long_context' => (int) env('TOKEN_THRESHOLD_LONG_CONTEXT', 3500),
        // Daily API safety token cap
        'daily_api_token_cap' => (int) env('DAILY_API_TOKEN_CAP', 500000),
    ],

    /*
    |--------------------------------------------------------------------------
    | Google AI Studio / Gemini Configuration (Free Tier & Paid)
    |--------------------------------------------------------------------------
    | Free tier provides generous quotas (up to 15 RPM, 1M TPM on Flash)
    | Get your key at: https://aistudio.google.com/app/apikey
    */
    'gemini' => [
        'api_key' => env('GEMINI_API_KEY', ''),
        'default_model' => env('GEMINI_MODEL', 'gemini-3.8-flash'),
        'base_url' => env('GEMINI_BASE_URL', 'https://generativelanguage.googleapis.com/v1beta'),
        'temperature' => (float) env('GEMINI_TEMPERATURE', 0.7),
        'max_tokens' => (int) env('GEMINI_MAX_TOKENS', 4096),
        'free_tier_mode' => (bool) env('GEMINI_FREE_TIER_MODE', true),
    ],

    /*
    |--------------------------------------------------------------------------
    | OpenAI Configuration (Free Trial Credits & Paid Plans)
    |--------------------------------------------------------------------------
    | Supports gpt-4o-mini, gpt-4o, gpt-3.5-turbo, or compatible proxies.
    | Get your key at: https://platform.openai.com/api-keys
    */
    'openai' => [
        'api_key' => env('OPENAI_API_KEY', ''),
        'default_model' => env('OPENAI_MODEL', 'gpt-4o-mini'),
        'base_url' => env('OPENAI_BASE_URL', 'https://api.openai.com/v1'),
        'temperature' => (float) env('OPENAI_TEMPERATURE', 0.7),
        'max_tokens' => (int) env('OPENAI_MAX_TOKENS', 4096),
    ],

    /*
    |--------------------------------------------------------------------------
    | Local Ollama & Llama Configuration (100% Free / On-Premise)
    |--------------------------------------------------------------------------
    | Zero network dependency, runs directly on VPS CPU/RAM or GPU.
    | Popular models: llama3.2:3b, llama3.2:1b, llama3.1:8b, qwen2.5:7b
    */
    'ollama' => [
        'base_url' => env('OLLAMA_BASE_URL', 'http://ollama:11434'),
        'default_model' => env('LLAMA_MODEL', env('DEFAULT_TEXT_MODEL', 'llama3.2:3b')),
        'timeout_seconds' => (int) env('OLLAMA_TIMEOUT_SECONDS', 180),
    ],
];
