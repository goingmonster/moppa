<script setup lang="ts">
import * as echarts from 'echarts'
import Globe from 'globe.gl'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

type TimeRange = 'today' | 'week' | 'month' | 'year' | 'all'
type MapMode = '2d' | '3d'

interface BackendQuestionItem {
  id: string
  content: string
  created_at?: string | null
  coordinates?: unknown
  location?: unknown
  geo?: unknown
  coordinate?: unknown
  lat?: unknown
  lng?: unknown
  lon?: unknown
  latitude?: unknown
  longitude?: unknown
  [key: string]: unknown
}

interface BackendPage<T> {
  page: number
  page_size: number
  total: number
  items: T[]
}

interface QuestionPoint {
  id: string
  title: string
  lat: number
  lng: number
  createdAt: string
}

interface GlobePoint {
  id: string
  lat: number
  lng: number
  size: number
  altitude: number
  color: string
  label: string
}

interface GlobeControlLike {
  enableZoom: boolean
  minDistance?: number
  maxDistance?: number
  enablePan?: boolean
  autoRotate?: boolean
}

interface GlobeViewLike {
  lat?: number
  lng?: number
  altitude?: number
}

interface GlobeLike {
  width: (value: number) => GlobeLike
  height: (value: number) => GlobeLike
  globeImageUrl: (value: string) => GlobeLike
  bumpImageUrl: (value: string) => GlobeLike
  backgroundColor: (value: string) => GlobeLike
  atmosphereColor: (value: string) => GlobeLike
  atmosphereAltitude: (value: number) => GlobeLike
  pointsData: (value: GlobePoint[]) => GlobeLike
  pointLat: (value: string | ((point: GlobePoint) => number)) => GlobeLike
  pointLng: (value: string | ((point: GlobePoint) => number)) => GlobeLike
  pointRadius: (value: string | ((point: GlobePoint) => number)) => GlobeLike
  pointAltitude: (value: string | ((point: GlobePoint) => number)) => GlobeLike
  pointColor: (value: string | ((point: GlobePoint) => string)) => GlobeLike
  pointLabel: (value: string | ((point: GlobePoint) => string)) => GlobeLike
  controls: () => GlobeControlLike
  pointOfView: (value?: GlobeViewLike, transitionMs?: number) => GlobeViewLike
  _destructor?: () => void
}

const props = defineProps<{
  backendOnline: boolean
}>()

const rangeOptions: Array<{ id: TimeRange; label: string }> = [
  { id: 'today', label: 'today' },
  { id: 'week', label: 'week' },
  { id: 'month', label: 'month' },
  { id: 'year', label: 'year' },
  { id: 'all', label: 'all' },
]

const modeOptions: Array<{ id: MapMode; label: string }> = [
  { id: '2d', label: '2D' },
  { id: '3d', label: '3D' },
]

const selectedRange = ref<TimeRange>('week')
const selectedMode = ref<MapMode>('2d')
const loading = ref(false)
const errorMessage = ref('')
const mapPoints = ref<QuestionPoint[]>([])
const totalQuestions = ref(0)
const lastUpdatedAt = ref('')
const map2dZoom = ref(1.25)

const map2dRef = ref<HTMLDivElement | null>(null)
const map3dRef = ref<HTMLDivElement | null>(null)

let map2dChart: echarts.ECharts | null = null
let map2dGeoRoamBound = false
let worldMapRegistered = false
let map3dGlobe: GlobeLike | null = null
let fetchSeq = 0
let resizeObserver: ResizeObserver | null = null

interface RangeCacheEntry {
  points: QuestionPoint[]
  total: number
  fetchedAt: number
}

const RANGE_CACHE_TTL_MS = 5 * 60 * 1000 // 5 minutes
const rangeCache = new Map<TimeRange, RangeCacheEntry>()

function getCachedRange(range: TimeRange): RangeCacheEntry | null {
  const entry = rangeCache.get(range)
  if (!entry) {
    return null
  }
  if (Date.now() - entry.fetchedAt > RANGE_CACHE_TTL_MS) {
    rangeCache.delete(range)
    return null
  }
  return entry
}

function setCachedRange(range: TimeRange, points: QuestionPoint[], total: number): void {
  rangeCache.set(range, { points, total, fetchedAt: Date.now() })
}

const pointsWithCoordinates = computed(() => mapPoints.value.length)

const displayUpdatedAt = computed(() => {
  if (!lastUpdatedAt.value) {
    return '--'
  }
  const parsed = new Date(lastUpdatedAt.value)
  if (Number.isNaN(parsed.getTime())) {
    return '--'
  }
  return parsed.toLocaleString('zh-CN', { hour12: false })
})

function apiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || 'http://127.0.0.1:8000'
}

function toLocalDayStart(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0)
}

function buildCreatedRange(range: TimeRange): { createdFrom: string | null; createdTo: string | null } {
  if (range === 'all') {
    return { createdFrom: null, createdTo: null }
  }

  const now = new Date()
  const end = now.toISOString()
  let start = toLocalDayStart(now)

  if (range === 'week') {
    start = new Date(start)
    start.setDate(start.getDate() - 6)
  } else if (range === 'month') {
    start = new Date(start)
    start.setDate(start.getDate() - 29)
  } else if (range === 'year') {
    start = new Date(start)
    start.setDate(start.getDate() - 364)
  }

  return {
    createdFrom: start.toISOString(),
    createdTo: end,
  }
}

function parseFiniteNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  if (typeof value === 'string') {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) {
      return parsed
    }
  }
  return null
}

function normalizeLngLat(lngValue: unknown, latValue: unknown): { lng: number; lat: number } | null {
  const lng = parseFiniteNumber(lngValue)
  const lat = parseFiniteNumber(latValue)
  if (lng === null || lat === null) {
    return null
  }
  if (Math.abs(lng) <= 180 && Math.abs(lat) <= 90) {
    return { lng, lat }
  }
  if (Math.abs(lat) <= 180 && Math.abs(lng) <= 90) {
    return { lng: lat, lat: lng }
  }
  return null
}

function extractFromPairObject(value: unknown): { lng: number; lat: number } | null {
  if (!value || typeof value !== 'object') {
    return null
  }
  const record = value as Record<string, unknown>
  return normalizeLngLat(
    record.lng ?? record.lon ?? record.longitude,
    record.lat ?? record.latitude,
  )
}

function extractCoordinates(item: BackendQuestionItem): { lng: number; lat: number } | null {
  const direct = normalizeLngLat(
    item.lng ?? item.lon ?? item.longitude,
    item.lat ?? item.latitude,
  )
  if (direct) {
    return direct
  }

  const candidates = [item.coordinates, item.coordinate, item.location, item.geo]
  for (const candidate of candidates) {
    if (Array.isArray(candidate) && candidate.length >= 2) {
      const fromArray = normalizeLngLat(candidate[0], candidate[1])
      if (fromArray) {
        return fromArray
      }
    }

    const fromObject = extractFromPairObject(candidate)
    if (fromObject) {
      return fromObject
    }

    if (candidate && typeof candidate === 'object') {
      const record = candidate as Record<string, unknown>
      const nestedCoordinates = record.coordinates
      if (Array.isArray(nestedCoordinates) && nestedCoordinates.length >= 2) {
        const fromNested = normalizeLngLat(nestedCoordinates[0], nestedCoordinates[1])
        if (fromNested) {
          return fromNested
        }
      }
      const fromNestedObject = extractFromPairObject(nestedCoordinates)
      if (fromNestedObject) {
        return fromNestedObject
      }
    }
  }

  return null
}

function toQuestionPoint(item: BackendQuestionItem): QuestionPoint | null {
  const coordinates = extractCoordinates(item)
  if (!coordinates) {
    return null
  }
  return {
    id: item.id,
    title: item.content || `问题 ${item.id}`,
    lat: coordinates.lat,
    lng: coordinates.lng,
    createdAt: item.created_at ?? '',
  }
}

function buildAuthHeaders(): HeadersInit {
  const headers = new Headers({ 'Content-Type': 'application/json' })
  const accessToken = localStorage.getItem('moppa_access_token')
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }
  return headers
}

async function ensureWorldMap(): Promise<boolean> {
  if (worldMapRegistered) {
    return true
  }

  const CDN_SOURCES = [
    'https://echarts.apache.org/examples/data/asset/geo/world.json',
    'https://cdn.jsdelivr.net/npm/echarts-map@3.0.1/json/world.json',
    'https://unpkg.com/echarts-map@3.0.1/json/world.json',
  ]

  for (const url of CDN_SOURCES) {
    try {
      const response = await fetch(url)
      if (!response.ok) {
        continue
      }
      const worldGeoJson = await response.json()
      echarts.registerMap('world', worldGeoJson)
      worldMapRegistered = true
      return true
    } catch {
      // try next source
    }
  }

  return false
}

function build2DSeriesData(): Array<{ name: string; value: [number, number, number]; createdAt: string }> {
  return mapPoints.value.map((point, index) => ({
    name: point.title,
    value: [point.lng, point.lat, 12 + Math.min(10, index % 5)],
    createdAt: point.createdAt,
  }))
}

function render2DMap(): void {
  if (!map2dChart) {
    return
  }

  map2dChart.setOption(
    {
      backgroundColor: 'transparent',
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(9, 16, 28, 0.92)',
        borderColor: 'rgba(104, 168, 255, 0.48)',
        textStyle: { color: '#d8e7ff' },
        formatter: (params: { data?: { name?: string; createdAt?: string } }) => {
          const title = params.data?.name ?? '未命名问题'
          const createdAt = params.data?.createdAt ? new Date(params.data.createdAt).toLocaleString('zh-CN', { hour12: false }) : '未知时间'
          return `<strong>${title}</strong><br/>创建时间: ${createdAt}`
        },
      },
      geo: {
        map: 'world',
        roam: true,
        zoom: map2dZoom.value,
        top: 10,
        bottom: 10,
        itemStyle: {
          areaColor: '#122034',
          borderColor: 'rgba(155, 197, 255, 0.38)',
          borderWidth: 0.8,
        },
        emphasis: {
          itemStyle: {
            areaColor: '#1c3558',
          },
          label: { show: false },
        },
      },
      series: [
        {
          name: '问题坐标',
          type: 'effectScatter',
          coordinateSystem: 'geo',
          symbolSize: (value: number[]) => {
            const intensity = value[2] ?? 10
            return intensity / 1.6
          },
          rippleEffect: {
            period: 4,
            scale: 2.8,
            brushType: 'stroke',
          },
          itemStyle: {
            color: '#7ec9ff',
            shadowBlur: 22,
            shadowColor: 'rgba(96, 186, 255, 0.72)',
          },
          data: build2DSeriesData(),
        },
      ],
    },
    { notMerge: true },
  )
}

async function init2DMap(): Promise<void> {
  if (!map2dRef.value) {
    return
  }
  const loaded = await ensureWorldMap()
  if (!loaded) {
    errorMessage.value = '世界底图加载失败，暂时无法渲染 2D 地图。'
    return
  }

  if (!map2dChart) {
    map2dChart = echarts.init(map2dRef.value)
  }

  if (!map2dGeoRoamBound) {
    map2dChart.on('georoam', () => {
      if (!map2dChart) {
        return
      }
      const option = map2dChart.getOption()
      const geoOption = Array.isArray(option.geo) ? option.geo[0] : option.geo
      if (geoOption && typeof geoOption.zoom === 'number') {
        map2dZoom.value = geoOption.zoom
      }
    })
    map2dGeoRoamBound = true
  }

  render2DMap()
  map2dChart.resize()
}

function toGlobePoints(): GlobePoint[] {
  return mapPoints.value.map((point, index) => ({
    id: point.id,
    lat: point.lat,
    lng: point.lng,
    size: 0.12 + ((index % 6) * 0.01),
    altitude: 0.08,
    color: index % 2 === 0 ? '#8cd4ff' : '#61b6ff',
    label: `${point.title}<br/>${point.createdAt ? new Date(point.createdAt).toLocaleString('zh-CN', { hour12: false }) : '未知时间'}`,
  }))
}

function resize3DMap(): void {
  if (!map3dGlobe || !map3dRef.value) {
    return
  }
  const width = Math.max(320, map3dRef.value.clientWidth)
  const height = Math.max(260, map3dRef.value.clientHeight)
  map3dGlobe.width(width).height(height)
}

function render3DPoints(): void {
  if (!map3dGlobe) {
    return
  }
  map3dGlobe.pointsData(toGlobePoints())
}

function init3DMap(): void {
  if (!map3dRef.value) {
    return
  }

  if (!map3dGlobe) {
    const globeFactory = Globe as unknown as () => (element: HTMLElement) => GlobeLike
    map3dGlobe = globeFactory()(map3dRef.value)
      .globeImageUrl('https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg')
      .bumpImageUrl('https://unpkg.com/three-globe/example/img/earth-topology.png')
      .backgroundColor('rgba(0,0,0,0)')
      .atmosphereColor('#6ab1ff')
      .atmosphereAltitude(0.21)
      .pointLat('lat')
      .pointLng('lng')
      .pointRadius('size')
      .pointAltitude('altitude')
      .pointColor('color')
      .pointLabel('label')

    const controls = map3dGlobe.controls()
    controls.enableZoom = true
    controls.enablePan = false
    controls.autoRotate = false
    controls.minDistance = 120
    controls.maxDistance = 700

    map3dGlobe.pointOfView({ lat: 20, lng: 10, altitude: 2.25 }, 0)
  }

  render3DPoints()
  resize3DMap()
}

function resizeActiveMap(): void {
  if (selectedMode.value === '2d') {
    map2dChart?.resize()
    return
  }
  resize3DMap()
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function zoom2D(multiplier: number): void {
  map2dZoom.value = clamp(map2dZoom.value * multiplier, 0.7, 8)
  if (map2dChart) {
    map2dChart.setOption({ geo: { zoom: map2dZoom.value } })
  }
}

function zoom3D(multiplier: number): void {
  if (!map3dGlobe) {
    return
  }
  const current = map3dGlobe.pointOfView()
  const nextAltitude = clamp((current.altitude ?? 2.25) * multiplier, 1.05, 4.2)
  map3dGlobe.pointOfView(
    {
      lat: current.lat ?? 20,
      lng: current.lng ?? 10,
      altitude: nextAltitude,
    },
    280,
  )
}

function zoomIn(): void {
  if (selectedMode.value === '2d') {
    zoom2D(1.2)
    return
  }
  zoom3D(0.82)
}

function zoomOut(): void {
  if (selectedMode.value === '2d') {
    zoom2D(0.82)
    return
  }
  zoom3D(1.2)
}

async function fetchQuestionsByRange(): Promise<void> {
  fetchSeq += 1
  const currentSeq = fetchSeq
  const range = selectedRange.value

  if (!props.backendOnline) {
    mapPoints.value = []
    totalQuestions.value = 0
    loading.value = false
    errorMessage.value = '后端离线：地图仅在后端在线时显示坐标数据。'
    return
  }

  // Serve from cache if already fetched for this range (within TTL)
  const cached = getCachedRange(range)
  if (cached) {
    if (currentSeq !== fetchSeq) {
      return
    }
    mapPoints.value = cached.points
    totalQuestions.value = cached.total
    lastUpdatedAt.value = new Date(cached.fetchedAt).toISOString()
    loading.value = false
    errorMessage.value = ''
    await nextTick()
    syncMapByMode()
    return
  }

  loading.value = true
  errorMessage.value = ''
  try {
    const { createdFrom, createdTo } = buildCreatedRange(selectedRange.value)
    const pageSize = 200
    const maxPages = 25
    const gathered: BackendQuestionItem[] = []

    for (let page = 1; page <= maxPages; page += 1) {
      const query = new URLSearchParams()
      query.set('keyword', '')
      query.set('deleted_mode', 'active_only')
      query.set('page', String(page))
      query.set('page_size', String(pageSize))
      if (createdFrom) {
        query.set('created_from', createdFrom)
      }
      if (createdTo) {
        query.set('created_to', createdTo)
      }

      const response = await fetch(`${apiBaseUrl()}/questions/search?${query.toString()}`, {
        method: 'GET',
        headers: buildAuthHeaders(),
      })
      if (!response.ok) {
        throw new Error(`请求失败: ${response.status}`)
      }

      const payload = (await response.json()) as BackendPage<BackendQuestionItem>
      if (currentSeq !== fetchSeq) {
        return
      }

      gathered.push(...payload.items)

      if (payload.items.length === 0 || gathered.length >= payload.total) {
        break
      }
    }

    if (currentSeq !== fetchSeq) {
      return
    }

    mapPoints.value = gathered
      .map(toQuestionPoint)
      .filter((point): point is QuestionPoint => point !== null)

    totalQuestions.value = gathered.length
    lastUpdatedAt.value = new Date().toISOString()
    setCachedRange(range, mapPoints.value, totalQuestions.value)
  } catch {
    if (currentSeq !== fetchSeq) {
      return
    }
    mapPoints.value = []
    totalQuestions.value = 0
    errorMessage.value = '地图数据加载失败：请检查问题搜索接口和坐标字段。'
  } finally {
    if (currentSeq === fetchSeq) {
      loading.value = false
      await nextTick()
      if (selectedMode.value === '2d') {
        await init2DMap()
      } else {
        init3DMap()
      }
    }
  }
}

function syncMapByMode(): void {
  if (selectedMode.value === '2d') {
    void init2DMap()
    return
  }
  init3DMap()
}

function observeMapContainers(): void {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  resizeObserver = new ResizeObserver(() => {
    resizeActiveMap()
  })
  if (map2dRef.value) {
    resizeObserver.observe(map2dRef.value)
  }
  if (map3dRef.value) {
    resizeObserver.observe(map3dRef.value)
  }
}

watch(selectedRange, () => {
  void fetchQuestionsByRange()
})

watch(selectedMode, () => {
  nextTick(() => {
    syncMapByMode()
  })
})

watch(mapPoints, () => {
  if (selectedMode.value === '2d') {
    render2DMap()
    return
  }
  render3DPoints()
})

watch(
  () => props.backendOnline,
  () => {
    void fetchQuestionsByRange()
  },
)

onMounted(() => {
  observeMapContainers()
  window.addEventListener('resize', resizeActiveMap)
  void fetchQuestionsByRange()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', resizeActiveMap)
  resizeObserver?.disconnect()
  resizeObserver = null
  if (map2dChart) {
    map2dChart.dispose()
    map2dChart = null
  }
  if (map3dGlobe && typeof map3dGlobe._destructor === 'function') {
    map3dGlobe._destructor()
  }
  map3dGlobe = null
})
</script>

<template>
  <article class="panel map-overview-panel">
    <div class="panel-head map-panel-head">
      <div>
        <h2>问题分布地图</h2>
        <span>默认展示本周带坐标问题，支持 2D/3D 切换与缩放</span>
      </div>
      <div class="map-zoom-actions">
        <button class="action-btn mini-btn" @click="zoomOut">缩小</button>
        <button class="action-btn mini-btn" @click="zoomIn">放大</button>
      </div>
    </div>

    <div class="map-control-bar">
      <div class="map-toggle-group">
        <span class="map-toggle-label">Time</span>
        <button
          v-for="option in rangeOptions"
          :key="`range-${option.id}`"
          :class="['level-btn map-toggle-btn', { active: selectedRange === option.id }]"
          @click="selectedRange = option.id"
        >
          {{ option.label }}
        </button>
      </div>
      <div class="map-toggle-group">
        <span class="map-toggle-label">Mode</span>
        <button
          v-for="option in modeOptions"
          :key="`mode-${option.id}`"
          :class="['level-btn map-toggle-btn', { active: selectedMode === option.id }]"
          @click="selectedMode = option.id"
        >
          {{ option.label }}
        </button>
      </div>
    </div>

    <div class="map-stage-shell">
      <div ref="map2dRef" v-show="selectedMode === '2d'" class="map-stage"></div>
      <div ref="map3dRef" v-show="selectedMode === '3d'" class="map-stage map-stage-globe"></div>
      <div v-if="loading" class="map-overlay">地图加载中...</div>
      <div v-else-if="errorMessage" class="map-overlay map-overlay-error">{{ errorMessage }}</div>
      <div v-else-if="pointsWithCoordinates === 0" class="map-overlay">当前筛选范围内暂无带坐标问题</div>
    </div>

    <div class="map-meta-row">
      <span>问题总数: {{ totalQuestions }}</span>
      <span>坐标问题: {{ pointsWithCoordinates }}</span>
      <span>更新时间: {{ displayUpdatedAt }}</span>
    </div>
  </article>
</template>
