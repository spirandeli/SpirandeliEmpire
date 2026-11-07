<?php

namespace App\Console\Commands;

use App\Jobs\GenerateDailyLanguageLessonJob;
use App\Models\LanguageProfile;
use Carbon\Carbon;
use Illuminate\Console\Command;

class GenerateDailyLanguageLessonsCommand extends Command
{
    protected $signature = 'language:generate-daily-lessons';

    protected $description = 'Gera automaticamente as micro-sessões de 15 minutos para os perfis de idiomas ativos';

    public function handle(): int
    {
        $today = Carbon::today();
        $dayOfWeekMap = [
            1 => 'MON',
            2 => 'TUE',
            3 => 'WED',
            4 => 'THU',
            5 => 'FRI',
            6 => 'SAT',
            7 => 'SUN',
        ];

        $currentDayCode = $dayOfWeekMap[$today->dayOfWeekIso] ?? 'MON';

        $profiles = LanguageProfile::where('is_active', true)
            ->where('cefr_level', '!=', 'UNSET')
            ->get();

        $count = 0;
        foreach ($profiles as $profile) {
            $studyDays = $profile->study_days ?? [];

            $shouldStudyToday = in_array('ALL', $studyDays, true)
                || in_array($currentDayCode, array_map('strtoupper', $studyDays), true);

            if ($shouldStudyToday) {
                GenerateDailyLanguageLessonJob::dispatch($profile, $today->toDateString());
                $count++;
            }
        }

        $this->info("Disparada a geração de {$count} sessões diárias de idiomas.");

        return self::SUCCESS;
    }
}
