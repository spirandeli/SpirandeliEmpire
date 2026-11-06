<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AiUsageLog extends Model
{
    use HasFactory;

    protected $fillable = [
        'user_id',
        'business_id',
        'agent_conversation_id',
        'model',
        'context',
        'prompt_tokens',
        'completion_tokens',
        'total_tokens',
        'estimated_cost_usd',
        'latency_ms',
    ];

    protected function casts(): array
    {
        return [
            'prompt_tokens' => 'integer',
            'completion_tokens' => 'integer',
            'total_tokens' => 'integer',
            'estimated_cost_usd' => 'decimal:6',
            'latency_ms' => 'integer',
            'created_at' => 'datetime',
            'updated_at' => 'datetime',
        ];
    }

    public function user(): BelongsTo
    {
        return $this->belongsTo(User::class);
    }

    public function business(): BelongsTo
    {
        return $this->belongsTo(Business::class);
    }

    public function conversation(): BelongsTo
    {
        return $this->belongsTo(AgentConversation::class, 'agent_conversation_id');
    }

    /**
     * Calcula o custo estimado em dólares para a chamada com base no modelo.
     */
    public static function calculateCostUsd(string $model, int $promptTokens, int $completionTokens): float
    {
        // Tabela de precificação oficial Gemini v1beta (por milhão de tokens)
        $isFlash = str_contains(strtolower($model), 'flash');

        if ($isFlash) {
            // ~$0.075 por milhão prompt / ~$0.30 por milhão output
            $promptCost = ($promptTokens / 1_000_000) * 0.075;
            $outputCost = ($completionTokens / 1_000_000) * 0.30;
        } else {
            // Pro / Gemini 3.8: ~$1.25 por milhão prompt / ~$5.00 por milhão output
            $promptCost = ($promptTokens / 1_000_000) * 1.25;
            $outputCost = ($completionTokens / 1_000_000) * 5.00;
        }

        return round($promptCost + $outputCost, 6);
    }
}

