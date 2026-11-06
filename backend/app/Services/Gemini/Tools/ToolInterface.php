<?php

namespace App\Services\Gemini\Tools;

interface ToolInterface
{
    /**
     * Nome da função registrado para o Gemini (ex: createBusinessVenture).
     */
    public function name(): string;

    /**
     * Descrição detalhada instruindo o modelo sobre a finalidade da tool.
     */
    public function description(): string;

    /**
     * Definição OpenAPI Schema dos parâmetros que a função aceita.
     *
     * @return array<string, mixed>
     */
    public function parameters(): array;

    /**
     * Executa a lógica em PHP com os argumentos validados pelo modelo.
     *
     * @param  array<string, mixed>  $arguments
     * @param  ToolExecutionContext  $context
     * @return array<string, mixed>
     */
    public function execute(array $arguments, ToolExecutionContext $context): array;

    /**
     * Retorna a declaração no formato esperado pela API do Gemini.
     *
     * @return array{name: string, description: string, parameters: array<string, mixed>}
     */
    public function toFunctionDeclaration(): array;
}

