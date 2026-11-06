<?php

namespace App\Enums;

enum AgentMessageRole: string
{
    case User = 'user';
    case Model = 'model';
    case Tool = 'tool';

    /** Role aceito pela REST API do Gemini (respostas de função voltam como `user`). */
    public function toGeminiRole(): string
    {
        return $this === self::Model ? 'model' : 'user';
    }
}
