<?php

namespace App\Enums;

enum TaskAssignee: string
{
    case Agent = 'agent';
    case User = 'user';

    public function label(): string
    {
        return match ($this) {
            self::Agent => 'Agente IA',
            self::User => 'Humano',
        };
    }
}
