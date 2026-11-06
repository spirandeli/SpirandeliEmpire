<?php

namespace App\Jobs;

use App\Enums\LogLevel;
use App\Enums\TaskAssignee;
use App\Enums\TaskStatus;
use App\Models\AgentLog;
use App\Models\ConversionEvent;
use App\Models\Task;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

class HandleFunnelRecoveryJob implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(public ConversionEvent $conversionEvent) {}

    public function handle(): void
    {
        $event = $this->conversionEvent;
        $business = $event->business;

        if (!$business) {
            return;
        }

        $customer = $event->customer_metadata ?? [];
        $customerIdentifier = $customer['name'] ?? $customer['email'] ?? 'Lead não identificado';
        $amountFormatted = 'R$ ' . number_format((float) $event->gross_amount, 2, ',', '.');

        $isPix = $event->event_type === ConversionEvent::EVENT_PIX_GENERATED;
        $actionTitle = $isPix
            ? "Lembrete PIX Pendente: {$customerIdentifier} ({$amountFormatted})"
            : "Recuperação de Carrinho Abandonado: {$customerIdentifier} ({$amountFormatted})";

        $description = "O evento foi registrado via {$event->source_platform}.\n"
            . "Cliente: {$customerIdentifier}\n"
            . "Valor bruto: {$amountFormatted}\n"
            . ($event->content_asset_id ? "Ativo de Origem: #{$event->content_asset_id} ({$event->contentAsset?->tracking_code})\n" : "")
            . "Disparar fluxo de recuperação de alta conversão.";

        // Cria tarefa de alta prioridade no Kanban
        $task = Task::create([
            'business_id' => $business->id,
            'user_id' => $business->user_id,
            'title' => $actionTitle,
            'description' => $description,
            'assignee' => TaskAssignee::Agent,
            'status' => TaskStatus::Backlog,
            'priority' => 'urgent',
            'metadata' => [
                'conversion_event_id' => $event->id,
                'type' => 'funnel_recovery',
                'customer' => $customer,
                'amount' => $event->gross_amount,
            ],
        ]);

        AgentLog::record(
            $business->user_id,
            'funnel_recovery_triggered',
            "Funnel Recovery acionado para evento #{$event->id}: Tarefa #{$task->id} criada.",
            LogLevel::Info,
            ['event_id' => $event->id, 'task_id' => $task->id],
            ['business_id' => $business->id, 'task_id' => $task->id]
        );
    }
}
