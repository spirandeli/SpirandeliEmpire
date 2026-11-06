<?php

namespace App\Http\Requests\Auth;

use Illuminate\Foundation\Http\FormRequest;

class UpdateProfileRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'name' => ['sometimes', 'string', 'max:120'],
            'timezone' => ['sometimes', 'timezone:all'],
            'locale' => ['sometimes', 'string', 'in:pt_BR,en'],
            'agent_enabled' => ['sometimes', 'boolean'],
            'settings' => ['sometimes', 'array'],
        ];
    }
}

