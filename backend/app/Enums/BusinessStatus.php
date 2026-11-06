<?php

namespace App\Enums;

enum BusinessStatus: string
{
    case Draft = 'draft';
    case Planning = 'planning';
    case Active = 'active';
    case Paused = 'paused';
    case Archived = 'archived';
}
