<?php

namespace App\Http\Requests\Business;

use Cron\CronExpression;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class AutomationRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        $creating = $this->isMethod('POST');
        $required = $creating ? 'required' : 'sometimes';
        $business = $this->route('business');
        $automation = $this->route('automation');

        return [
            'type' => [$required, Rule::in(config('abvos.automation_types'))],
            'name' => [
                $required, 'string', 'max:160',
                Rule::unique('business_automations', 'name')
                    ->where('business_id', $business->id)
                    ->where('type', $this->input('type', $automation?->type))
                    ->ignore($automation?->id),
            ],
            'cron_expression' => [$required, 'string', 'max:64', function ($attr, $value, $fail) {
                if (! CronExpression::isValidExpression($value)) {
                    $fail('Expressão cron inválida.');
                }
            }],
            'timezone' => ['sometimes', 'timezone:all'],
            'is_enabled' => ['sometimes', 'boolean'],
            'config' => ['sometimes', 'nullable', 'array'],
        ];
    }
}

