<script setup lang="ts">
import * as echarts from 'echarts'
import type { ScreenSpaceEventHandler, Viewer } from 'cesium'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import 'cesium/Build/Cesium/Widgets/widgets.css'

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
  content: string
  lat: number
  lng: number
  createdAt: string
}

interface AggregatedPoint {
  id: string
  title: string
  content: string
  lat: number
  lng: number
  count: number
  createdAt: string
  items: QuestionPoint[]
  cluster: boolean
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
const hoveredPoint = ref<QuestionPoint | null>(null)
const hoveredPointId = ref<string | null>(null)
const selectedPoint = ref<QuestionPoint | null>(null)
const selectedCluster = ref<AggregatedPoint | null>(null)
const tooltipX = ref(0)
const tooltipY = ref(0)

const mapStageShellRef = ref<HTMLDivElement | null>(null)
const map2dRef = ref<HTMLDivElement | null>(null)
const map3dRef = ref<HTMLDivElement | null>(null)

let map2dChart: echarts.ECharts | null = null
let map2dGeoRoamBound = false
let map2dClickBound = false
let worldMapRegistered = false
let cesiumViewer: Viewer | null = null
let cesiumHoverHandler: ScreenSpaceEventHandler | null = null
let cesiumRuntime: typeof import('cesium') | null = null
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

function getAggregationCellSize(mode: MapMode, zoom: number, pointCount: number): number {
  if (pointCount <= 80) {
    return mode === '2d' ? 1.5 : 2.4
  }
  if (mode === '2d') {
    return Math.max(0.4, 10 / Math.max(zoom, 1))
  }
  if (pointCount > 800) {
    return 6
  }
  if (pointCount > 300) {
    return 4
  }
  return 2.8
}

function aggregatePoints(points: QuestionPoint[], mode: MapMode, zoom: number): AggregatedPoint[] {
  const cellSize = getAggregationCellSize(mode, zoom, points.length)
  const buckets = new Map<string, QuestionPoint[]>()

  for (const point of points) {
    const lngBucket = Math.round(point.lng / cellSize)
    const latBucket = Math.round(point.lat / cellSize)
    const key = `${lngBucket}:${latBucket}`
    const bucket = buckets.get(key)
    if (bucket) {
      bucket.push(point)
    } else {
      buckets.set(key, [point])
    }
  }

  return Array.from(buckets.entries()).map(([key, items]) => {
    const lng = items.reduce((sum, item) => sum + item.lng, 0) / items.length
    const lat = items.reduce((sum, item) => sum + item.lat, 0) / items.length
    const latestCreatedAt = items
      .map((item) => item.createdAt)
      .filter(Boolean)
      .sort()
    const latestCreatedAtValue = latestCreatedAt[latestCreatedAt.length - 1] ?? ''

    if (items.length === 1) {
      const item = items[0]
      if (!item) {
        return {
          id: `cluster:${mode}:${key}`,
          title: '0 个问题',
          content: '',
          lat,
          lng,
          count: 0,
          createdAt: '',
          items: [],
          cluster: true,
        }
      }
      return {
        id: item.id,
        title: item.title,
        content: item.content,
        lat: item.lat,
        lng: item.lng,
        count: 1,
        createdAt: item.createdAt,
        items,
        cluster: false,
      }
    }

    const preview = items
      .slice(0, 3)
      .map((item) => item.title)
      .join(' / ')

    return {
      id: `cluster:${mode}:${key}`,
      title: `${items.length} 个问题`,
      content: preview,
      lat,
      lng,
      count: items.length,
      createdAt: latestCreatedAtValue,
      items,
      cluster: true,
    }
  })
}

const aggregatedPoints = computed(() => aggregatePoints(mapPoints.value, selectedMode.value, map2dZoom.value))
const aggregatedPointCount = computed(() => aggregatedPoints.value.length)

const pointIndexMap = computed(() => {
  const index = new Map<string, AggregatedPoint>()
  for (const point of aggregatedPoints.value) {
    index.set(point.id, point)
  }
  return index
})

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

const selectedPointTime = computed(() => {
  if (!selectedPoint.value?.createdAt) {
    return '--'
  }
  const parsed = new Date(selectedPoint.value.createdAt)
  if (Number.isNaN(parsed.getTime())) {
    return '--'
  }
  return parsed.toLocaleString('zh-CN', { hour12: false })
})

const selectedClusterPreview = computed(() => {
  if (!selectedCluster.value) {
    return []
  }
  return selectedCluster.value.items
})

function getThemeColor(name: string, fallback: string): string {
  const base = mapStageShellRef.value ?? document.documentElement
  const value = getComputedStyle(base).getPropertyValue(name).trim()
  return value || fallback
}

function getMapThemePalette(): {
  singleFill: string
  singleOutline: string
  clusterFill: string
  clusterOutline: string
  clusterText: string
  clusterChipBg: string
  globeBase: string
  sceneBackground: string
  atmosphere: string
  atmosphereGlow: string
} {
  return {
    singleFill: getThemeColor('--accent', '#61b6ff'),
    singleOutline: getThemeColor('--accent-strong', '#8cd4ff'),
    clusterFill: getThemeColor('--accent-strong', '#2d73d5'),
    clusterOutline: getThemeColor('--line', '#8cd4ff'),
    clusterText: getThemeColor('--surface-3', '#09111e'),
    clusterChipBg: getThemeColor('--surface-chip', 'rgba(97, 182, 255, 0.16)'),
    globeBase: getThemeColor('--surface-2', '#122034'),
    sceneBackground: getThemeColor('--bg-0', '#09111e'),
    atmosphere: getThemeColor('--accent', '#61b6ff'),
    atmosphereGlow: getThemeColor('--panel-glow', 'rgba(97, 182, 255, 0.16)'),
  }
}

function selectAggregatedPointById(pointId: string | null): void {
  if (!pointId) {
    clearSelectedPoint()
    return
  }
  const selected = pointIndexMap.value.get(pointId) ?? null
  if (selected?.cluster) {
    selectedCluster.value = selected
    selectedPoint.value = null
    return
  }
  selectedPoint.value = selected?.items[0] ?? null
  selectedCluster.value = null
}

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
  let start = toLocalDayStart(now)
  let end = new Date(start)

  if (range === 'week') {
    start = new Date(start)
    start.setDate(start.getDate() - start.getDay() + (start.getDay() === 0 ? -6 : 1))
    end = new Date(start)
    end.setDate(end.getDate() + 7)
  } else if (range === 'month') {
    start = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0)
    end = new Date(now.getFullYear(), now.getMonth() + 1, 1, 0, 0, 0, 0)
  } else if (range === 'year') {
    start = new Date(now.getFullYear(), 0, 1, 0, 0, 0, 0)
    end = new Date(now.getFullYear() + 1, 0, 1, 0, 0, 0, 0)
  } else {
    end = new Date(start)
    end.setDate(end.getDate() + 1)
  }

  return {
    createdFrom: start.toISOString(),
    createdTo: end.toISOString(),
  }
}

function clearHoveredPoint(): void {
  hoveredPoint.value = null
  hoveredPointId.value = null
}

function clearSelectedPoint(): void {
  selectedPoint.value = null
  selectedCluster.value = null
}

function updateTooltipPosition(screenX: number, screenY: number): void {
  const shellRect = mapStageShellRef.value?.getBoundingClientRect()
  if (!shellRect) {
    tooltipX.value = screenX + 14
    tooltipY.value = screenY - 36
    return
  }

  tooltipX.value = screenX - shellRect.left + 14
  tooltipY.value = screenY - shellRect.top - 36
}

async function loadCesium(): Promise<typeof import('cesium')> {
  if (cesiumRuntime) {
    return cesiumRuntime
  }
  cesiumRuntime = await import('cesium')
  return cesiumRuntime
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
    content: item.content || `问题 ${item.id}`,
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

function build2DSeriesData(): Array<{ id: string; name: string; value: [number, number, number]; createdAt: string; count: number; cluster: boolean }> {
  return aggregatedPoints.value.map((point, index) => ({
    id: point.id,
    name: point.title,
    value: [point.lng, point.lat, 12 + Math.min(18, Math.max(point.count * 2, index % 5))],
    createdAt: point.createdAt,
    count: point.count,
    cluster: point.cluster,
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
        formatter: (params: { data?: { name?: string; createdAt?: string; count?: number; cluster?: boolean } }) => {
          const title = params.data?.name ?? '未命名问题'
          const createdAt = params.data?.createdAt ? new Date(params.data.createdAt).toLocaleString('zh-CN', { hour12: false }) : '未知时间'
          const count = params.data?.count ?? 1
          const clusterLabel = params.data?.cluster ? `<br/>聚合数量: ${count}` : ''
          return `<strong>${title}</strong>${clusterLabel}<br/>创建时间: ${createdAt}`
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

  if (!map2dClickBound) {
    map2dChart.on('click', (params: { data?: unknown }) => {
      const record = params.data && typeof params.data === 'object' ? (params.data as { id?: string }) : undefined
      selectAggregatedPointById(record?.id ?? null)
    })
    map2dClickBound = true
  }

  render2DMap()
  map2dChart.resize()
}

async function init3DMap(): Promise<void> {
  if (!map3dRef.value) {
    return
  }

  if (cesiumViewer) {
    resize3DMap()
    render3DPoints()
    return
  }

  const cesium = await loadCesium()
  const palette = getMapThemePalette()

  cesiumViewer = new cesium.Viewer(map3dRef.value, {
    baseLayer: false,
    baseLayerPicker: false,
    animation: false,
    timeline: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    homeButton: false,
    fullscreenButton: false,
    infoBox: false,
    selectionIndicator: false,
    geocoder: false,
    creditContainer: document.createElement('div'),
    requestRenderMode: true,
    maximumRenderTimeChange: Number.POSITIVE_INFINITY,
  })

  // Add OpenStreetMap as the base imagery layer
  cesiumViewer.imageryLayers.addImageryProvider(
    new cesium.OpenStreetMapImageryProvider({
      url: 'https://tile.openstreetmap.org/',
    }),
  )

  // Ensure globe and atmosphere are visible
  cesiumViewer.scene.skyAtmosphere!.show = true
  cesiumViewer.scene.globe.show = true
  cesiumViewer.scene.backgroundColor = cesium.Color.fromCssColorString(palette.sceneBackground)
  cesiumViewer.scene.globe.baseColor = cesium.Color.fromCssColorString(palette.globeBase)
  cesiumViewer.scene.skyAtmosphere!.hueShift = 0.08
  cesiumViewer.scene.skyAtmosphere!.saturationShift = -0.12
  cesiumViewer.scene.skyAtmosphere!.brightnessShift = -0.18
  cesiumViewer.scene.globe.showGroundAtmosphere = true

  // Hover detection: show tooltip only when mouse is over a point
  cesiumHoverHandler = new cesium.ScreenSpaceEventHandler(cesiumViewer.scene.canvas)
  cesiumHoverHandler.setInputAction((movement: { endPosition: { x: number; y: number } }) => {
    updateTooltipPosition(movement.endPosition.x, movement.endPosition.y)
    const picked = cesiumViewer!.scene.pick(movement.endPosition as import('cesium').Cartesian2)
    if (cesium.defined(picked) && cesium.defined(picked.id)) {
      const entityId = picked.id.id as string
      if (hoveredPointId.value === entityId) {
        return
      }
      hoveredPointId.value = entityId
      const hovered = pointIndexMap.value.get(entityId) ?? null
      hoveredPoint.value = hovered && !hovered.cluster ? hovered.items[0] ?? null : null
    } else {
      clearHoveredPoint()
    }
  }, cesium.ScreenSpaceEventType.MOUSE_MOVE)

  cesiumHoverHandler.setInputAction((movement: { position: { x: number; y: number } }) => {
    const picked = cesiumViewer!.scene.pick(movement.position as import('cesium').Cartesian2)
    if (cesium.defined(picked) && cesium.defined(picked.id)) {
      const entityId = picked.id.id as string
      selectAggregatedPointById(entityId)
      cesiumViewer!.scene.requestRender()
      return
    }
    clearSelectedPoint()
  }, cesium.ScreenSpaceEventType.LEFT_CLICK)

  map3dRef.value.addEventListener('mouseleave', clearHoveredPoint)

  resize3DMap()
  render3DPoints()
  cesiumViewer.scene.requestRender()
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function resize3DMap(): void {
  if (!cesiumViewer || !map3dRef.value) {
    return
  }
  cesiumViewer.resize()
}

function render3DPoints(): void {
  if (!cesiumViewer) {
    return
  }

  const cesium = cesiumRuntime
  if (!cesium) {
    return
  }
  const palette = getMapThemePalette()

  // Remove existing question-point entities
  cesiumViewer.entities.removeAll()

  for (const point of aggregatedPoints.value) {
    const timeStr = point.createdAt
      ? new Date(point.createdAt).toLocaleString('zh-CN', { hour12: false })
      : '未知时间'
    cesiumViewer!.entities.add({
      id: point.id,
      position: cesium.Cartesian3.fromDegrees(point.lng, point.lat, 0),
      point: {
        pixelSize: point.cluster ? Math.min(18, 8 + Math.ceil(point.count / 2)) : 9,
        color: point.cluster
          ? cesium.Color.fromCssColorString(palette.clusterFill).withAlpha(0.94)
          : cesium.Color.fromCssColorString(palette.singleFill).withAlpha(0.9),
        outlineColor: point.cluster
          ? cesium.Color.fromCssColorString(palette.clusterOutline)
          : cesium.Color.fromCssColorString(palette.singleOutline),
        outlineWidth: point.cluster ? 2.4 : 1.8,
        heightReference: cesium.HeightReference.CLAMP_TO_GROUND,
      },
      description: point.cluster ? `聚合问题数: ${point.count}` : `创建时间: ${timeStr}`,
    })
  }

  cesiumViewer.scene.requestRender()
}

function zoom2D(multiplier: number): void {
  map2dZoom.value = clamp(map2dZoom.value * multiplier, 0.7, 8)
  if (map2dChart) {
    map2dChart.setOption({ geo: { zoom: map2dZoom.value } })
  }
}

function zoom3D(multiplier: number): void {
  if (!cesiumViewer) {
    return
  }
  const cesium = cesiumRuntime
  if (!cesium) {
    return
  }
  const camera = cesiumViewer.camera
  const height = camera.positionCartographic.height
  const newHeight = clamp(height * multiplier, 10000, 60000000)
  camera.flyTo({
    destination: cesium.Cartesian3.fromRadians(
      camera.positionCartographic.longitude,
      camera.positionCartographic.latitude,
      newHeight,
    ),
    duration: 0.3,
  })
  cesiumViewer.scene.requestRender()
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

function resizeActiveMap(): void {
  if (selectedMode.value === '2d') {
    map2dChart?.resize()
    return
  }
  resize3DMap()
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
        await init3DMap()
      }
    }
  }
}

function syncMapByMode(): void {
  if (selectedMode.value === '2d') {
    void init2DMap()
    return
  }
  void init3DMap()
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
  clearSelectedPoint()
  void fetchQuestionsByRange()
})

watch(selectedMode, () => {
  clearHoveredPoint()
  clearSelectedPoint()
  if (cesiumViewer) {
    cesiumViewer.useDefaultRenderLoop = selectedMode.value === '3d'
    if (selectedMode.value === '3d') {
      cesiumViewer.scene.requestRender()
    }
  }
  nextTick(() => {
    syncMapByMode()
  })
})

watch(mapPoints, () => {
  clearSelectedPoint()
  if (selectedMode.value === '2d') {
    render2DMap()
    return
  }
  render3DPoints()
})

watch(
  () => props.backendOnline,
  () => {
    clearHoveredPoint()
    clearSelectedPoint()
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
  map3dRef.value?.removeEventListener('mouseleave', clearHoveredPoint)
  if (cesiumHoverHandler) {
    cesiumHoverHandler.destroy()
    cesiumHoverHandler = null
  }
  if (cesiumViewer) {
    cesiumViewer.destroy()
    cesiumViewer = null
  }
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

    <div ref="mapStageShellRef" class="map-stage-shell">
      <div ref="map2dRef" v-show="selectedMode === '2d'" class="map-stage"></div>
      <div ref="map3dRef" v-show="selectedMode === '3d'" class="map-stage map-stage-globe"></div>
      <div v-if="selectedMode === '3d' && hoveredPoint" class="map-tooltip" :style="{ left: tooltipX + 'px', top: tooltipY + 'px' }">{{ hoveredPoint.title }}</div>
      <div v-if="selectedPoint" class="map-point-detail">
        <div class="map-point-detail-head">
          <strong>问题详情</strong>
          <button class="action-btn mini-btn" @click="clearSelectedPoint">关闭</button>
        </div>
        <p>{{ selectedPoint.content }}</p>
        <div class="map-point-detail-meta">
          <span>ID: {{ selectedPoint.id }}</span>
          <span>时间: {{ selectedPointTime }}</span>
          <span>坐标: {{ selectedPoint.lng.toFixed(4) }}, {{ selectedPoint.lat.toFixed(4) }}</span>
        </div>
      </div>
      <div v-if="selectedCluster" class="map-point-detail">
        <div class="map-point-detail-head">
          <strong>聚合详情</strong>
          <button class="action-btn mini-btn" @click="clearSelectedPoint">关闭</button>
        </div>
        <p>当前位置聚合了 {{ selectedCluster.count }} 个问题。</p>
        <div class="map-point-detail-meta">
          <span>坐标中心: {{ selectedCluster.lng.toFixed(4) }}, {{ selectedCluster.lat.toFixed(4) }}</span>
          <span>问题列表:</span>
        </div>
        <div class="map-cluster-preview">
          <article v-for="item in selectedClusterPreview" :key="item.id" class="map-cluster-item">
            <strong>{{ item.title }}</strong>
            <small>
              {{ item.createdAt ? new Date(item.createdAt).toLocaleString('zh-CN', { hour12: false }) : '未知时间' }}
            </small>
          </article>
        </div>
      </div>
      <div v-if="loading" class="map-overlay">地图加载中...</div>
      <div v-else-if="errorMessage" class="map-overlay map-overlay-error">{{ errorMessage }}</div>
      <div v-else-if="pointsWithCoordinates === 0" class="map-overlay">当前筛选范围内暂无带坐标问题</div>
    </div>

    <div class="map-meta-row">
      <span>问题总数: {{ totalQuestions }}</span>
      <span>坐标问题: {{ pointsWithCoordinates }}</span>
      <span>渲染点位: {{ aggregatedPointCount }}</span>
      <span>更新时间: {{ displayUpdatedAt }}</span>
    </div>
  </article>
</template>
