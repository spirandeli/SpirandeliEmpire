<?php

namespace App\Enums;

enum IntegrationProvider: string
{
    case Gemini = 'gemini';
    case Google = 'google';
    case AppleCaldav = 'apple_caldav';
    case ShortcutsWebhook = 'shortcuts_webhook';
    case TikTokShop = 'tiktok_shop';
}
