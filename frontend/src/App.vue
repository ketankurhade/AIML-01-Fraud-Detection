<template>
  <div class="min-h-screen bg-[#080d1a] text-slate-100 flex flex-col selection:bg-sky-500 selection:text-white">
    <!-- Top Header and KPI Bar -->
    <KpiBar
      :connection-status="connectionStatus"
      :stats="stats"
      :ring-count="ringsData.rings ? ringsData.rings.length : 3" />

    <!-- Navigation Tabs & Toolbar -->
    <div class="bg-[#0b1329] border-b border-slate-800/80 px-6 sticky top-0 z-40 backdrop-blur-md bg-opacity-90">
      <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
        <nav class="flex space-x-1 py-2 font-mono text-xs">
          <!-- Tab 1: Live Ticker -->
          <button
            @click="activeTab = 'ticker'"
            :class="activeTab === 'ticker' ? 'bg-sky-500/15 text-sky-400 border-sky-500 font-bold' : 'text-slate-400 hover:text-slate-200 border-transparent'"
            class="px-4 py-2 rounded-lg border-b-2 flex items-center gap-2 transition-all">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-sky-500"></span>
            </span>
            <span>Live Transactions</span>
            <span class="px-1.5 py-0.2 rounded bg-slate-800 text-[10px] text-slate-300 font-normal">{{ transactions.length }}</span>
          </button>

          <!-- Tab 2: Analyst Triage -->
          <button
            @click="activeTab = 'triage'"
            :class="activeTab === 'triage' ? 'bg-rose-500/15 text-rose-400 border-rose-500 font-bold' : 'text-slate-400 hover:text-slate-200 border-transparent'"
            class="px-4 py-2 rounded-lg border-b-2 flex items-center gap-2 transition-all">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>Analyst Triage</span>
            <span v-if="pendingAlertsCount > 0" class="px-1.5 py-0.2 rounded bg-rose-950 border border-rose-800 text-[10px] text-rose-300 font-bold">
              {{ pendingAlertsCount }}
            </span>
          </button>

          <!-- Tab 3: Fraud Rings -->
          <button
            @click="activeTab = 'rings'"
            :class="activeTab === 'rings' ? 'bg-indigo-500/15 text-indigo-400 border-indigo-500 font-bold' : 'text-slate-400 hover:text-slate-200 border-transparent'"
            class="px-4 py-2 rounded-lg border-b-2 flex items-center gap-2 transition-all">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            <span>Ring Network Explorer</span>
            <span class="px-1.5 py-0.2 rounded bg-indigo-950 border border-indigo-800 text-[10px] text-indigo-300">PyG GNN</span>
          </button>

          <!-- Tab 4: Drift Observability -->
          <button
            @click="activeTab = 'drift'"
            :class="activeTab === 'drift' ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500 font-bold' : 'text-slate-400 hover:text-slate-200 border-transparent'"
            class="px-4 py-2 rounded-lg border-b-2 flex items-center gap-2 transition-all">
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <span>Model Drift (Evidently)</span>
          </button>
        </nav>

        <!-- Live Simulation Quick Trigger -->
        <div class="flex items-center space-x-2 py-2">
          <button
            @click="triggerSampleBatch"
            :disabled="isSimulating"
            class="px-3 py-1.5 bg-gradient-to-r from-sky-600 to-indigo-600 hover:from-sky-500 hover:to-indigo-500 text-white rounded-lg text-xs font-mono font-medium flex items-center gap-1.5 transition-all shadow-md shadow-sky-950">
            <svg class="w-3.5 h-3.5" :class="{ 'animate-spin': isSimulating }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>{{ isSimulating ? 'Scoring...' : 'Simulate 5 Live Tx' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- Main Content Body -->
    <main class="max-w-7xl mx-auto w-full px-6 py-6 flex-1">
      <!-- Tab 1: Live Transactions -->
      <TransactionTicker
        v-if="activeTab === 'ticker'"
        :transactions="transactions"
        @clear="clearTransactions"
        @toggle-pause="handleTogglePause" />

      <!-- Tab 2: Analyst Triage -->
      <CaseTriage
        v-if="activeTab === 'triage'"
        :alerts="alerts"
        @refresh="fetchAlerts"
        @action-performed="handleAlertAction" />

      <!-- Tab 3: Fraud Ring Network Explorer -->
      <FraudRingGraph
        v-if="activeTab === 'rings'"
        :rings-data="ringsData" />

      <!-- Tab 4: Evidently AI Drift Monitoring -->
      <DriftDashboard
        v-if="activeTab === 'drift'"
        :drift-data="driftData" />
    </main>

    <!-- Footer -->
    <footer class="bg-[#090e1c] border-t border-slate-800/60 py-4 px-6 text-center text-xs font-mono text-slate-500">
      <div class="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
        <div>
          <span>FraudShield AI Enterprise</span> &bull; 
          <span class="text-slate-400">Production Inference Engine & Ring Graph Miner</span>
        </div>
        <div class="flex items-center space-x-3 text-slate-400">
          <span>Feast Feature Store</span>
          <span>&bull;</span>
          <span>XGBoost</span>
          <span>&bull;</span>
          <span>PyTorch Geometric</span>
          <span>&bull;</span>
          <span>Evidently AI</span>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import KpiBar from './components/KpiBar.vue'
import TransactionTicker from './components/TransactionTicker.vue'
import CaseTriage from './components/CaseTriage.vue'
import FraudRingGraph from './components/FraudRingGraph.vue'
import DriftDashboard from './components/DriftDashboard.vue'

const activeTab = ref('ticker')
const connectionStatus = ref('disconnected') // 'connected' | 'polling' | 'disconnected'
const isPaused = ref(false)
const isSimulating = ref(false)

const stats = ref({
  total_scored: 0,
  total_flagged: 0,
  blocked_amount: 0,
  avg_latency_ms: 3.12
})

const transactions = ref([])
const alerts = ref([])
const ringsData = ref({ nodes: [], edges: [], rings: [] })
const driftData = ref({
  dataset_drift: false,
  drift_share: 0.0,
  number_of_columns: 8,
  number_of_drifted_features: 0,
  drift_by_feature: {}
})

let ws = null
let pollInterval = null
let reconnectTimeout = null

const pendingAlertsCount = computed(() => {
  return alerts.value.filter(a => a.status === 'PENDING').length
})

const clearTransactions = () => {
  transactions.value = []
}

const handleTogglePause = (paused) => {
  isPaused.value = paused
}

const handleAlertAction = ({ alertId, action, notes }) => {
  const target = alerts.value.find(a => a.alert_id === alertId)
  if (target) {
    target.status = action === 'APPROVE' ? 'APPROVED' : (action === 'CONFIRM_FRAUD' ? 'CONFIRMED_FRAUD' : 'FLAGGED_KYC')
    target.analyst_notes = notes
  }
}

// WebSocket Connection
const initWebSocket = () => {
  try {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host || 'localhost:8000'
    const wsUrl = `${protocol}//${host}/ws/transactions`

    ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log('Connected to FraudShield WebSocket live feed')
      connectionStatus.value = 'connected'
      if (pollInterval) {
        clearInterval(pollInterval)
        pollInterval = null
      }
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'PING') return

        if (!isPaused.value) {
          transactions.value.unshift(data)
          if (transactions.value.length > 250) {
            transactions.value.pop()
          }
        }

        // Update real-time stats
        stats.value.total_scored += 1
        if (data.is_fraud || data.final_score >= 0.5) {
          stats.value.total_flagged += 1
          stats.value.blocked_amount += (data.amount || 0)

          // Add to alert triage queue
          alerts.value.unshift({
            alert_id: data.transaction_id || `ALT-${Date.now()}`,
            timestamp: data.timestamp || new Date().toISOString(),
            type: data.type,
            amount: data.amount,
            nameOrig: data.nameOrig,
            nameDest: data.nameDest,
            p_xgb: data.p_xgb,
            p_gnn: data.p_gnn,
            risk_score: data.final_score,
            risk_tier: data.final_score >= 0.8 ? 'CRITICAL' : 'HIGH',
            status: 'PENDING',
            error_balance_orig: data.error_balance_orig || 0,
            error_balance_dest: data.error_balance_dest || 0
          })
        }
      } catch (err) {
        console.error('Error parsing live WS payload:', err)
      }
    }

    ws.onerror = (err) => {
      console.warn('WebSocket connection error, switching to REST polling fallback:', err)
      connectionStatus.value = 'polling'
      startPolling()
    }

    ws.onclose = () => {
      connectionStatus.value = 'polling'
      startPolling()
      // Retry WebSocket reconnection after 5s
      reconnectTimeout = setTimeout(() => {
        initWebSocket()
      }, 5000)
    }
  } catch (err) {
    console.warn('Failed to initialize WebSocket, enabling polling:', err)
    connectionStatus.value = 'polling'
    startPolling()
  }
}

// REST Fallback Polling
const startPolling = () => {
  if (pollInterval) return
  pollInterval = setInterval(async () => {
    try {
      await fetchStats()
      await fetchAlerts()
    } catch {
      // Keep quiet during disconnection
    }
  }, 2000)
}

const fetchStats = async () => {
  try {
    const res = await axios.get('/api/v1/stats')
    if (res.data) {
      stats.value.total_scored = Math.max(stats.value.total_scored, res.data.total_scored || 0)
      stats.value.total_flagged = Math.max(stats.value.total_flagged, res.data.total_flagged || 0)
      stats.value.blocked_amount = Math.max(stats.value.blocked_amount, res.data.blocked_amount || 0)
      stats.value.avg_latency_ms = res.data.avg_latency_ms || 3.1
    }
  } catch (err) {
    // Graceful offline fallback
  }
}

const fetchAlerts = async () => {
  try {
    const res = await axios.get('/api/v1/alerts')
    if (res.data && Array.isArray(res.data)) {
      alerts.value = res.data
    }
  } catch (err) {
    // Initial mock alerts if API is not running
    if (alerts.value.length === 0) {
      alerts.value = [
        {
          alert_id: 'ALT-1001',
          timestamp: new Date().toISOString(),
          type: 'TRANSFER',
          amount: 450000.0,
          nameOrig: 'C1000000001',
          nameDest: 'C1000000002',
          p_xgb: 0.998,
          p_gnn: 0.942,
          risk_score: 0.978,
          risk_tier: 'CRITICAL',
          status: 'PENDING',
          error_balance_orig: -450000.0,
          error_balance_dest: 0.0
        },
        {
          alert_id: 'ALT-1002',
          timestamp: new Date().toISOString(),
          type: 'CASH_OUT',
          amount: 820000.0,
          nameOrig: 'C2000000001',
          nameDest: 'C2000000004',
          p_xgb: 0.995,
          p_gnn: 0.891,
          risk_score: 0.958,
          risk_tier: 'CRITICAL',
          status: 'PENDING',
          error_balance_orig: -820000.0,
          error_balance_dest: 0.0
        },
        {
          alert_id: 'ALT-1003',
          timestamp: new Date().toISOString(),
          type: 'TRANSFER',
          amount: 125000.0,
          nameOrig: 'C992817263',
          nameDest: 'C482710294',
          p_xgb: 0.74,
          p_gnn: 0.42,
          risk_score: 0.628,
          risk_tier: 'HIGH',
          status: 'PENDING',
          error_balance_orig: -125000.0,
          error_balance_dest: 0.0
        }
      ]
    }
  }
}

const fetchRings = async () => {
  try {
    const res = await axios.get('/api/v1/rings')
    if (res.data) {
      ringsData.value = res.data
    }
  } catch (err) {
    // Handled by default simulated rings in component
  }
}

const fetchDrift = async () => {
  try {
    const res = await axios.get('/api/v1/monitoring/drift')
    if (res.data) {
      driftData.value = res.data
    }
  } catch (err) {
    // Handled gracefully
  }
}

// Interactive Simulation Helper (scores 5 sample transactions)
const triggerSampleBatch = async () => {
  isSimulating.value = true
  const sampleBatch = [
    {
      step: 1,
      type: 'TRANSFER',
      amount: 450000.0,
      nameOrig: 'C1000000001',
      oldbalanceOrg: 450000.0,
      newbalanceOrig: 0.0,
      nameDest: 'C1000000002',
      oldbalanceDest: 0.0,
      newbalanceDest: 0.0,
      timestamp: new Date().toISOString()
    },
    {
      step: 1,
      type: 'PAYMENT',
      amount: 142.50,
      nameOrig: 'C827192837',
      oldbalanceOrg: 5200.0,
      newbalanceOrig: 5057.50,
      nameDest: 'M982716253',
      oldbalanceDest: 0.0,
      newbalanceDest: 0.0,
      timestamp: new Date().toISOString()
    },
    {
      step: 1,
      type: 'CASH_OUT',
      amount: 820000.0,
      nameOrig: 'C2000000001',
      oldbalanceOrg: 820000.0,
      newbalanceOrig: 0.0,
      nameDest: 'C2000000004',
      oldbalanceDest: 0.0,
      newbalanceDest: 0.0,
      timestamp: new Date().toISOString()
    },
    {
      step: 1,
      type: 'CASH_IN',
      amount: 3400.0,
      nameOrig: 'C451293847',
      oldbalanceOrg: 12000.0,
      newbalanceOrig: 15400.0,
      nameDest: 'C192837465',
      oldbalanceDest: 0.0,
      newbalanceDest: 0.0,
      timestamp: new Date().toISOString()
    },
    {
      step: 1,
      type: 'TRANSFER',
      amount: 590000.0,
      nameOrig: 'C3000000002',
      oldbalanceOrg: 590000.0,
      newbalanceOrig: 0.0,
      nameDest: 'C3000000003',
      oldbalanceDest: 0.0,
      newbalanceDest: 0.0,
      timestamp: new Date().toISOString()
    }
  ]

  for (const item of sampleBatch) {
    try {
      const res = await axios.post('/api/v1/score', item)
      const scoredTx = {
        ...item,
        ...res.data,
        is_fraud: res.data.decision === 'BLOCK' || res.data.final_score >= 0.5
      }
      transactions.value.unshift(scoredTx)
      stats.value.total_scored += 1
      if (scoredTx.is_fraud) {
        stats.value.total_flagged += 1
        stats.value.blocked_amount += item.amount
      }
    } catch {
      // Simulate client-side response if backend not currently running
      const isFraud = item.amount > 300000
      const simTx = {
        ...item,
        p_xgb: isFraud ? 0.99 : 0.02,
        p_gnn: isFraud ? 0.92 : 0.03,
        final_score: isFraud ? 0.965 : 0.024,
        decision: isFraud ? 'BLOCK' : 'APPROVE',
        tier: isFraud ? 'CRITICAL' : 'LOW',
        error_balance_orig: isFraud ? -item.amount : 0,
        error_balance_dest: 0,
        orig_drain_ratio: isFraud ? 1.0 : 0.03,
        latency_ms: 2.85,
        is_fraud: isFraud
      }
      transactions.value.unshift(simTx)
      stats.value.total_scored += 1
      if (isFraud) {
        stats.value.total_flagged += 1
        stats.value.blocked_amount += item.amount
      }
    }
    // slight delay
    await new Promise(r => setTimeout(r, 200))
  }
  isSimulating.value = false
}

onMounted(() => {
  fetchStats()
  fetchAlerts()
  fetchRings()
  fetchDrift()
  initWebSocket()
})

onUnmounted(() => {
  if (ws) ws.close()
  if (pollInterval) clearInterval(pollInterval)
  if (reconnectTimeout) clearTimeout(reconnectTimeout)
})
</script>

