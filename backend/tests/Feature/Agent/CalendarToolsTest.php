<?php

namespace Tests\Feature\Agent;

use App\Models\CalendarEvent;
use App\Models\User;
use App\Services\AppleCalDavService;
use App\Services\Gemini\Tools\CreateCalendarEventTool;
use App\Services\Gemini\Tools\CreateReminderTool;
use App\Services\Gemini\Tools\ToolExecutionContext;
use App\Services\GoogleWorkspaceService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class CalendarToolsTest extends TestCase
{
    use RefreshDatabase;

    private User $user;

    protected function setUp(): void
    {
        parent::setUp();
        $this->user = User::factory()->create();
    }

    public function test_create_calendar_event_tool_persists_in_unified_calendar(): void
    {
        $tool = new CreateCalendarEventTool(
            app(GoogleWorkspaceService::class),
            app(AppleCalDavService::class)
        );

        $context = new ToolExecutionContext($this->user);

        $result = $tool->execute([
            'title' => '[Gravação TikTok] Vídeo Mini Aspirador',
            'starts_at' => now()->addDay()->setHour(14)->setMinute(0)->toIso8601String(),
            'ends_at' => now()->addDay()->setHour(15)->setMinute(0)->toIso8601String(),
            'description' => 'Gravar os 3 hooks e demonstração prática.',
        ], $context);

        $this->assertTrue($result['success']);
        $this->assertDatabaseHas('calendar_events', [
            'user_id' => $this->user->id,
            'title' => '[Gravação TikTok] Vídeo Mini Aspirador',
            'kind' => 'event',
            'created_by_agent' => true,
        ]);
    }

    public function test_create_reminder_tool_persists_in_unified_calendar(): void
    {
        $tool = new CreateReminderTool(
            app(GoogleWorkspaceService::class),
            app(AppleCalDavService::class)
        );

        $context = new ToolExecutionContext($this->user);

        $result = $tool->execute([
            'title' => 'Aprovar roteiro de vídeo antes das 18h',
            'due_at' => now()->addHours(2)->toIso8601String(),
            'priority' => 'high',
        ], $context);

        $this->assertTrue($result['success']);
        $this->assertDatabaseHas('calendar_events', [
            'user_id' => $this->user->id,
            'title' => 'Aprovar roteiro de vídeo antes das 18h',
            'kind' => 'reminder',
            'created_by_agent' => true,
        ]);
    }
}

