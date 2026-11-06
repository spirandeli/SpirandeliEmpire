<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AgentLearning extends Model
{
    use HasFactory;

    protected $fillable = [
        'business_id',
        'topic',
        'insight',
        'confidence_score',
        'data_source',
        'metadata',
    ];

    protected function casts(): array
    {
        return [
            'confidence_score' => 'integer',
            'metadata' => 'array',
        ];
    }

    public function business(): BelongsTo
    {
        return $this->belongsTo(Business::class);
    }
}
