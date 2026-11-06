<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\AgentLogResource;
use App\Models\AgentLog;
use Illuminate\Http\Request;

/** Console em tempo real do agente: o front faz polling com `after_id`. */
class AgentLogController extends Controller
{
    public function index(Request $request)
    {
        $request->validate([
            'business_id' => ['sometimes', 'integer'],
            'task_id' => ['sometimes', 'integer'],
            'level' => ['sometimes', 'in:debug,info,success,warning,error'],
            'after_id' => ['sometimes', 'integer', 'min:0'],
            'limit' => ['sometimes', 'integer', 'min:1', 'max:500'],
        ]);

        $limit = $request->integer('limit', 100);

        $query = AgentLog::query()
            ->where('user_id', $request->user()->id)
            ->when($request->filled('business_id'), fn ($q) => $q->where('business_id', $request->business_id))
            ->when($request->filled('task_id'), fn ($q) => $q->where('task_id', $request->task_id))
            ->when($request->filled('level'), fn ($q) => $q->where('level', $request->level));

        if ($request->filled('after_id')) {
            $logs = $query->after($request->integer('after_id'))->limit($limit)->get();
        } else {
            // Carga inicial: as últimas N linhas em ordem cronológica.
            $logs = $query->latest('id')->limit($limit)->get()->reverse()->values();
        }

        return AgentLogResource::collection($logs)->additional([
            'meta' => ['last_id' => $logs->max('id')],
        ]);
    }
}

