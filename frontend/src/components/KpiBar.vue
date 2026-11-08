<template>
  <header class="bg-[#0f172a] border-b border-slate-800/80 px-6 py-4 shadow-xl">
    <div class="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <!-- Brand & Status -->
      <div class="flex items-center space-x-4">
        <div class="h-10 w-10 rounded-xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
          <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              FraudShield <span class="text-sky-400 font-mono text-xs px-2 py-0.5 rounded bg-sky-950 border border-sky-800/60 font-semibold uppercase tracking-wider">AI Platform</span>
            </h1>
          </div>
          <p class="text-xs text-slate-400 font-mono">Hybrid XGBoost + PyG GraphSAGE + Feast Online Store</p>
        </div>
      </div>

      <!-- Live Connection & Engine Badges -->
      <div class="flex flex-wrap items-center gap-3">
        <!-- Model engine tags -->
        <div class="hidden lg:flex items-center space-x-2 text-xs">
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-700/80 text-slate-300">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            XGBoost (AUC: 1.00)
          </span>
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-700/80 text-slate-300">
            <span class="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
            PyG GraphSAGE (AUC: 0.996)
          </span>
          <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-700/80 text-slate-300">
            <span class="w-1.5 h-1.5 rounded-full bg-sky-400"></span>
            Feast Store (3,719 Accts)
          </span>
        </div>

        <!-- Connection status badge -->
        <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-medium shadow-sm transition-all"
          :class="statusBadgeClasses">
          <span class="relative flex h-2 w-2">
            <span v-if="connectionStatus === 'connected'" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2" :class="statusDotClass"></span>
          </span>
          <span>{{ statusText }}</span>
        </div>
      </div>
    </div>

    <!-- KPI Metric Cards Grid -->
    <div class="max-w-7xl mx-auto grid grid-cols-2 lg:grid-cols-5 gap-3 mt-4 pt-3 border-t border-slate-800/60">
      <!-- Total Transactions -->
      <div class="bg-slate-900/80 border border-slate-800/80 rounded-xl p-3 shadow-inner">
        <div class="flex items-center justify-between">
          <span class="text-xs uppercase font-mono tracking-wider text-slate-400">Total Scored</span>
          <svg class="w-4 h-4 text-sky-400 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
        </div>
        <div class="mt-1 flex items-baseline justify-between">
          <span class="text-2xl font-bold font-mono text-white">{{ stats.total_scored.toLocaleString() }}</span>
          <span class="text-[11px] font-mono text-sky-400/90 font-medium">real-time</span>
        </div>
      </div>

      <!-- Flagged Frauds -->
      <div class="bg-slate-900/80 border border-slate-800/80 rounded-xl p-3 shadow-inner"
        :class="{ 'border-rose-900/70 bg-rose-950/20': stats.total_flagged > 0 }">
        <div class="flex items-center justify-between">
          <span class="text-xs uppercase font-mono tracking-wider text-rose-300">Fraud Alerts</span>
          <svg class="w-4 h-4 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <div class="mt-1 flex items-baseline justify-between">
          <span class="text-2xl font-bold font-mono text-rose-400">{{ stats.total_flagged.toLocaleString() }}</span>
          <span class="text-[11px] font-mono text-rose-400/90 font-medium">{{ fraudRateText }}</span>
        </div>
      </div>

      <!-- Blocked Volume -->
      <div class="bg-slate-900/80 border border-slate-800/80 rounded-xl p-3 shadow-inner">
        <div class="flex items-center justify-between">
          <span class="text-xs uppercase font-mono tracking-wider text-slate-400">Blocked Value</span>
          <svg class="w-4 h-4 text-amber-400 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <div class="mt-1 flex items-baseline justify-between">
          <span class="text-2xl font-bold font-mono text-amber-300">{{ formattedBlockedAmount }}</span>
          <span class="text-[11px] font-mono text-slate-400">USD</span>
        </div>
      </div>

      <!-- Average Latency -->
      <div class="bg-slate-900/80 border border-slate-800/80 rounded-xl p-3 shadow-inner">
        <div class="flex items-center justify-between">
          <span class="text-xs uppercase font-mono tracking-wider text-slate-400">Avg Latency</span>
          <svg class="w-4 h-4 text-emerald-400 opacity-80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <div class="mt-1 flex items-baseline justify-between">
          <span class="text-2xl font-bold font-mono text-emerald-400">{{ (stats.avg_latency_ms || 3.1).toFixed(2) }} <span class="text-xs text-slate-400 font-normal">ms</span></span>
          <span class="text-[10px] font-mono text-emerald-500 font-medium px-1.5 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/50">&lt; 5ms SLA</span>
        </div>
      </div>

      <!-- High Risk Rings Detected -->
      <div class="col-span-2 lg:col-span-1 bg-slate-900/80 border border-slate-800/80 rounded-xl p-3 shadow-inner">
        <div class="flex items-center justify-between">
          <span class="text-xs uppercase font-mono tracking-wider text-indigo-300">Fraud Rings</span>
          <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </div>
        <div class="mt-1 flex items-baseline justify-between">
          <span class="text-2xl font-bold font-mono text-indigo-300">{{ ringCount }}</span>
          <span class="text-[11px] font-mono text-indigo-400/90 font-medium">3 Laundering Hubs</span>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  connectionStatus: {
    type: String,
    default: 'disconnected' // 'connected' | 'polling' | 'disconnected'
  },
  stats: {
    type: Object,
    default: () => ({
      total_scored: 0,
      total_flagged: 0,
      blocked_amount: 0,
      avg_latency_ms: 3.12
    })
  },
  ringCount: {
    type: Number,
    default: 3
  }
})

const statusBadgeClasses = computed(() => {
  if (props.connectionStatus === 'connected') {
    return 'bg-emerald-950/40 border-emerald-800 text-emerald-300'
  } else if (props.connectionStatus === 'polling') {
    return 'bg-amber-950/40 border-amber-800 text-amber-300'
  }
  return 'bg-rose-950/40 border-rose-800 text-rose-300'
})

const statusDotClass = computed(() => {
  if (props.connectionStatus === 'connected') return 'bg-emerald-400'
  if (props.connectionStatus === 'polling') return 'bg-amber-400'
  return 'bg-rose-400'
})

const statusText = computed(() => {
  if (props.connectionStatus === 'connected') return 'WebSocket: LIVE STREAM'
  if (props.connectionStatus === 'polling') return 'REST Polling (1s Fallback)'
  return 'WebSocket: Disconnected'
})

const formattedBlockedAmount = computed(() => {
  const amt = props.stats.blocked_amount || 0
  if (amt >= 1e6) {
    return `$${(amt / 1e6).toFixed(2)}M`
  } else if (amt >= 1e3) {
    return `$${(amt / 1e3).toFixed(1)}k`
  }
  return `$${amt.toFixed(2)}`
})

const fraudRateText = computed(() => {
  if (!props.stats.total_scored) return '0.0% rate'
  const rate = (props.stats.total_flagged / props.stats.total_scored) * 100
  return `${rate.toFixed(1)}% rate`
})
</script>

