<?php

namespace App\Http\Requests\Integration;

use Illuminate\Foundation\Http\FormRequest;

class SaveGeminiRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'api_key' => ['required', 'string', 'min:20', 'max:255'],
            'model' => ['nullable', 'string', 'max:64', 'regex:/^[a-zA-Z0-9._-]+$/'],
        ];
    }
}

