<?php

namespace App\Http\Requests\Task;

use App\Enums\TaskAssignee;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class UpdateTaskRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    /** Status só muda via PATCH /tasks/{id}/move. */
    public function rules(): array
    {
        return [
            'title' => ['sometimes', 'string', 'max:255'],
            'description' => ['nullable', 'string', 'max:10000'],
            'assignee' => ['sometimes', Rule::enum(TaskAssignee::class)],
            'priority' => ['sometimes', 'in:low,medium,high,urgent'],
            'due_at' => ['nullable', 'date'],
            'scheduled_at' => ['nullable', 'date'],
            'agent_action' => ['nullable', 'string', 'max:64'],
            'payload' => ['nullable', 'array'],
        ];
    }
}

