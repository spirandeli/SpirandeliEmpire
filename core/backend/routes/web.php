<?php

use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return response()->json([
        'message' => 'SpirandeliEmpire OS Core API',
        'status' => 'online',
        'docs' => '/api/health'
    ]);
});

