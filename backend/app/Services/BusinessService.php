<?php

namespace App\Services;

use App\Enums\BusinessStatus;
use App\Enums\LogLevel;
use App\Models\AgentLog;
use App\Models\Business;
use App\Models\BusinessAutomation;
use App\Models\User;
use Illuminate\Support\Facades\DB;

/**
 * Regras de negócio de `businesses`. Reutilizado pelos controllers REST
 * e (Fase 3) pela tool `createBusinessVenture` do Gemini.
 */
class BusinessService
{
    public function create(User $user, array $data, bool $withDefaultAutomations = true): Business
    {
        return DB::transaction(function () use ($user, $data, $withDefaultAutomations) {
            $business = $user->businesses()->create(array_merge(
                ['type' => 'custom', 'status' => BusinessStatus::Draft->value],
                $data,
            ));

            if ($withDefaultAutomations) {
                foreach ($this->defaultAutomationsFor($business) as $automation) {
                    $business->automations()->create($automation);
                }
            }

            AgentLog::record($user->id, 'business_created', "Negócio \"{$business->name}\" criado.", LogLevel::Success,
                ['type' => $business->type], ['business_id' => $business->id]);

            return $business->load('automations');
        });
    }

    public function update(Business $business, array $data): Business
    {
        $business->update($data);

        return $business->refresh()->load('automations');
    }

    /** Ativa o negócio e libera os workers autônomos para operá-lo. */
    public function activate(Business $business): Business
    {
        $business->forceFill([
            'status' => BusinessStatus::Active,
            'automation_enabled' => true,
            'activated_at' => $business->activated_at ?? now(),
        ])->save();

        // Garante next_run_at calculado nas automações habilitadas.
        $business->automations()->where('is_enabled', true)->get()->each(function (BusinessAutomation $a) {
            if ($a->next_run_at === null || $a->next_run_at->isPast()) {
                $a->forceFill(['next_run_at' => $a->computeNextRun()])->save();
            }
        });

        AgentLog::record($business->user_id, 'business_activated', "Negócio \"{$business->name}\" ativado: agente autônomo liberado.",
            LogLevel::Success, [], ['business_id' => $business->id]);

        return $business->refresh()->load('automations');
    }

    public function pause(Business $business): Business
    {
        $business->forceFill(['status' => BusinessStatus::Paused, 'automation_enabled' => false])->save();

        AgentLog::record($business->user_id, 'business_paused', "Negócio \"{$business->name}\" pausado.",
            LogLevel::Warning, [], ['business_id' => $business->id]);

        return $business->refresh()->load('automations');
    }

    /**
     * Automações padrão por tipo de negócio.
     *
     * @return array<int, array<string, mixed>>
     */
    public function defaultAutomationsFor(Business $business): array
    {
        if (! $business->isTikTokShopAffiliate()) {
            return [];
        }

        return [
            [
                'type' => BusinessAutomation::TYPE_TIKTOK_MINING,
                'name' => 'Mineração de produtos em alta',
                'cron_expression' => '0 */6 * * *',
                'config' => [
                    'categories' => [],
                    'min_commission_rate' => 10,
                    'min_price' => 0,
                    'max_items_per_run' => 30,
                    'min_overall_score' => 60,
                ],
            ],
            [
                'type' => BusinessAutomation::TYPE_CONTENT_GENERATION,
                'name' => 'Geração de roteiros e hooks',
                'cron_expression' => '30 */6 * * *',
                'config' => [
                    'max_products_per_run' => 3,
                    'hooks_per_package' => 3,
                    'require_approval' => true,
                ],
            ],
        ];
    }
}

