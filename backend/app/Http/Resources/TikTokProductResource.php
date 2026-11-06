<?php

namespace App\Http\Resources;

use Illuminate\Http\Request;
use Illuminate\Http\Resources\Json\JsonResource;

/** @mixin \App\Models\TikTokProduct */
class TikTokProductResource extends JsonResource
{
    public function toArray(Request $request): array
    {
        return [
            'id' => $this->id,
            'business_id' => $this->business_id,
            'external_id' => $this->external_id,
            'title' => $this->title,
            'category' => $this->category,
            'shop_name' => $this->shop_name,
            'image_url' => $this->image_url,
            'product_url' => $this->product_url,
            'affiliate_link' => $this->affiliate_link,
            'price' => (float) $this->price,
            'currency' => $this->currency,
            'commission_rate' => (float) $this->commission_rate,
            'commission_value' => (float) $this->commission_value,
            'sales_count' => $this->sales_count,
            'sales_velocity' => (float) $this->sales_velocity,
            'rating' => (float) $this->rating,
            'reviews_count' => $this->reviews_count,
            'margin_score' => $this->margin_score,
            'velocity_score' => $this->velocity_score,
            'viral_score' => $this->viral_score,
            'overall_score' => $this->overall_score,
            'status' => $this->status,
            'ai_analysis' => $this->ai_analysis,
            'mined_at' => $this->mined_at?->toIso8601String(),
            'selected_at' => $this->selected_at?->toIso8601String(),
            'created_at' => $this->created_at?->toIso8601String(),
        ];
    }
}

