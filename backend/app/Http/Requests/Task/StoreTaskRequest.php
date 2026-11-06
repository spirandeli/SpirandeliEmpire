<?php

namespace App\Http\Requests\Task;

use App\Enums\TaskAssignee;
use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StoreTaskRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'business_id' => ['required', 'integer', Rule::exists('businesses', 'id')
                ->where('user_id', $this->user()->id)->whereNull('deleted_at')],
            'parent_id' => ['nullable', 'integer', Rule::exists('tasks', 'id')->where('user_id', $this->user()->id)],
            'title' => ['required', 'string', 'max:255'],
            'description' => ['nullable', 'string', 'max:10000'],
            'assignee' => ['sometimes', Rule::enum(TaskAssignee::class)],
            'priority' => ['sometimes', 'in:low,medium,high,urgent'],
            'status' => ['sometimes', 'in:backlog,todo_user,awaiting_supervision,done'],
            'due_at' => ['nullable', 'date'],
            'scheduled_at' => ['nullable', 'date'],
            'agent_action' => ['nullable', 'string', 'max:64'],
            'payload' => ['nullable', 'array'],
        ];
    }
}

