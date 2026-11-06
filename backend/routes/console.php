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
