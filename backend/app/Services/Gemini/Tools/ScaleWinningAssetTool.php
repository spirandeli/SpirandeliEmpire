<?php

namespace App\Services\Gemini\Tools;

use App\Enums\ApprovalStatus;
use App\Models\ApprovalQueue;
use App\Models\Business;
use App\Models\ContentAsset;
use App\Models\Task;
use App\Services\ApprovalService;
use Illuminate\Validation\ValidationException;

class ScaleWinningAssetTool extends AbstractTool
{
    public function __construct(private readonly ?ApprovalService $approvalService = null)
    {
    }

    public function name(): string
    {
        return 'scaleWinningAsset';
    }

    public function description(): string
    {
        return 'Gera novas variações criativas com ganchos (Hooks) e ângulos aprimorados a partir de um ativo vencedor com alto ROI, submetendo o pacote para a fila de aprovação humana com badge de Auto-Otimização de ROI.';
    }

    public function parameters(): array
    {
        return [
            'type' => 'OBJECT',
            'properties' => [
                'winning_asset_id' => [
                    'type' => 'INTEGER',
                    'description' => 'ID do ContentAsset vencedor com métricas comprovadas.',
                ],
                'new_hooks' => [
                    'type' => 'ARRAY',
                    'items' => ['type' => 'STRING'],
                    'description' => 'Lista com 3 variações de ganchos (Hooks) para os primeiros 3 segundos.',
                ],
                'angle_category' => [
                    'type' => 'STRING',
                    'description' => 'Categoria de ângulo de abordagem (ex: dor_direta, curiosidade, prova_social, contraintuitivo).',
                ],
                'reasoning' => [
                    'type' => 'STRING',
                    'description' => 'Diagnóstico e justificativa de por que este criativo funcionou e como as variações vão escalar o faturamento.',
                ],
                'variation_script' => [
                    'type' => 'STRING',
                    'description' => 'Roteiro adaptado ou instrução visual para a nova versão.',
                ],
            ],
            'required' => ['winning_asset_id', 'new_hooks', 'reasoning'],
        ];
    }

    public function execute(array $arguments, ToolExecutionContext $context): array
    {
        $businessId = $context->business?->id;
        $winningAssetId = (int) ($arguments['winning_asset_id'] ?? 0);
        $newHooks = (array) ($arguments['new_hooks'] ?? []);
        $angleCategory = (string) ($arguments['angle_category'] ?? 'dor_direta');
        $reasoning = (string) ($arguments['reasoning'] ?? '');
        $variationScript = (string) ($arguments['variation_script'] ?? '');

        $winningAsset = ContentAsset::find($winningAssetId);
        if (!$winningAsset) {
            throw ValidationException::withMessages(['winning_asset_id' => 'Ativo vencedor não encontrado.']);
        }

        $business = $winningAsset->business;
        if ($context->user && $business->user_id !== $context->user->id) {
            throw ValidationException::withMessages(['winning_asset_id' => 'Acesso não autorizado ao ativo deste negócio.']);
        }

        $createdAssets = [];
        foreach ($newHooks as $index => $hookText) {
            $createdAssets[] = ContentAsset::create([
                'business_id' => $business->id,
                'parent_id' => $winningAsset->id,
                'tiktok_product_id' => $winningAsset->tiktok_product_id,
                'type' => ContentAsset::TYPE_HOOK,
                'platform' => $winningAsset->platform ?: 'tiktok',
                'title' => "Variação #" . ($index + 1) . " (Base: {$winningAsset->tracking_code})",
                'body' => $hookText,
                'funnel_stage' => $winningAsset->funnel_stage ?: ContentAsset::STAGE_TOF_ATTRACTION,
                'angle_category' => $angleCategory,
                'status' => 'pending_approval',
                'metadata' => [
                    'is_scaled_winner' => true,
                    'parent_tracking_code' => $winningAsset->tracking_code,
                    'parent_roi_score' => $winningAsset->roi_score,
                    'parent_revenue' => $winningAsset->total_revenue_brl,
                ],
            ]);
        }

        // Submete para a fila de supervisão humana
        $approval = ApprovalQueue::create([
            'business_id' => $business->id,
            'user_id' => $business->user_id,
            'type' => 'roi_scaling',
            'status' => ApprovalStatus::Pending,
            'priority' => 'high',
            'title' => "⚡ Escalação de Vencedor: {$winningAsset->tracking_code} (ROI: {$winningAsset->roi_score})",
            'summary' => $reasoning,
            'payload' => [
                'winning_asset_id' => $winningAsset->id,
                'parent_tracking_code' => $winningAsset->tracking_code,
                'parent_revenue_brl' => $winningAsset->total_revenue_brl,
                'parent_sales_count' => $winningAsset->total_sales_count,
                'parent_roi_score' => $winningAsset->roi_score,
                'angle_category' => $angleCategory,
                'new_hooks' => $newHooks,
                'variation_script' => $variationScript,
                'reasoning' => $reasoning,
                'badge' => 'Auto-Otimização de ROI',
            ],
        ]);

        return [
            'success' => true,
            'message' => '3 novas variações criadas e enviadas para supervisão humana com badge de ROI Scaling.',
            'winning_asset_id' => $winningAsset->id,
            'approval_queue_id' => $approval->id,
            'variations_count' => count($createdAssets),
        ];
    }
}
