<?php

namespace App\Http\Controllers;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Http\Request;

abstract class Controller
{
    /**
     * Isolamento multi-tenant: recurso de outro usuário responde 404 (não vaza a existência).
     *
     * @template T of Model
     *
     * @param  T  $model
     * @return T
     */
    protected function owned(Model $model, Request $request): Model
    {
        abort_unless((int) $model->getAttribute('user_id') === (int) $request->user()->id, 404);

        return $model;
    }
}

