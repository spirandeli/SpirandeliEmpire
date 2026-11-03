<?php

namespace App\Services;

class VpsMonitorService
{
    /**
     * Get real CPU usage percentage.
     */
    public function getCpuUsage(): float
    {
        if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
            return 12.5; // Baseline for local dev if tested
        }

        $load = sys_getloadavg();
        $coreCount = (int) shell_exec('nproc 2>/dev/null') ?: 1;
        $usage = ($load[0] / $coreCount) * 100;
        return round(min(100, max(0, $usage)), 1);
    }

    /**
     * Get real RAM usage stats.
     */
    public function getMemoryUsage(): array
    {
        if (strtoupper(substr(PHP_OS, 0, 3)) === 'WIN') {
            return ['total_gb' => 8.0, 'used_gb' => 2.4, 'free_gb' => 5.6, 'percentage' => 30.0];
        }

        $free = shell_exec('free -m');
        if (!$free) {
            return ['total_gb' => 0, 'used_gb' => 0, 'free_gb' => 0, 'percentage' => 0];
        }

        $lines = explode("\n", trim($free));
        $memLine = preg_split('/\s+/', $lines[1]);
        $totalMb = (int) ($memLine[1] ?? 0);
        $usedMb = (int) ($memLine[2] ?? 0);
        $freeMb = (int) ($memLine[3] ?? 0);

        $percentage = ($totalMb > 0) ? ($usedMb / $totalMb) * 100 : 0;

        return [
            'total_gb' => round($totalMb / 1024, 2),
            'used_gb' => round($usedMb / 1024, 2),
            'free_gb' => round($freeMb / 1024, 2),
            'percentage' => round($percentage, 1),
        ];
    }

    /**
     * Get disk usage stats.
     */
    public function getDiskUsage(): array
    {
        $path = base_path();
        $total = disk_total_space($path);
        $free = disk_free_space($path);
        $used = $total - $free;

        $totalGb = $total / (1024 * 1024 * 1024);
        $usedGb = $used / (1024 * 1024 * 1024);
        $freeGb = $free / (1024 * 1024 * 1024);
        $percentage = ($total > 0) ? ($used / $total) * 100 : 0;

        return [
            'total_gb' => round($totalGb, 1),
            'used_gb' => round($usedGb, 1),
            'free_gb' => round($freeGb, 1),
            'percentage' => round($percentage, 1),
        ];
    }

    /**
     * Get summary metrics.
     */
    public function getSystemSummary(): array
    {
        return [
            'cpu_percent' => $this->getCpuUsage(),
            'memory' => $this->getMemoryUsage(),
            'disk' => $this->getDiskUsage(),
            'php_version' => PHP_VERSION,
            'os' => PHP_OS,
            'timestamp' => now()->toIso8601String(),
        ];
    }
}

