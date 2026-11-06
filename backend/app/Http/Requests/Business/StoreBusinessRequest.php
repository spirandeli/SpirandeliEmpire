<?php

namespace App\Http\Requests\Business;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StoreBusinessRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'name' => ['required', 'string', 'max:120'],
            'type' => ['sometimes', Rule::in(config('abvos.business_types'))],
            'archetype' => ['sometimes', 'nullable', 'string', 'max:48'],
            'north_star_metric' => ['sometimes', 'nullable', 'string', 'max:48'],
            'target_kpi_value' => ['sometimes', 'nullable', 'numeric'],
            'niche' => ['nullable', 'string', 'max:190'],
            'description' => ['nullable', 'string', 'max:5000'],
            'canvas' => ['sometimes', 'array'],
            'brand_rules' => ['sometimes', 'array'],
            'goals' => ['sometimes', 'array'],
            'acquisition_channels' => ['sometimes', 'array'],
            'automation_playbook' => ['sometimes', 'array'],
            'kpis' => ['sometimes', 'array'],
            'with_default_automations' => ['sometimes', 'boolean'],
        ];
    }
}

