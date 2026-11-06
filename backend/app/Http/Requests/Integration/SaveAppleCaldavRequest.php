<?php

namespace App\Http\Requests\Integration;

use Illuminate\Foundation\Http\FormRequest;

class SaveAppleCaldavRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /** Senha de app do iCloud: 4 blocos de 4 letras minúsculas (xxxx-xxxx-xxxx-xxxx). */
    public function rules(): array
    {
        return [
            'apple_id' => ['required', 'string', 'email', 'max:190'],
            'app_password' => ['required', 'string', 'regex:/^[a-z]{4}(-[a-z]{4}){3}$/'],
            'server_url' => ['nullable', 'url:https', 'max:255'],
        ];
    }

    public function messages(): array
    {
        return [
            'app_password.regex' => 'Use a Senha Específica de App do iCloud (formato xxxx-xxxx-xxxx-xxxx), não a senha do Apple ID.',
        ];
    }
}

