<?php

namespace App\Services\Playbooks\Contracts;

interface BusinessPlaybookInterface
{
    public function getArchetypeName(): string;

    public function getDisplayName(): string;

    public function getRecommendedNorthStarMetric(): string;

    public function getFunnelStages(): array;

    public function getAngles(): array;

    public function getSystemPromptExtension(): string;

    public function getOptimizationGuidance(array $metrics): string;
}

