<template>
  <div class="space-y-6 max-w-7xl mx-auto">
    <div class="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h2 class="text-xl font-bold text-slate-100">Administração & Monitoramento da VPS</h2>
        <p class="text-xs text-slate-400 mt-1">
          Observabilidade total sem expor terminal aberto na internet (Princípio de Segurança 14.2)
        </p>
      </div>
      <a
        href="/kuma"
        target="_blank"
        class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-cyan-400 border border-slate-700 rounded-xl text-xs font-mono transition flex items-center space-x-2"
      >
        <span>Abrir Uptime Kuma ↗</span>
      </a>
    </div>

    <!-- Live Telemetry -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-mono text-slate-400 uppercase">Processador (CPU)</span>
          <span class="text-xs font-mono text-emerald-400 font-bold">8.2%</span>
        </div>
        <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
          <div class="bg-emerald-500 h-2 rounded-full" style="width: 8.2%"></div>
        </div>
        <span class="text-[10px] text-slate-500 mt-2 block font-mono">Carga normal em repouso</span>
      </div>

      <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-mono text-slate-400 uppercase">Memória RAM</span>
          <span class="text-xs font-mono text-cyan-400 font-bold">2.4 GB / 8.0 GB (30%)</span>
        </div>
        <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
          <div class="bg-cyan-500 h-2 rounded-full" style="width: 30%"></div>
        </div>
        <span class="text-[10px] text-slate-500 mt-2 block font-mono">Otimizado para VPS econômica</span>
      </div>

      <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
        <div class="flex items-center justify-between mb-2">
          <span class="text-xs font-mono text-slate-400 uppercase">Armazenamento (SSD)</span>
          <span class="text-xs font-mono text-amber-400 font-bold">14.2 GB / 100 GB (14%)</span>
        </div>
        <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
          <div class="bg-amber-500 h-2 rounded-full" style="width: 14%"></div>
        </div>
        <span class="text-[10px] text-slate-500 mt-2 block font-mono">Volumes persistentes saudáveis</span>
      </div>
    </div>

    <!-- Container Grid -->
    <div class="bg-slate-900/80 p-6 rounded-2xl border border-slate-800">
      <h3 class="text-sm font-bold text-slate-200 uppercase font-mono mb-4">
        Containers Docker em Execução
      </h3>
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 font-mono text-xs">
        <div v-for="c in containers" :key="c.name" class="p-3 bg-slate-950/60 rounded-xl border border-slate-800 flex items-center justify-between">
          <div>
            <div class="font-bold text-slate-200">{{ c.name }}</div>
            <div class="text-[10px] text-slate-500">{{ c.image }}</div>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-800 uppercase">
            {{ c.status }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const containers = [
  { name: 'empire_caddy', image: 'caddy:2-alpine', status: 'Running' },
  { name: 'empire_backend', image: 'php:8.3-fpm-alpine', status: 'Running' },
  { name: 'empire_worker', image: 'php:8.3-fpm-alpine', status: 'Running' },
  { name: 'empire_jeffrey_worker', image: 'python:3.11-slim', status: 'Running' },
  { name: 'empire_postgres', image: 'postgres:16-alpine', status: 'Healthy' },
  { name: 'empire_redis', image: 'redis:7-alpine', status: 'Healthy' },
  { name: 'empire_ollama', image: 'ollama/ollama:latest', status: 'Running' },
  { name: 'empire_monitoring', image: 'louislam/uptime-kuma:1-alpine', status: 'Running' },
]
</script>

