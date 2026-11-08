<template>
  <div class="space-y-4">
    <!-- Header & Filter Controls -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-md">
      <div class="flex items-center space-x-3">
        <div class="p-2 rounded-lg bg-rose-950/60 border border-rose-800/60 text-rose-400">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <div>
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            Fraud Analyst Investigation Triage
            <span class="px-2 py-0.5 rounded-full bg-slate-800 text-xs font-mono text-slate-300">{{ alerts.length }} Cases</span>
          </h2>
          <p class="text-xs text-slate-400">Review flagged transactions, inspect Feast feature telemetry, and execute compliance enforcement.</p>
        </div>
      </div>

      <!-- Filters -->
      <div class="flex flex-wrap items-center gap-2">
        <select
          v-model="statusFilter"
          class="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500 font-mono">
          <option value="ALL">All Statuses</option>
          <option value="PENDING">Pending Review</option>
          <option value="CONFIRMED_FRAUD">Confirmed Fraud</option>
          <option value="FLAGGED_KYC">Flagged KYC</option>
          <option value="APPROVED">Approved</option>
        </select>

        <select
          v-model="tierFilter"
          class="bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-sky-500 font-mono">
          <option value="ALL">All Risk Tiers</option>
          <option value="CRITICAL">Critical Risk (&ge; 80%)</option>
          <option value="HIGH">High Risk (50% - 80%)</option>
          <option value="MEDIUM">Medium Risk (25% - 50%)</option>
        </select>

        <button
          @click="fetchAlerts"
          class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-mono flex items-center gap-1.5 transition-colors">
          <svg class="w-3.5 h-3.5" :class="{ 'animate-spin': isRefreshing }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>
    </div>

    <!-- Alert Cards / Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      <div
        v-for="alert in filteredAlerts"
        :key="alert.alert_id"
        @click="openTriageModal(alert)"
        class="bg-slate-900/90 border rounded-xl p-4 shadow-lg cursor-pointer transition-all hover:border-sky-500/60 hover:-translate-y-0.5"
        :class="{
          'border-rose-800/80 bg-rose-950/10': alert.risk_tier === 'CRITICAL' && alert.status === 'PENDING',
          'border-amber-800/80 bg-amber-950/10': alert.risk_tier === 'HIGH' && alert.status === 'PENDING',
          'border-slate-800': alert.status !== 'PENDING'
        }">
        
        <!-- Card Header -->
        <div class="flex items-center justify-between border-b border-slate-800/70 pb-2.5">
          <span class="text-xs font-mono font-bold px-2 py-0.5 rounded"
            :class="getTierClass(alert.risk_tier)">
            {{ alert.risk_tier }}
          </span>

          <span class="text-xs font-mono px-2 py-0.5 rounded-full border"
            :class="getStatusBadgeClass(alert.status)">
            {{ alert.status }}
          </span>
        </div>

        <!-- Transaction Content -->
        <div class="mt-3 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-xs text-slate-400 font-mono">Amount</span>
            <span class="text-lg font-bold font-mono text-amber-300">
              ${{ Number(alert.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
            </span>
          </div>

          <div class="text-xs font-mono space-y-1 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
            <div class="flex justify-between">
              <span class="text-slate-500">Sender:</span>
              <span class="text-slate-200 font-medium">{{ alert.nameOrig }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Recipient:</span>
              <span class="text-slate-200 font-medium">{{ alert.nameDest }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-slate-500">Type:</span>
              <span class="text-indigo-400 font-semibold">{{ alert.type }}</span>
            </div>
          </div>

          <!-- Score Breakdown Bar -->
          <div class="pt-1">
            <div class="flex justify-between text-xs font-mono mb-1">
              <span class="text-slate-400">Blended Risk Score</span>
              <span class="font-bold" :class="getScoreTextColor(alert.risk_score)">
                {{ ((alert.risk_score || 0) * 100).toFixed(1) }}%
              </span>
            </div>
            <div class="w-full bg-slate-950 rounded-full h-2 overflow-hidden border border-slate-800">
              <div
                class="h-full rounded-full transition-all duration-500"
                :class="alert.risk_score >= 0.7 ? 'bg-rose-500' : 'bg-amber-400'"
                :style="{ width: `${Math.min(100, (alert.risk_score || 0) * 100)}%` }"></div>
            </div>
          </div>
        </div>

        <!-- Timestamp & Footer -->
        <div class="mt-4 pt-2.5 border-t border-slate-800 flex items-center justify-between text-[11px] font-mono text-slate-500">
          <span>Alert ID: {{ alert.alert_id }}</span>
          <span class="text-sky-400 hover:text-sky-300 font-medium flex items-center gap-1">
            Investigate
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </span>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="filteredAlerts.length === 0" class="bg-slate-900/80 border border-slate-800 rounded-xl p-12 text-center text-slate-500">
      <svg class="w-12 h-12 mx-auto text-slate-600 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <h3 class="text-base font-medium text-slate-300">No matching investigation cases</h3>
      <p class="text-xs text-slate-500 mt-1">All flagged high-risk alerts have been resolved or filtered out.</p>
    </div>

    <!-- Triage & Enforcement Action Modal -->
    <div v-if="activeAlert" class="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
      <div class="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl relative font-sans">
        <button
          @click="activeAlert = null"
          class="absolute top-4 right-4 text-slate-400 hover:text-white p-1 rounded-lg">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <div class="flex items-center space-x-3 border-b border-slate-800 pb-4">
          <div class="p-2 rounded-lg bg-rose-950/80 border border-rose-800 text-rose-400">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <div>
            <h3 class="text-lg font-bold text-white">Case Investigation Dossier</h3>
            <p class="text-xs font-mono text-slate-400">Alert Ref: {{ activeAlert.alert_id }} &bull; Current Status: <span class="text-white font-bold">{{ activeAlert.status }}</span></p>
          </div>
        </div>

        <!-- Risk & Signal Indicators -->
        <div class="grid grid-cols-2 gap-4 my-4 font-mono text-xs">
          <div class="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
            <h4 class="font-sans font-semibold text-slate-300">Transaction Profile</h4>
            <div class="space-y-1">
              <p><span class="text-slate-500">Sender Account:</span> <span class="text-white">{{ activeAlert.nameOrig }}</span></p>
              <p><span class="text-slate-500">Destination Account:</span> <span class="text-white">{{ activeAlert.nameDest }}</span></p>
              <p><span class="text-slate-500">Type:</span> <span class="text-indigo-400 font-bold">{{ activeAlert.type }}</span></p>
              <p><span class="text-slate-500">Amount:</span> <span class="text-amber-400 font-bold text-sm">${{ Number(activeAlert.amount || 0).toLocaleString() }}</span></p>
            </div>
          </div>

          <div class="bg-slate-950 p-3.5 rounded-xl border border-slate-800 space-y-2">
            <h4 class="font-sans font-semibold text-slate-300">Model Telemetry & Scoring</h4>
            <div class="space-y-1">
              <p><span class="text-slate-500">XGBoost Score:</span> <span class="text-white font-bold">{{ ((activeAlert.p_xgb || 0) * 100).toFixed(1) }}%</span></p>
              <p><span class="text-slate-500">PyG GNN Ring Score:</span> <span class="text-white font-bold">{{ ((activeAlert.p_gnn || 0) * 100).toFixed(1) }}%</span></p>
              <p><span class="text-slate-500">Blended Risk Score:</span> <span class="text-rose-400 font-bold text-sm">{{ ((activeAlert.risk_score || 0) * 100).toFixed(1) }}%</span></p>
              <p><span class="text-slate-500">Risk Assessment:</span> <span class="text-rose-400 font-bold">{{ activeAlert.risk_tier }}</span></p>
            </div>
          </div>
        </div>

        <!-- Feature Store Inconsistency Signals -->
        <div class="bg-slate-950 p-3.5 rounded-xl border border-slate-800 mb-4 font-mono text-xs space-y-2">
          <h4 class="font-sans font-semibold text-slate-300 flex items-center justify-between">
            <span>Feast Balance Integrity Signals</span>
            <span class="text-[11px] text-sky-400">Online SQLite Store</span>
          </h4>
          <div class="grid grid-cols-2 gap-3 text-slate-400">
            <div class="p-2 rounded bg-slate-900 border border-slate-800">
              <span class="block text-[10px] text-slate-500">Origin Balance Discrepancy</span>
              <span class="text-white font-bold text-xs">
                ${{ (activeAlert.error_balance_orig || 0).toLocaleString() }}
              </span>
            </div>
            <div class="p-2 rounded bg-slate-900 border border-slate-800">
              <span class="block text-[10px] text-slate-500">Destination Balance Discrepancy</span>
              <span class="text-white font-bold text-xs">
                ${{ (activeAlert.error_balance_dest || 0).toLocaleString() }}
              </span>
            </div>
          </div>
        </div>

        <!-- Analyst Action Note -->
        <div class="mb-4">
          <label class="block text-xs font-semibold text-slate-300 mb-1">Analyst Resolution Notes</label>
          <textarea
            v-model="analystNotes"
            rows="2"
            placeholder="Add compliance notes or justification for audit log..."
            class="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-sky-500 font-sans"></textarea>
        </div>

        <!-- Enforcement Buttons -->
        <div class="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800">
          <span class="text-xs text-slate-500 font-mono">Action immediately updates compliance audit trail</span>
          <div class="flex items-center space-x-2">
            <!-- Green Approve -->
            <button
              @click="handleAction('APPROVE')"
              :disabled="isSubmitting"
              class="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-md shadow-emerald-950">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
              </svg>
              Approve
            </button>

            <!-- Yellow Flag KYC -->
            <button
              @click="handleAction('FLAG_KYC')"
              :disabled="isSubmitting"
              class="px-3.5 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-md shadow-amber-950">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Flag KYC
            </button>

            <!-- Red Confirm Fraud -->
            <button
              @click="handleAction('CONFIRM_FRAUD')"
              :disabled="isSubmitting"
              class="px-3.5 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-md shadow-rose-950">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
              </svg>
              Confirm Fraud & Freeze
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const props = defineProps({
  alerts: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['refresh', 'action-performed'])

const statusFilter = ref('ALL')
const tierFilter = ref('ALL')
const isRefreshing = ref(false)
const activeAlert = ref(null)
const analystNotes = ref('')
const isSubmitting = ref(false)

const filteredAlerts = computed(() => {
  return props.alerts.filter(a => {
    const matchesStatus = statusFilter.value === 'ALL' || a.status === statusFilter.value
    const matchesTier = tierFilter.value === 'ALL' || a.risk_tier === tierFilter.value
    return matchesStatus && matchesTier
  })
})

const openTriageModal = (alert) => {
  activeAlert.value = alert
  analystNotes.value = alert.analyst_notes || ''
}

const fetchAlerts = () => {
  isRefreshing.value = true
  emit('refresh')
  setTimeout(() => {
    isRefreshing.value = false
  }, 600)
}

const handleAction = async (action) => {
  if (!activeAlert.value) return
  isSubmitting.value = true
  try {
    const alertId = activeAlert.value.alert_id
    // Call backend API
    await axios.post(`/api/v1/alerts/${alertId}/action`, {
      action: action,
      notes: analystNotes.value || `Analyst manual action: ${action}`,
      analyst_notes: analystNotes.value || `Analyst manual action: ${action}`
    })

    // Local state update
    activeAlert.value.status = action === 'APPROVE' ? 'APPROVED' : (action === 'CONFIRM_FRAUD' ? 'CONFIRMED_FRAUD' : 'FLAGGED_KYC')
    emit('action-performed', { alertId, action, notes: analystNotes.value })
    activeAlert.value = null
  } catch (err) {
    console.error('Failed to submit analyst action:', err)
    // Fallback local update if API is running in mock/offline mode
    activeAlert.value.status = action === 'APPROVE' ? 'APPROVED' : (action === 'CONFIRM_FRAUD' ? 'CONFIRMED_FRAUD' : 'FLAGGED_KYC')
    emit('action-performed', { alertId: activeAlert.value.alert_id, action, notes: analystNotes.value })
    activeAlert.value = null
  } finally {
    isSubmitting.value = false
  }
}

const getTierClass = (tier) => {
  switch (tier) {
    case 'CRITICAL':
      return 'bg-rose-950/90 text-rose-300 border border-rose-800'
    case 'HIGH':
      return 'bg-amber-950/90 text-amber-300 border border-amber-800'
    default:
      return 'bg-sky-950/90 text-sky-300 border border-sky-800'
  }
}

const getStatusBadgeClass = (status) => {
  switch (status) {
    case 'PENDING':
      return 'border-amber-700/60 bg-amber-950/40 text-amber-300'
    case 'CONFIRMED_FRAUD':
      return 'border-rose-700/60 bg-rose-950/40 text-rose-300 font-bold'
    case 'APPROVED':
      return 'border-emerald-700/60 bg-emerald-950/40 text-emerald-300'
    case 'FLAGGED_KYC':
      return 'border-purple-700/60 bg-purple-950/40 text-purple-300'
    default:
      return 'border-slate-700 bg-slate-800 text-slate-300'
  }
}

const getScoreTextColor = (score) => {
  if (score >= 0.7) return 'text-rose-400'
  if (score >= 0.4) return 'text-amber-400'
  return 'text-emerald-400'
}
</script>
