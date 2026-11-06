<?php

namespace App\Services\Playbooks;

use App\Models\Business;
use App\Services\Playbooks\Contracts\BusinessPlaybookInterface;

class BusinessPlaybookFactory
{
    /**
     * Retorna a instância do playbook especializado para o arquétipo fornecido
     */
    public static function forArchetype(?string $archetype): BusinessPlaybookInterface
    {
        return match ($archetype) {
            Business::ARCHETYPE_INFOPRODUCT => new InfoproductLaunchPlaybook(),
            Business::ARCHETYPE_SAAS => new SaasGrowthPlaybook(),
            Business::ARCHETYPE_ECOMMERCE => new EcommerceDropPlaybook(),
            default => new AffiliateTikTokPlaybook(),
        };
    }

    /**
     * Retorna a lista de todos os playbooks suportados
     */
    public static function all(): array
    {
        return [
            new AffiliateTikTokPlaybook(),
            new InfoproductLaunchPlaybook(),
            new SaasGrowthPlaybook(),
            new EcommerceDropPlaybook(),
        ];
    }
}

