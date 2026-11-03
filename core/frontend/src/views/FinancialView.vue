<template>
  <div class="space-y-6 max-w-7xl mx-auto">
    <div class="bg-slate-900/80 p-6 rounded-2xl border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h2 class="text-xl font-bold text-slate-100">Empire Financial & Analytics</h2>
        <p class="text-xs text-slate-400 mt-1">
          Governança financeira estrita: Teto operacional de R$ 200,00/mês
        </p>
      </div>

      <div class="px-4 py-2 bg-amber-500/10 border border-amber-500/40 rounded-xl text-amber-400 font-mono text-xs font-bold">
        Teto Mensal: R$ 200,00
      </div>
    </div>

    <!-- Financial Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
        <div class="text-xs font-mono text-slate-400 uppercase">Receita Bruta Confirmada</div>
        <div class="text-2xl font-bold text-emerald-400 mt-2">R$ 0,00</div>
        <div class="text-xs text-slate-500 mt-1 font-mono">Fontes verificadas apenas</div>
      </div>

      <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
        <div class="text-xs font-mono text-slate-400 uppercase">Despesas Totais do Mês</div>
        <div class="text-2xl font-bold text-red-400 mt-2">R$ 0,00</div>
        <div class="text-xs text-slate-500 mt-1 font-mono">Infraestrutura + Operações</div>
      </div>

      <div class="bg-slate-900/80 p-5 rounded-xl border border-slate-800">
        <div class="text-xs font-mono text-slate-400 uppercase">Saldo Restante do Orçamento</div>
        <div class="text-2xl font-bold text-amber-400 mt-2">R$ 200,00</div>
        <div class="text-xs text-slate-500 mt-1 font-mono">100% disponível</div>
      </div>
    </div>

    <!-- Ledger Table -->
    <div class="bg-slate-900/80 p-6 rounded-2xl border border-slate-800">
      <h3 class="text-sm font-bold text-slate-200 uppercase font-mono mb-4">
        Livro Razão de Lançamentos Financeiros
      </h3>
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs font-mono">
          <thead class="bg-slate-950/80 text-slate-400 border-b border-slate-800">
            <tr>
              <th class="p-3">Data</th>
              <th class="p-3">Negócio</th>
              <th class="p-3">Tipo</th>
              <th class="p-3">Descrição</th>
              <th class="p-3 text-right">Valor (BRL)</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60 text-slate-300">
            <tr>
              <td class="p-3">2026-11-01</td>
              <td class="p-3">Empire Core</td>
              <td class="p-3 text-cyan-400">Infraestrutura</td>
              <td class="p-3">Previsão VPS Linux Ubuntu 24.04</td>
              <td class="p-3 text-right text-red-400">- R$ 60,00</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

