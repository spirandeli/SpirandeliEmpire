<?php

namespace App\Enums;

enum TaskStatus: string
{
    case Backlog = 'backlog';
    case InProgressAgent = 'in_progress_agent';
    case AwaitingSupervision = 'awaiting_supervision';
    case TodoUser = 'todo_user';
    case Done = 'done';

    public function label(): string
    {
        return match ($this) {
            self::Backlog => 'Backlog',
            self::InProgressAgent => 'Em Execução (IA Worker)',
            self::AwaitingSupervision => 'Aguardando Supervisão',
            self::TodoUser => 'A Fazer (Humano)',
            self::Done => 'Concluído',
        };
    }

    public function isOpen(): bool
    {
        return $this !== self::Done;
    }
}
