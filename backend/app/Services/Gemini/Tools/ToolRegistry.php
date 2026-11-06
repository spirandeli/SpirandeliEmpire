<?php

namespace App\Services\Gemini\Tools;

use Illuminate\Support\Collection;

class ToolRegistry
{
    /**
     * @var array<string, ToolInterface>
     */
    private array $tools = [];

    /**
     * @var array<string, string>
     */
    private array $aliases = [
        'initialize_business_venture' => 'createBusinessVenture',
        'create_business_venture' => 'createBusinessVenture',
        'create_task' => 'createTask',
        'submit_for_approval' => 'submitForHumanApproval',
        'submit_for_human_approval' => 'submitForHumanApproval',
        'get_user_schedule' => 'checkUserSchedule',
        'check_user_schedule' => 'checkUserSchedule',
        'save_tiktok_product_strategy' => 'saveTikTokProductStrategy',
    ];

    /**
     * @param  array<int, ToolInterface>  $tools
     */
    public function __construct(array $tools = [])
    {
        foreach ($tools as $tool) {
            $this->register($tool);
        }
    }

    public function register(ToolInterface $tool): self
    {
        $this->tools[$tool->name()] = $tool;

        return $this;
    }

    public function registerAlias(string $alias, string $targetName): self
    {
        $this->aliases[$alias] = $targetName;

        return $this;
    }

    public function get(string $name): ?ToolInterface
    {
        $resolved = $this->aliases[$name] ?? $name;

        return $this->tools[$resolved] ?? null;
    }

    public function has(string $name): bool
    {
        $resolved = $this->aliases[$name] ?? $name;

        return isset($this->tools[$resolved]);
    }

    /**
     * Retorna a lista de todas as tools formatada para a chave `tools` do Gemini.
     *
     * @return array<int, array{functionDeclarations: array<int, mixed>}>
     */
    public function toGeminiTools(): array
    {
        if (empty($this->tools)) {
            return [];
        }

        $declarations = Collection::make($this->tools)
            ->map(fn (ToolInterface $tool) => $tool->toFunctionDeclaration())
            ->values()
            ->all();

        return [
            [
                'functionDeclarations' => $declarations,
            ],
        ];
    }

    /**
     * Executa uma tool pelo nome com os argumentos passados.
     *
     * @param  string  $name
     * @param  array<string, mixed>  $arguments
     * @param  ToolExecutionContext  $context
     * @return array<string, mixed>
     */
    public function execute(string $name, array $arguments, ToolExecutionContext $context): array
    {
        $tool = $this->get($name);

        if (! $tool) {
            return [
                'success' => false,
                'error' => "A ferramenta \"{$name}\" não está registrada no sistema.",
            ];
        }

        return $tool->execute($arguments, $context);
    }
}

