<?php

namespace App\Http\Requests\Business;

use Illuminate\Foundation\Http\FormRequest;

class UpdateBusinessRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /** Status muda apenas via /activate e /pause; o type é imutável após a criação. */
    public function rules(): array
    {
        return [
            'name' => ['sometimes', 'string', 'max:120'],
            'archetype' => ['sometimes', 'nullable', 'string', 'max:48'],
            'north_star_metric' => ['sometimes', 'nullable', 'string', 'max:48'],
            'target_kpi_value' => ['sometimes', 'nullable', 'numeric'],
            'niche' => ['nullable', 'string', 'max:190'],
            'description' => ['nullable', 'string', 'max:5000'],
            'canvas' => ['sometimes', 'nullable', 'array'],
            'brand_rules' => ['sometimes', 'nullable', 'array'],
            'goals' => ['sometimes', 'nullable', 'array'],
            'acquisition_channels' => ['sometimes', 'nullable', 'array'],
            'automation_playbook' => ['sometimes', 'nullable', 'array'],
            'kpis' => ['sometimes', 'nullable', 'array'],
            'ai_summary' => ['sometimes', 'nullable', 'string', 'max:10000'],
        ];
    }
}

