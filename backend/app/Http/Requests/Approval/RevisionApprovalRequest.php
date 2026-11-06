<?php

namespace App\Http\Requests\Approval;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class RevisionApprovalRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'feedback' => ['required', 'string', 'min:5', 'max:2000'],
            'section' => ['nullable', Rule::in(config('abvos.revision_sections'))],
        ];
    }
}

