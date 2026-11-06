<?php

namespace App\Services\Gemini\Tools;

abstract class AbstractTool implements ToolInterface
{
    public function toFunctionDeclaration(): array
    {
        return [
            'name' => $this->name(),
            'description' => $this->description(),
            'parameters' => $this->parameters(),
        ];
    }
}

