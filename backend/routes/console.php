<?php

use Illuminate\Support\Facades\Schedule;

/*
|--------------------------------------------------------------------------
| Console Routes & Task Scheduler
|--------------------------------------------------------------------------
| Executado 24/7 pelo container `worker` via `php artisan schedule:work`.
*/

Schedule::command('abvos:run-automations')
    ->everyMinute()
    ->withoutOverlapping(10)
    ->runInBackground();

Schedule::command('abvos:optimize-growth')
    ->dailyAt('03:00')
    ->withoutOverlapping(30)
    ->runInBackground();

Schedule::command('language:generate-daily-lessons')
    ->dailyAt('04:00')
    ->withoutOverlapping(15)
    ->runInBackground();
