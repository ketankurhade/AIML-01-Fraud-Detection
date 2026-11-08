<template>
  <div class="space-y-4">
    <!-- Controls Header -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-wrap items-center justify-between gap-4 shadow-md">
      <div class="flex items-center space-x-3">
        <div class="p-2 rounded-lg bg-indigo-950/60 border border-indigo-800/60 text-indigo-400">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
          </svg>
        </div>
        <div>
          <h2 class="text-base font-bold text-white flex items-center gap-2">
            PyG Graph Neural Network &bull; Fraud Ring Topology
            <span class="px-2 py-0.5 rounded-full bg-indigo-950 border border-indigo-800 text-xs font-mono text-indigo-300">
              {{ ringsData.rings ? ringsData.rings.length : 3 }} Detected Laundering Hubs
            </span>
          </h2>
          <p class="text-xs text-slate-400">Sub-graph mining reveals cyclic money laundering circuits and mule distribution accounts.</p>
        </div>
      </div>

      <!-- Ring Selector & Zoom Buttons -->
      <div class="flex flex-wrap items-center gap-2">
        <div class="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-mono">
          <button
            @click="selectRing('all')"
            :class="selectedRingId === 'all' ? 'bg-indigo-600 text-white font-bold' : 'text-slate-400 hover:text-white'"
            class="px-2.5 py-1 rounded transition-colors">
            All Rings
          </button>
          <button
            v-for="(ring, idx) in ringsList"
            :key="ring.ring_id || idx"
            @click="selectRing(ring.ring_id)"
            :class="selectedRingId === ring.ring_id ? 'bg-rose-600 text-white font-bold' : 'text-slate-400 hover:text-white'"
            class="px-2.5 py-1 rounded transition-colors flex items-center gap-1">
            <span>Ring #{{ idx + 1 }}</span>
            <span class="text-[10px] opacity-75 font-normal">({{ ring.nodes ? ring.nodes.length : 3 }})</span>
          </button>
        </div>

        <div class="flex items-center space-x-1">
          <button
            @click="zoomIn"
            title="Zoom In"
            class="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </button>
          <button
            @click="zoomOut"
            title="Zoom Out"
            class="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 12H6" />
            </svg>
          </button>
          <button
            @click="resetZoom"
            title="Reset View"
            class="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 text-xs font-mono transition-colors">
            Reset
          </button>
        </div>
      </div>
    </div>

    <!-- Main Graph Canvas & Details Sidebar -->
    <div class="grid grid-cols-1 lg:grid-cols-4 gap-4">
      <!-- Interactive SVG Canvas (3 cols) -->
      <div class="lg:col-span-3 bg-slate-950 border border-slate-800 rounded-xl relative overflow-hidden h-[540px] shadow-2xl select-none">
        <!-- Legend Overlay -->
        <div class="absolute top-3 left-3 z-10 bg-slate-900/90 border border-slate-800 backdrop-blur-md rounded-lg p-2.5 text-[11px] font-mono text-slate-300 space-y-1.5 shadow-lg">
          <div class="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Topology Legend</div>
          <div class="flex items-center space-x-2">
            <span class="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-sm shadow-rose-500"></span>
            <span>Mule / Launderer Account (Ring Node)</span>
          </div>
          <div class="flex items-center space-x-2">
            <span class="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
            <span>High Volume Originator</span>
          </div>
          <div class="flex items-center space-x-2">
            <span class="w-2.5 h-2.5 rounded-full bg-sky-400"></span>
            <span>Connected Endpoint Account</span>
          </div>
          <div class="flex items-center space-x-2 pt-1 border-t border-slate-800">
            <span class="w-4 h-0.5 bg-rose-500"></span>
            <span>Cyclic Laundering Flow</span>
          </div>
        </div>

        <!-- SVG Graph Canvas -->
        <svg
          ref="svgRef"
          class="w-full h-full cursor-grab active:cursor-grabbing"
          @mousedown="startPan"
          @mousemove="onPan"
          @mouseup="endPan"
          @mouseleave="endPan"
          @wheel.prevent="onWheel">
          
          <defs>
            <!-- Marker Arrowhead Red -->
            <marker id="arrow-rose" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#f43f5e" />
            </marker>
            <!-- Marker Arrowhead Amber -->
            <marker id="arrow-amber" viewBox="0 0 10 10" refX="20" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#f59e0b" />
            </marker>
            <!-- Marker Arrowhead Sky -->
            <marker id="arrow-sky" viewBox="0 0 10 10" refX="18" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#38bdf8" />
            </marker>

            <!-- Radial Glow Filter -->
            <filter id="glow-rose" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          <!-- Transform Group -->
          <g :transform="`translate(${panX}, ${panY}) scale(${zoomLevel})`">
            <!-- Background Rings Area Highlights -->
            <g v-for="(cluster, cIdx) in ringClusters" :key="'cluster-' + cIdx">
              <circle
                :cx="cluster.cx"
                :cy="cluster.cy"
                :r="cluster.radius + 35"
                fill="none"
                stroke="rgba(244, 63, 94, 0.15)"
                stroke-dasharray="6,6"
                stroke-width="1.5" />
              <text
                :x="cluster.cx"
                :y="cluster.cy - cluster.radius - 40"
                text-anchor="middle"
                class="text-[11px] font-mono fill-rose-400/80 font-bold tracking-wider">
                {{ cluster.title }}
              </text>
            </g>

            <!-- Directed Edges -->
            <g class="edges">
              <path
                v-for="(edge, eIdx) in renderedEdges"
                :key="'edge-' + eIdx"
                :d="calculateEdgePath(edge)"
                :stroke="edge.isRingEdge ? '#f43f5e' : '#475569'"
                :stroke-width="edge.isRingEdge ? 2.5 : 1.5"
                :stroke-dasharray="edge.isRingEdge ? 'none' : '4,2'"
                :marker-end="edge.isRingEdge ? 'url(#arrow-rose)' : 'url(#arrow-sky)'"
                fill="none"
                class="transition-colors hover:stroke-amber-400 cursor-pointer"
                @click="selectEdge(edge)" />
            </g>

            <!-- Nodes -->
            <g class="nodes">
              <g
                v-for="node in renderedNodes"
                :key="node.id"
                :transform="`translate(${node.x}, ${node.y})`"
                class="cursor-pointer transition-transform hover:scale-110"
                @click.stop="selectNode(node)">
                
                <!-- Pulse ring for fraud nodes -->
                <circle
                  v-if="node.isFraud || node.risk_score >= 0.5"
                  r="18"
                  fill="none"
                  stroke="#f43f5e"
                  stroke-width="2"
                  class="animate-ping opacity-30" />

                <!-- Node Body -->
                <circle
                  :r="node.radius || 12"
                  :fill="getNodeColor(node)"
                  :stroke="node.id === (selectedNode && selectedNode.id) ? '#ffffff' : (node.isFraud ? '#fda4af' : '#1e293b')"
                  :stroke-width="node.id === (selectedNode && selectedNode.id) ? 3 : 1.5"
                  :filter="node.isFraud ? 'url(#glow-rose)' : 'none'" />

                <!-- Node Label -->
                <text
                  y="22"
                  text-anchor="middle"
                  class="text-[10px] font-mono font-medium fill-slate-300 pointer-events-none select-none">
                  {{ truncateId(node.id) }}
                </text>
              </g>
            </g>
          </g>
        </svg>

        <!-- Canvas controls help overlay -->
        <div class="absolute bottom-3 right-3 text-[10px] font-mono text-slate-500 bg-slate-900/80 px-2 py-1 rounded border border-slate-800">
          Scroll to zoom &bull; Drag to pan &bull; Click node to inspect
        </div>
      </div>

      <!-- Detail Inspection Panel (1 col) -->
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 flex flex-col justify-between shadow-xl">
        <div class="space-y-4">
          <div class="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 class="text-sm font-bold text-white flex items-center gap-2">
              <svg class="w-4 h-4 text-sky-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Topology Inspector
            </h3>
            <span v-if="selectedNode" class="text-xs font-mono px-2 py-0.5 rounded bg-rose-950 border border-rose-800 text-rose-300">
              Selected Node
            </span>
          </div>

          <!-- If a Node is selected -->
          <div v-if="selectedNode" class="space-y-3 font-mono text-xs">
            <div class="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1">
              <span class="text-slate-500 block text-[10px] uppercase">Account ID</span>
              <span class="text-sky-300 font-bold text-sm break-all">{{ selectedNode.id }}</span>
            </div>

            <div class="grid grid-cols-2 gap-2">
              <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                <span class="text-slate-500 block text-[10px]">In-Degree (Incoming)</span>
                <span class="text-white font-bold text-sm">{{ selectedNode.in_degree || 2 }} txs</span>
              </div>
              <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800">
                <span class="text-slate-500 block text-[10px]">Out-Degree (Outgoing)</span>
                <span class="text-white font-bold text-sm">{{ selectedNode.out_degree || 2 }} txs</span>
              </div>
            </div>

            <div class="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1">
              <span class="text-slate-500 block text-[10px] uppercase">Total Ring Volume Flow</span>
              <span class="text-amber-400 font-bold text-base">
                ${{ Number(selectedNode.total_volume || 842500).toLocaleString() }}
              </span>
            </div>

            <div class="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1">
              <span class="text-slate-500 block text-[10px] uppercase">GraphSAGE Risk Assessment</span>
              <div class="flex items-center justify-between">
                <span class="text-slate-300">Ring Probability:</span>
                <span class="text-rose-400 font-bold">{{ ((selectedNode.risk_score || 0.88) * 100).toFixed(1) }}%</span>
              </div>
              <p class="text-[11px] text-slate-400 font-sans mt-1">
                Participates in a closed cyclic transfer chain with structured split amounts.
              </p>
            </div>
          </div>

          <!-- If no node selected, show general ring statistics -->
          <div v-else class="space-y-3 font-mono text-xs text-slate-400">
            <div class="bg-slate-950 p-3.5 rounded-lg border border-slate-800">
              <h4 class="text-slate-200 font-bold text-sm mb-1 font-sans">Active Laundering Detection</h4>
              <p class="text-xs text-slate-400 font-sans leading-relaxed">
                The GNN engine models directional money flow graphs. When funds circulate in loops (e.g. Mule A &rarr; Mule B &rarr; Mule C &rarr; Mule A), GNN embedding distance shrinks rapidly, triggering proactive ring blocks.
              </p>
            </div>

            <div class="bg-slate-950 p-3.5 rounded-lg border border-slate-800 space-y-2">
              <div class="flex justify-between">
                <span class="text-slate-400">Discovered Rings:</span>
                <span class="text-rose-400 font-bold">3 Active Rings</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Accounts Flagged:</span>
                <span class="text-white font-bold">12 Mule Accounts</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">Laundered Capital:</span>
                <span class="text-amber-300 font-bold">$2,840,000</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick actions -->
        <div class="pt-4 border-t border-slate-800">
          <button
            v-if="selectedNode"
            @click="selectedNode = null"
            class="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-mono font-medium transition-colors">
            Clear Selection
          </button>
          <div v-else class="text-center text-[11px] text-slate-500 font-mono">
            Click any node on the graph to inspect account signals
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
  ringsData: {
    type: Object,
    default: () => ({
      nodes: [],
      edges: [],
      rings: []
    })
  }
})

const svgRef = ref(null)
const selectedRingId = ref('all')
const selectedNode = ref(null)
const zoomLevel = ref(1.0)
const panX = ref(160)
const panY = ref(120)
const isPanning = ref(false)
const startMouseX = ref(0)
const startMouseY = ref(0)

// Default simulated topology if API rings data is empty or fetching
const defaultRings = [
  {
    ring_id: 'ring-1',
    title: 'Ring #1: Cyclic Triangle (Laundering Circuit)',
    nodes: [
      { id: 'C1000000001', role: 'mule', x: 200, y: 150, risk_score: 0.94, total_volume: 450000, isFraud: true, in_degree: 2, out_degree: 2 },
      { id: 'C1000000002', role: 'mule', x: 340, y: 150, risk_score: 0.91, total_volume: 420000, isFraud: true, in_degree: 2, out_degree: 2 },
      { id: 'C1000000003', role: 'mule', x: 270, y: 270, risk_score: 0.96, total_volume: 490000, isFraud: true, in_degree: 2, out_degree: 2 }
    ],
    edges: [
      { source: 'C1000000001', target: 'C1000000002', amount: 450000, isRingEdge: true },
      { source: 'C1000000002', target: 'C1000000003', amount: 420000, isRingEdge: true },
      { source: 'C1000000003', target: 'C1000000001', amount: 410000, isRingEdge: true }
    ]
  },
  {
    ring_id: 'ring-2',
    title: 'Ring #2: Mule Distribution Fan-Out',
    nodes: [
      { id: 'C2000000001', role: 'origin', x: 520, y: 160, risk_score: 0.82, total_volume: 850000, isFraud: true, in_degree: 1, out_degree: 3 },
      { id: 'C2000000002', role: 'mule', x: 640, y: 100, risk_score: 0.88, total_volume: 280000, isFraud: true, in_degree: 1, out_degree: 1 },
      { id: 'C2000000003', role: 'mule', x: 660, y: 180, risk_score: 0.85, total_volume: 310000, isFraud: true, in_degree: 1, out_degree: 1 },
      { id: 'C2000000004', role: 'mule', x: 640, y: 260, risk_score: 0.89, total_volume: 260000, isFraud: true, in_degree: 1, out_degree: 1 }
    ],
    edges: [
      { source: 'C2000000001', target: 'C2000000002', amount: 280000, isRingEdge: true },
      { source: 'C2000000001', target: 'C2000000003', amount: 310000, isRingEdge: true },
      { source: 'C2000000001', target: 'C2000000004', amount: 260000, isRingEdge: true }
    ]
  },
  {
    ring_id: 'ring-3',
    title: 'Ring #3: Smurfing Rapid Aggregation Loop',
    nodes: [
      { id: 'C3000000001', role: 'mule', x: 220, y: 440, risk_score: 0.89, total_volume: 620000, isFraud: true, in_degree: 1, out_degree: 1 },
      { id: 'C3000000002', role: 'mule', x: 380, y: 440, risk_score: 0.92, total_volume: 600000, isFraud: true, in_degree: 1, out_degree: 1 },
      { id: 'C3000000003', role: 'hub', x: 500, y: 420, risk_score: 0.95, total_volume: 1200000, isFraud: true, in_degree: 2, out_degree: 1 }
    ],
    edges: [
      { source: 'C3000000001', target: 'C3000000002', amount: 600000, isRingEdge: true },
      { source: 'C3000000002', target: 'C3000000003', amount: 590000, isRingEdge: true },
      { source: 'C3000000003', target: 'C3000000001', amount: 550000, isRingEdge: true }
    ]
  }
]

const ringsList = computed(() => {
  if (props.ringsData && props.ringsData.rings && props.ringsData.rings.length > 0) {
    return props.ringsData.rings
  }
  return defaultRings
})

const ringClusters = computed(() => {
  return ringsList.value.map((ring, idx) => {
    let sumX = 0, sumY = 0
    const nodes = ring.nodes || []
    nodes.forEach(n => {
      sumX += (n.x || 200)
      sumY += (n.y || 200)
    })
    const count = nodes.length || 1
    return {
      title: ring.title || `Laundering Ring #${idx + 1}`,
      cx: sumX / count,
      cy: sumY / count,
      radius: 90
    }
  })
})

const renderedNodes = computed(() => {
  let allNodes = []
  if (selectedRingId.value === 'all') {
    ringsList.value.forEach(ring => {
      allNodes.push(...(ring.nodes || []))
    })
  } else {
    const ring = ringsList.value.find(r => r.ring_id === selectedRingId.value)
    if (ring) allNodes = ring.nodes || []
  }
  return allNodes
})

const renderedEdges = computed(() => {
  let allEdges = []
  if (selectedRingId.value === 'all') {
    ringsList.value.forEach(ring => {
      allEdges.push(...(ring.edges || []))
    })
  } else {
    const ring = ringsList.value.find(r => r.ring_id === selectedRingId.value)
    if (ring) allEdges = ring.edges || []
  }
  return allEdges
})

const selectRing = (ringId) => {
  selectedRingId.value = ringId
  selectedNode.value = null
  if (ringId === 'ring-1') {
    panX.value = 180
    panY.value = 140
    zoomLevel.value = 1.25
  } else if (ringId === 'ring-2') {
    panX.value = -120
    panY.value = 140
    zoomLevel.value = 1.25
  } else if (ringId === 'ring-3') {
    panX.value = 80
    panY.value = -120
    zoomLevel.value = 1.25
  } else {
    resetZoom()
  }
}

const selectNode = (node) => {
  selectedNode.value = node
}

const selectEdge = (edge) => {
  console.log('Selected Edge:', edge)
}

const truncateId = (id) => {
  if (!id) return ''
  return id.length > 8 ? `${id.slice(0, 4)}...${id.slice(-3)}` : id
}

const getNodeColor = (node) => {
  if (node.isFraud || node.risk_score >= 0.7) return '#f43f5e' // Rose
  if (node.role === 'origin') return '#f59e0b' // Amber
  return '#38bdf8' // Sky
}

const calculateEdgePath = (edge) => {
  const sourceNode = renderedNodes.value.find(n => n.id === edge.source)
  const targetNode = renderedNodes.value.find(n => n.id === edge.target)
  if (!sourceNode || !targetNode) return ''

  const sx = sourceNode.x
  const sy = sourceNode.y
  const tx = targetNode.x
  const ty = targetNode.y

  // Quadratic curved path
  const dx = tx - sx
  const dy = ty - sy
  const cx = (sx + tx) / 2 - dy * 0.15
  const cy = (sy + ty) / 2 + dx * 0.15

  return `M ${sx} ${sy} Q ${cx} ${cy} ${tx} ${ty}`
}

// Pan & Zoom handlers
const zoomIn = () => {
  zoomLevel.value = Math.min(2.5, zoomLevel.value + 0.2)
}
const zoomOut = () => {
  zoomLevel.value = Math.max(0.5, zoomLevel.value - 0.2)
}
const resetZoom = () => {
  zoomLevel.value = 1.0
  panX.value = 80
  panY.value = 60
}

const startPan = (e) => {
  isPanning.value = true
  startMouseX.value = e.clientX - panX.value
  startMouseY.value = e.clientY - panY.value
}
const onPan = (e) => {
  if (!isPanning.value) return
  panX.value = e.clientX - startMouseX.value
  panY.value = e.clientY - startMouseY.value
}
const endPan = () => {
  isPanning.value = false
}
const onWheel = (e) => {
  const delta = e.deltaY < 0 ? 0.1 : -0.1
  zoomLevel.value = Math.min(2.5, Math.max(0.4, zoomLevel.value + delta))
}
</script>

