<?php

namespace App\Http\Requests\Approval;

use Illuminate\Foundation\Http\FormRequest;

class ApproveApprovalRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'scheduled_for' => ['nullable', 'date', 'after:now'],
            'selected_hook_index' => ['nullable', 'integer', 'min:0', 'max:20'],
        ];
    }
}

