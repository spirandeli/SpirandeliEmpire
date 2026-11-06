<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Support\Str;

class ContentAsset extends Model
{
    use HasFactory;

    public const TYPE_HOOK = 'hook';
    public const TYPE_VIDEO_SCRIPT = 'video_script';
    public const TYPE_VISUAL_PROMPT = 'visual_prompt';
    public const TYPE_CAPTION = 'caption';
    public const TYPE_HASHTAGS = 'hashtags';
    public const TYPE_CTA = 'cta';
    public const TYPE_THUMBNAIL_PROMPT = 'thumbnail_prompt';

    public const STAGE_TOF_ATTRACTION = 'tof_attraction';
    public const STAGE_MOF_CONVERSION = 'mof_conversion';
    public const STAGE_BOF_RETENTION = 'bof_retention';

    protected $fillable = [
        'tracking_code', 'business_id', 'tiktok_product_id', 'approval_queue_id', 'parent_id',
        'type', 'platform', 'title', 'body', 'content', 'version', 'is_selected',
        'status', 'funnel_stage', 'angle_category', 'total_views', 'total_clicks',
        'total_leads', 'total_sales_count', 'total_revenue_brl', 'roi_score',
        'scheduled_at', 'published_at', 'external_url', 'metadata',
    ];

    protected function casts(): array
    {
        return [
            'content' => 'array',
            'metadata' => 'array',
            'version' => 'integer',
            'is_selected' => 'boolean',
            'total_views' => 'integer',
            'total_clicks' => 'integer',
            'total_leads' => 'integer',
            'total_sales_count' => 'integer',
            'total_revenue_brl' => 'decimal:2',
            'roi_score' => 'decimal:2',
            'scheduled_at' => 'datetime',
            'published_at' => 'datetime',
        ];
    }

    protected static function booted(): void
    {
        static::creating(function (ContentAsset $asset) {
            if (empty($asset->tracking_code)) {
                $asset->tracking_code = 'AST-' . strtoupper(Str::random(6));
            }
            if (empty($asset->funnel_stage)) {
                $asset->funnel_stage = self::STAGE_TOF_ATTRACTION;
            }
        });
    }

    public function business(): BelongsTo
    {
        return $this->belongsTo(Business::class);
    }

    public function product(): BelongsTo
    {
        return $this->belongsTo(TikTokProduct::class, 'tiktok_product_id');
    }

    public function approvalQueue(): BelongsTo
    {
        return $this->belongsTo(ApprovalQueue::class);
    }

    public function parent(): BelongsTo
    {
        return $this->belongsTo(self::class, 'parent_id');
    }

    public function revisions(): HasMany
    {
        return $this->hasMany(self::class, 'parent_id');
    }

    public function conversionEvents(): HasMany
    {
        return $this->hasMany(ConversionEvent::class);
    }

    /** Apenas versões vigentes (ignora as substituídas por revisões). */
    public function scopeCurrent(Builder $query): Builder
    {
        return $query->where('status', '!=', 'superseded');
    }

    public function scopeOfType(Builder $query, string $type): Builder
    {
        return $query->where('type', $type);
    }

    public function scopeWinners(Builder $query): Builder
    {
        return $query->where('roi_score', '>=', 60.00)->orderByDesc('roi_score');
    }

    /**
     * Recalcula a pontuação de ROI (0 a 100) com base no desempenho real
     */
    public function recalculateRoiScore(): void
    {
        $revenue = (float) $this->total_revenue_brl;
        $sales = (int) $this->total_sales_count;
        $clicks = (int) $this->total_clicks;
        $leads = (int) $this->total_leads;

        if ($revenue > 0 || $sales > 0) {
            // Peso de Receita: até 50 pontos (R$ 500 = 50 pts)
            $revenueScore = min(50.0, ($revenue / 500.0) * 50.0);

            // Peso de Volume de Vendas: até 30 pontos (5 vendas = 30 pts)
            $salesScore = min(30.0, $sales * 6.0);

            // Eficiência de Conversão: até 20 pontos
            if ($clicks > 0) {
                $cvr = $sales / max(1, $clicks);
                $efficiencyScore = min(20.0, $cvr * 400.0); // 5% de taxa de conversão = 20 pts
            } else {
                $efficiencyScore = 15.0; // Vendas registradas direto sem cliques prévios
            }

            $score = round($revenueScore + $salesScore + $efficiencyScore, 2);
        } else {
            // Sem vendas ainda: pontuação de tração de topo de funil (máx 25 pts)
            $trafficScore = min(15.0, $clicks * 0.5);
            $leadScore = min(10.0, $leads * 2.0);
            $score = round($trafficScore + $leadScore, 2);
        }

        $this->roi_score = min(100.00, max(0.00, $score));
        $this->saveQuietly();
    }

    /**
     * Cria a nova versão deste asset (revisão pedida pelo usuário) e marca a atual como substituída.
     */
    public function createRevision(array $attributes): self
    {
        $this->forceFill(['status' => 'superseded', 'is_selected' => false])->save();

        return static::create(array_merge(
            $this->only([
                'business_id', 'tiktok_product_id', 'approval_queue_id', 'type', 'platform', 'title',
                'funnel_stage', 'angle_category',
            ]),
            $attributes,
            [
                'parent_id' => $this->id,
                'version' => $this->version + 1,
                'status' => 'pending_approval',
            ]
        ));
    }
}
