<?php

return [

    // Em VPS pública, desligue após criar sua conta (REGISTRATION_ENABLED=false).
    'registration_enabled' => (bool) env('REGISTRATION_ENABLED', true),

    'business_types' => [
        'tiktok_shop_affiliate',
        'dropshipping',
        'digital_product',
        'content_channel',
        'custom',
    ],

    'automation_types' => [
        'tiktok_product_mining',
        'affiliate_content_generation',
        'calendar_sync',
        'performance_review',
        'custom',
    ],

    // Pacotes sem decisão após esse prazo expiram (job da Fase 5).
    'approval_default_expiry_hours' => 72,

    // Seções que o usuário pode pedir para o agente reescrever.
    'revision_sections' => ['hooks', 'script', 'visual_prompts', 'caption', 'hashtags', 'cta', 'all'],
];

