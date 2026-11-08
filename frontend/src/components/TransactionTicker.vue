<template>
  <div class="space-y-4">
    <!-- Controls and Filter Bar -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-md">
      <div class="flex flex-wrap items-center gap-3">
        <!-- Live Ticker Indicator -->
        <div class="flex items-center space-x-2">
          <span class="relative flex h-3 w-3">
            <span v-if="!isPaused" class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3 w-3" :class="isPaused ? 'bg-amber-400' : 'bg-emerald-500'"></span>
          </span>
          <span class="text-sm font-semibold font-mono text-slate-200">
            {{ isPaused ? 'FEED PAUSED' : 'LIVE STREAM FEED' }}
          </span>
        </div>

        <span class="text-slate-600">|</span>

        <!-- Filter buttons -->
        <div class="flex items-center space-x-1.5 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-medium">
          <button
            @click="filterMode = 'all'"
            :class="filterMode === 'all' ? 'bg-sky-500 text-white font-semibold' : 'text-slate-400 hover:text-white'"
            class="px-2.5 py-1 rounded transition-colors">
            All ({{ transactions.length }})
          </button>
          <button
            @click="filterMode = 'fraud_only'"
            :class="filterMode === 'fraud_only' ? 'bg-rose-600 text-white font-semibold' : 'text-slate-400 hover:text-rose-400'"
            class="px-2.5 py-1 rounded transition-colors flex items-center gap-1">
            <span>Critical & High</span>
            <span class="px-1.5 py-0.2 bg-rose-950/80 border border-rose-700/60 rounded text-[10px]">{{ fraudCount }}</span>
          </button>
          <button
            @click="filterMode = 'transfer_cashout'"
            :class="filterMode === 'transfer_cashout' ? 'bg-indigo-600 text-white font-semibold' : 'text-slate-400 hover:text-indigo-400'"
            class="px-2.5 py-1 rounded transition-colors">
            Transfers / Cash Out
          </button>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex items-center space-x-2">
        <button
          @click="togglePause"
          class="px-3 py-1.5 rounded-lg border text-xs font-mono font-medium flex items-center gap-1.5 transition-colors"
          :class="isPaused ? 'border-emerald-700 bg-emerald-950/40 text-emerald-300 hover:bg-emerald-900/50' : 'border-amber-700 bg-amber-950/40 text-amber-300 hover:bg-amber-900/50'">
          <svg v-if="!isPaused" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <svg v-else class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{{ isPaused ? 'Resume Ticker' : 'Pause Ticker' }}</span>
        </button>

        <button
          @click="clearTransactions"
          class="px-3 py-1.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:text-white text-xs font-mono font-medium transition-colors">
          Clear
        </button>
      </div>
    </div>

    <!-- Live Transactions Table -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl overflow-hidden shadow-xl">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs font-sans">
          <thead class="bg-slate-950/80 text-slate-400 uppercase font-mono tracking-wider border-b border-slate-800">
            <tr>
              <th scope="col" class="py-3 px-4">Time</th>
              <th scope="col" class="py-3 px-3">Type</th>
              <th scope="col" class="py-3 px-4">Sender (Orig)</th>
              <th scope="col" class="py-3 px-4">Receiver (Dest)</th>
              <th scope="col" class="py-3 px-4 text-right">Amount</th>
              <th scope="col" class="py-3 px-3 text-center">XGBoost Score</th>
              <th scope="col" class="py-3 px-3 text-center">GNN Ring</th>
              <th scope="col" class="py-3 px-4 text-center">Blended Risk</th>
              <th scope="col" class="py-3 px-3 text-center">Decision</th>
              <th scope="col" class="py-3 px-3 text-center">Inspect</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-800/60 font-mono">
            <tr
              v-for="tx in filteredTransactions"
              :key="tx.transaction_id || tx.tx_id || (tx.timestamp + tx.nameOrig)"
              class="transition-colors hover:bg-slate-800/40"
              :class="{
                'bg-rose-950/20 hover:bg-rose-950/30': tx.is_fraud || tx.decision === 'BLOCK' || (tx.final_score >= 0.5),
                'bg-slate-900/50': !tx.is_fraud && tx.final_score < 0.5
              }">
              
              <!-- Time -->
              <td class="py-3 px-4 whitespace-nowrap text-slate-400">
                {{ formatTime(tx.timestamp) }}
              </td>

              <!-- Type Badge -->
              <td class="py-3 px-3 whitespace-nowrap">
                <span
                  class="px-2 py-0.5 rounded text-[11px] font-semibold tracking-wide"
                  :class="getTypeBadgeClass(tx.type)">
                  {{ tx.type }}
                </span>
              </td>

              <!-- Sender Account -->
              <td class="py-3 px-4 whitespace-nowrap font-medium text-slate-300">
                <div class="flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full" :class="tx.is_fraud ? 'bg-rose-500' : 'bg-slate-600'"></span>
                  <span>{{ tx.nameOrig }}</span>
                </div>
              </td>

              <!-- Receiver Account -->
              <td class="py-3 px-4 whitespace-nowrap font-medium text-slate-300">
                <div class="flex items-center gap-1.5">
                  <span class="w-2 h-2 rounded-full" :class="tx.is_fraud ? 'bg-rose-500' : 'bg-slate-600'"></span>
                  <span>{{ tx.nameDest }}</span>
                </div>
              </td>

              <!-- Amount -->
              <td class="py-3 px-4 whitespace-nowrap text-right font-bold"
                :class="tx.amount > 100000 ? 'text-amber-300' : 'text-slate-200'">
                ${{ Number(tx.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
              </td>

              <!-- XGBoost Score -->
              <td class="py-3 px-3 whitespace-nowrap text-center">
                <div class="flex items-center justify-center gap-1.5">
                  <div class="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div class="h-full rounded-full"
                      :class="getScoreBarColor(tx.p_xgb || 0)"
                      :style="{ width: `${Math.min(100, (tx.p_xgb || 0) * 100)}%` }"></div>
                  </div>
                  <span class="text-xs" :class="getScoreTextColor(tx.p_xgb || 0)">
                    {{ ((tx.p_xgb || 0) * 100).toFixed(1) }}%
                  </span>
                </div>
              </td>

              <!-- GNN Ring Score -->
              <td class="py-3 px-3 whitespace-nowrap text-center">
                <div class="flex items-center justify-center gap-1.5">
                  <div class="w-12 bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div class="h-full rounded-full"
                      :class="getScoreBarColor(tx.p_gnn || 0)"
                      :style="{ width: `${Math.min(100, (tx.p_gnn || 0) * 100)}%` }"></div>
                  </div>
                  <span class="text-xs" :class="getScoreTextColor(tx.p_gnn || 0)">
                    {{ ((tx.p_gnn || 0) * 100).toFixed(1) }}%
                  </span>
                </div>
              </td>

              <!-- Blended Risk Score -->
              <td class="py-3 px-4 whitespace-nowrap text-center">
                <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold"
                  :class="getRiskBadgeClass(tx.final_score)">
                  {{ ((tx.final_score || 0) * 100).toFixed(1) }}%
                </span>
              </td>

              <!-- Decision Badge -->
              <td class="py-3 px-3 whitespace-nowrap text-center">
                <span v-if="tx.decision === 'BLOCK' || tx.is_fraud || tx.final_score >= 0.5"
                  class="px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/40 text-[11px] font-bold tracking-wider inline-flex items-center gap-1 shadow-sm shadow-rose-950">
                  <span class="w-1.5 h-1.5 rounded-full bg-rose-400 animate-pulse"></span>
                  BLOCK
                </span>
                <span v-else-if="tx.final_score >= 0.25"
                  class="px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[11px] font-bold tracking-wider inline-flex items-center gap-1">
                  REVIEW
                </span>
                <span v-else
                  class="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] font-semibold tracking-wider inline-flex items-center gap-1">
                  APPROVE
                </span>
              </td>

              <!-- Inspect Button -->
              <td class="py-3 px-3 whitespace-nowrap text-center">
                <button
                  @click="openDetails(tx)"
                  class="text-sky-400 hover:text-sky-300 hover:bg-sky-950/60 p-1.5 rounded-lg transition-colors"
                  title="Inspect Features & Raw PaySim Record">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                </button>
              </td>
            </tr>

            <!-- Empty State -->
            <tr v-if="filteredTransactions.length === 0">
              <td colspan="10" class="py-12 text-center text-slate-500 font-sans">
                <div class="flex flex-col items-center justify-center space-y-2">
                  <svg class="w-10 h-10 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                  </svg>
                  <p class="text-sm font-medium">Awaiting live transactions from producer or test replay...</p>
                  <p class="text-xs text-slate-600">Run producer with <code class="text-sky-400">python -m services.producer.producer --limit 50</code></p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Transaction Detail Modal -->
    <div v-if="selectedTx" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div class="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl relative font-sans">
        <button
          @click="selectedTx = null"
          class="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div class="flex items-center space-x-3 border-b border-slate-800 pb-4">
          <span class="w-3 h-3 rounded-full" :class="selectedTx.final_score >= 0.5 ? 'bg-rose-500' : 'bg-emerald-500'"></span>
          <h3 class="text-lg font-bold text-white">Transaction Diagnostic Report</h3>
          <span class="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">ID: {{ selectedTx.transaction_id || 'TX-LIVE' }}</span>
        </div>

        <div class="grid grid-cols-2 gap-4 my-4 font-mono text-xs">
          <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1.5">
            <p class="text-slate-400 font-sans font-semibold">Origin Account Details</p>
            <p><span class="text-slate-500">Account ID:</span> <span class="text-white">{{ selectedTx.nameOrig }}</span></p>
            <p><span class="text-slate-500">Old Balance:</span> <span class="text-white">${{ (selectedTx.oldbalanceOrg || 0).toLocaleString() }}</span></p>
            <p><span class="text-slate-500">New Balance:</span> <span class="text-white">${{ (selectedTx.newbalanceOrig || 0).toLocaleString() }}</span></p>
            <p><span class="text-slate-500">Drain Ratio:</span> <span :class="(selectedTx.orig_drain_ratio || 0) > 0.9 ? 'text-rose-400 font-bold' : 'text-slate-300'">{{ ((selectedTx.orig_drain_ratio || 0) * 100).toFixed(1) }}%</span></p>
          </div>

          <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 space-y-1.5">
            <p class="text-slate-400 font-sans font-semibold">Destination Account Details</p>
            <p><span class="text-slate-500">Account ID:</span> <span class="text-white">{{ selectedTx.nameDest }}</span></p>
            <p><span class="text-slate-500">Old Balance:</span> <span class="text-white">${{ (selectedTx.oldbalanceDest || 0).toLocaleString() }}</span></p>
            <p><span class="text-slate-500">New Balance:</span> <span class="text-white">${{ (selectedTx.newbalanceDest || 0).toLocaleString() }}</span></p>
            <p><span class="text-slate-500">Amount:</span> <span class="text-amber-400 font-bold">${{ Number(selectedTx.amount || 0).toLocaleString() }}</span></p>
          </div>
        </div>

        <!-- Feast Feature Store Balance Discrepancy View -->
        <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 mb-4 font-mono text-xs">
          <p class="text-slate-300 font-sans font-semibold mb-2 flex items-center justify-between">
            <span>Feast Feature Store Discrepancy Indicators</span>
            <span class="text-[11px] text-sky-400">Sub-millisecond Feast Online Lookup</span>
          </p>
          <div class="grid grid-cols-3 gap-2 text-center">
            <div class="bg-slate-900 p-2 rounded-lg border border-slate-800">
              <span class="text-slate-400 block text-[10px]">Orig Balance Error</span>
              <span class="font-bold text-sm" :class="Math.abs(selectedTx.error_balance_orig || 0) > 10 ? 'text-rose-400' : 'text-emerald-400'">
                ${{ (selectedTx.error_balance_orig || 0).toLocaleString() }}
              </span>
            </div>
            <div class="bg-slate-900 p-2 rounded-lg border border-slate-800">
              <span class="text-slate-400 block text-[10px]">Dest Balance Error</span>
              <span class="font-bold text-sm" :class="Math.abs(selectedTx.error_balance_dest || 0) > 10 ? 'text-rose-400' : 'text-emerald-400'">
                ${{ (selectedTx.error_balance_dest || 0).toLocaleString() }}
              </span>
            </div>
            <div class="bg-slate-900 p-2 rounded-lg border border-slate-800">
              <span class="text-slate-400 block text-[10px]">Scoring Latency</span>
              <span class="font-bold text-sm text-sky-400">
                {{ selectedTx.latency_ms ? `${selectedTx.latency_ms.toFixed(2)} ms` : '< 3.5 ms' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Risk Breakdown -->
        <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2 font-mono text-xs">
          <p class="text-slate-300 font-sans font-semibold">Model Ensemble Weighting</p>
          <div class="flex items-center justify-between">
            <span class="text-slate-400">XGBoost Feature Tree (65% Weight):</span>
            <span class="text-white font-bold">{{ ((selectedTx.p_xgb || 0) * 100).toFixed(2) }}%</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-slate-400">PyG GraphSAGE Ring Topology (35% Weight):</span>
            <span class="text-white font-bold">{{ ((selectedTx.p_gnn || 0) * 100).toFixed(2) }}%</span>
          </div>
          <div class="flex items-center justify-between border-t border-slate-800 pt-2 text-sm">
            <span class="text-slate-200 font-bold">Blended Risk Score:</span>
            <span class="font-extrabold text-base" :class="getScoreTextColor(selectedTx.final_score)">
              {{ ((selectedTx.final_score || 0) * 100).toFixed(2) }}%
            </span>
          </div>
        </div>

        <div class="mt-6 flex justify-end">
          <button
            @click="selectedTx = null"
            class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold">
            Close Diagnostic
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  transactions: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['clear', 'toggle-pause'])

const filterMode = ref('all')
const isPaused = ref(false)
const selectedTx = ref(null)

const togglePause = () => {
  isPaused.value = !isPaused.value
  emit('toggle-pause', isPaused.value)
}

const clearTransactions = () => {
  emit('clear')
}

const openDetails = (tx) => {
  selectedTx.value = tx
}

const fraudCount = computed(() => {
  return props.transactions.filter(t => t.is_fraud || t.final_score >= 0.5 || t.tier === 'CRITICAL' || t.tier === 'HIGH').length
})

const filteredTransactions = computed(() => {
  if (filterMode.value === 'fraud_only') {
    return props.transactions.filter(t => t.is_fraud || t.final_score >= 0.5 || t.tier === 'CRITICAL' || t.tier === 'HIGH')
  } else if (filterMode.value === 'transfer_cashout') {
    return props.transactions.filter(t => t.type === 'TRANSFER' || t.type === 'CASH_OUT')
  }
  return props.transactions
})

const formatTime = (ts) => {
  if (!ts) return new Date().toLocaleTimeString()
  try {
    const d = new Date(ts)
    return isNaN(d.getTime()) ? String(ts) : d.toLocaleTimeString()
  } catch {
    return String(ts)
  }
}

const getTypeBadgeClass = (type) => {
  switch (type) {
    case 'TRANSFER':
      return 'bg-purple-900/60 border border-purple-700/60 text-purple-300'
    case 'CASH_OUT':
      return 'bg-rose-900/60 border border-rose-700/60 text-rose-300'
    case 'PAYMENT':
      return 'bg-sky-900/60 border border-sky-700/60 text-sky-300'
    case 'CASH_IN':
      return 'bg-emerald-900/60 border border-emerald-700/60 text-emerald-300'
    case 'DEBIT':
      return 'bg-amber-900/60 border border-amber-700/60 text-amber-300'
    default:
      return 'bg-slate-800 text-slate-300'
  }
}

const getScoreBarColor = (score) => {
  if (score >= 0.7) return 'bg-rose-500'
  if (score >= 0.4) return 'bg-amber-400'
  return 'bg-emerald-500'
}

const getScoreTextColor = (score) => {
  if (score >= 0.7) return 'text-rose-400 font-bold'
  if (score >= 0.4) return 'text-amber-400 font-medium'
  return 'text-emerald-400'
}

const getRiskBadgeClass = (score) => {
  const s = score || 0
  if (s >= 0.7) return 'bg-rose-950/80 border border-rose-800 text-rose-300'
  if (s >= 0.4) return 'bg-amber-950/80 border border-amber-800 text-amber-300'
  return 'bg-emerald-950/80 border border-emerald-800 text-emerald-300'
}
</script>

