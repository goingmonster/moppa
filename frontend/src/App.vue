<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

type Level = 'L1' | 'L2' | 'L3' | 'L4'
type AppView = 'home' | 'events' | 'questions'

interface EventItem {
  id: string
  codename: string
  theater: string
  summary: string
  severity: 'low' | 'medium' | 'high'
  timestamp: string
}

interface TemplateItem {
  level: Level
  objective: string
  constraints: string
  outputFormat: string
  qualityRule: string
}

interface QuestionItem {
  id: string
  eventId: string
  level: Level
  title: string
  hypothesis: string
  deadline: string
  status: 'collecting' | 'locked' | 'resolved'
  groundTruth: string
}

interface ModelAnswer {
  model: string
  answer: string
  confidence: number
  reason: string
  latencyMs: number
}

interface ExpertComment {
  id: string
  author: string
  content: string
}

interface ExpertAnswer {
  id: string
  expert: string
  answer: string
  reason: string
  comments: ExpertComment[]
}

interface QuestionComment {
  id: string
  author: string
  content: string
}

interface RankRow {
  model: string
  level: Level
  score: number
  avgLatency: number
  accuracy: number
}

interface BackendHealth {
  status: string
  database: boolean
}

interface BackendEventItem {
  id: string
  event_key: string
  content: string
  source_system: string
  credibility_level: number
  event_time: string
  filter_status: string
  trace_id: string
}

interface BackendQuestionItem {
  id: string
  event_id: string
  level: number
  content: string
  deadline: string
  status: string
  trace_id: string
}

interface BackendPage<T> {
  page: number
  page_size: number
  total: number
  items: T[]
}

const levels: Level[] = ['L1', 'L2', 'L3', 'L4']

const events = ref<EventItem[]>([
  {
    id: 'evt-001',
    codename: '铁砂行动',
    theater: '边境 A7 扇区',
    summary: '在争议走廊附近监测到补给车队改道。',
    severity: 'high',
    timestamp: '2026-03-08T05:20:00Z',
  },
  {
    id: 'evt-002',
    codename: '静港回波',
    theater: '沿海 C2 网格',
    summary: '未标绘海底通道出现异常声呐回波。',
    severity: 'medium',
    timestamp: '2026-03-09T13:15:00Z',
  },
  {
    id: 'evt-003',
    codename: '北境极光',
    theater: '极地中继枢纽',
    summary: '卫星丢包与风暴前沿及干扰信号同时出现。',
    severity: 'high',
    timestamp: '2026-03-10T01:45:00Z',
  },
])

const templateState = reactive<Record<Level, TemplateItem>>({
  L1: {
    level: 'L1',
    objective: '识别未来 24 小时的趋势方向。',
    constraints: '最多使用 3 个可观测因子，并说明因果关系。',
    outputFormat: '单行预测 + 置信度 + 触发条件。',
    qualityRule: '结论必须可证伪且具备明确时间边界。',
  },
  L2: {
    level: 'L2',
    objective: '估计未来 72 小时战术机动发生概率。',
    constraints: '包含一个替代场景并标注不确定性来源。',
    outputFormat: '概率区间 + 时间线 + 关键依赖。',
    qualityRule: '禁止使用“可能/大概”等无数值范围的模糊表达。',
  },
  L3: {
    level: 'L3',
    objective: '预测通信受扰条件下的作战影响。',
    constraints: '对比两个战略假设并给出证据权重。',
    outputFormat: '主假设 + 次假设 + 风险矩阵。',
    qualityRule: '推理链必须包含假设校验点。',
  },
  L4: {
    level: 'L4',
    objective: '评估多战区耦合下的战役级结果。',
    constraints: '建模长尾风险与二阶效应。',
    outputFormat: '结果分布 + 置信驱动因素 + 注意事项。',
    qualityRule: '必须提供供人工审阅的可解释说明。',
  },
})

const questions = ref<QuestionItem[]>([
  {
    id: 'q-101',
    eventId: 'evt-001',
    level: 'L2',
    title: 'A7 走廊车队流量会在 72 小时内上升吗？',
    hypothesis: '若流量持续上升 20%，可判定存在前置部署行为。',
    deadline: '2026-03-12T00:00:00Z',
    status: 'collecting',
    groundTruth: '待遥测数据复核。',
  },
  {
    id: 'q-102',
    eventId: 'evt-002',
    level: 'L1',
    title: '声呐异常会持续到下一个潮汐周期吗？',
    hypothesis: '若异常高于基线持续 18 小时，说明来源并非环境因素。',
    deadline: '2026-03-11T06:00:00Z',
    status: 'locked',
    groundTruth: '待信号归因报告。',
  },
  {
    id: 'q-103',
    eventId: 'evt-003',
    level: 'L3',
    title: '本周中继故障会使指挥吞吐降到 65% 以下吗？',
    hypothesis: '天气与干扰叠加可能导致吞吐持续下降。',
    deadline: '2026-03-15T12:00:00Z',
    status: 'resolved',
    groundTruth: '观测平均吞吐 61.7%，已确认跌破阈值。',
  },
])

const answersByQuestion = reactive<Record<string, ModelAnswer[]>>({
  'q-101': [
    {
      model: 'Aegis-7B',
      answer: '是，预计机动增幅约 +24%，置信度 0.71。',
      confidence: 71,
      reason: '历史上，油料补给峰值与路线去冲突通信常先于车队激增出现。',
      latencyMs: 1020,
    },
    {
      model: 'Falcon-13',
      answer: '增幅不确定，可能在 +8% 到 +18% 之间。',
      confidence: 58,
      reason: '信号存在冲突，天气扰动可能压缩可机动窗口。',
      latencyMs: 1440,
    },
  ],
  'q-102': [
    {
      model: 'Aegis-7B',
      answer: '异常会在最后一次潮位切换前衰减至基线以下。',
      confidence: 64,
      reason: '该模式更符合历史温跃层反射，不像主动平台运动。',
      latencyMs: 910,
    },
    {
      model: 'Orion-XL',
      answer: '预计会持续，但会间歇性掉线。',
      confidence: 67,
      reason: '频率谐波中存在人工脉冲间隔特征。',
      latencyMs: 1780,
    },
  ],
  'q-103': [
    {
      model: 'Falcon-13',
      answer: '吞吐可能降至 60-63%，并维持在低位。',
      confidence: 76,
      reason: '相关干扰脉冲与天气导致的中继不稳定时段高度重合。',
      latencyMs: 1260,
    },
    {
      model: 'Orion-XL',
      answer: '大约降至 68%，但 48 小时内可恢复。',
      confidence: 61,
      reason: '该判断基于备用路由快速切换且备链路稳定的前提。',
      latencyMs: 2010,
    },
  ],
})

const expertAnswersByQuestion = reactive<Record<string, ExpertAnswer[]>>({
  'q-103': [
    {
      id: 'exp-301',
      expert: '沃斯指挥官',
      answer: '在确认干扰源转移前，吞吐大概率持续劣化。',
      reason: '现场日志显示干扰节奏具有自适应性，能绕过标准回退时序。',
      comments: [
        {
          id: 'ec-1',
          author: '分析员伊姆兰',
          content: '同意节奏判断，能补充按天气单元划分的置信区间吗？',
        },
      ],
    },
  ],
})

const questionCommentsByQuestion = reactive<Record<string, QuestionComment[]>>({
  'q-101': [
    {
      id: 'qc-1',
      author: '行动联络官',
      content: '锁定该问题前，需要交叉核验走廊视频流。',
    },
  ],
  'q-103': [
    {
      id: 'qc-2',
      author: '风险小组',
      content: '真实结果已发布，请对模型分歧窗口做复盘。',
    },
  ],
})

const rankingRows = ref<RankRow[]>([
  { model: 'Aegis-7B', level: 'L1', score: 86.2, avgLatency: 940, accuracy: 82 },
  { model: 'Aegis-7B', level: 'L2', score: 84.1, avgLatency: 1010, accuracy: 79 },
  { model: 'Falcon-13', level: 'L2', score: 80.8, avgLatency: 1310, accuracy: 76 },
  { model: 'Falcon-13', level: 'L3', score: 83.5, avgLatency: 1240, accuracy: 78 },
  { model: 'Orion-XL', level: 'L1', score: 78.7, avgLatency: 1810, accuracy: 74 },
  { model: 'Orion-XL', level: 'L3', score: 77.2, avgLatency: 1960, accuracy: 70 },
  { model: 'Sentinel-R', level: 'L4', score: 75.9, avgLatency: 2210, accuracy: 68 },
])

const selectedEventId = ref(events.value[0]?.id ?? '')
const selectedLevel = ref<Level>('L1')
const selectedQuestionId = ref(questions.value[0]?.id ?? '')
const rankingLevel = ref<'ALL' | Level>('ALL')
const currentView = ref<AppView>('home')
const backendStatus = ref('后端未连接，当前使用模拟数据')
const backendOnline = ref(false)

const draftExpert = reactive({ name: '', answer: '', reason: '' })
const draftExpertComments = reactive<Record<string, string>>({})
const draftQuestionComment = ref('')
const draftEvent = reactive({ codename: '', theater: '', summary: '', severity: 'medium' as EventItem['severity'] })
const draftQuestion = reactive({ title: '', level: 'L2' as Level, deadline: '', status: 'collecting' as QuestionItem['status'] })

const selectedEvent = computed(() => events.value.find((eventItem) => eventItem.id === selectedEventId.value))
const selectedTemplate = computed(() => templateState[selectedLevel.value])
const selectedQuestion = computed(() => questions.value.find((question) => question.id === selectedQuestionId.value))

const filteredQuestions = computed(() =>
  questions.value.filter((question) => !selectedEventId.value || question.eventId === selectedEventId.value),
)
const previewEvents = computed(() =>
  [...events.value]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 3),
)

const selectedQuestionAnswers = computed(() => answersByQuestion[selectedQuestionId.value] ?? [])
const selectedExpertAnswers = computed(() => expertAnswersByQuestion[selectedQuestionId.value] ?? [])
const selectedQuestionComments = computed(() => questionCommentsByQuestion[selectedQuestionId.value] ?? [])
const dataSourceLabel = computed(() => (backendOnline.value ? '后端' : '模拟'))

const displayedRanking = computed(() => {
  const filtered =
    rankingLevel.value === 'ALL'
      ? rankingRows.value
      : rankingRows.value.filter((row) => row.level === rankingLevel.value)
  return [...filtered].sort((a, b) => b.score - a.score)
})

const statusLabel: Record<QuestionItem['status'], string> = {
  collecting: '收集中',
  locked: '已封存 / 待真实结果',
  resolved: '已解析',
}

const severityLabel: Record<EventItem['severity'], string> = {
  low: '低',
  medium: '中',
  high: '高',
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function selectEvent(id: string): void {
  selectedEventId.value = id
  const firstQuestion = questions.value.find((question) => question.eventId === id)
  if (firstQuestion) {
    selectedQuestionId.value = firstQuestion.id
  }
}

function saveTemplate(): void {
  const current = templateState[selectedLevel.value]
  templateState[selectedLevel.value] = {
    ...current,
    objective: current.objective.trim(),
    constraints: current.constraints.trim(),
    outputFormat: current.outputFormat.trim(),
    qualityRule: current.qualityRule.trim(),
  }
}

function addQuestionComment(): void {
  if (!selectedQuestionId.value || !draftQuestionComment.value.trim()) {
    return
  }
  const list = questionCommentsByQuestion[selectedQuestionId.value] ?? []
  list.push({
    id: `qc-${Date.now()}`,
    author: '审阅席',
    content: draftQuestionComment.value.trim(),
  })
  questionCommentsByQuestion[selectedQuestionId.value] = list
  draftQuestionComment.value = ''
}

function addExpertAnswer(): void {
  if (!selectedQuestionId.value || !draftExpert.name.trim() || !draftExpert.answer.trim() || !draftExpert.reason.trim()) {
    return
  }

  const list = expertAnswersByQuestion[selectedQuestionId.value] ?? []
  list.push({
    id: `exp-${Date.now()}`,
    expert: draftExpert.name.trim(),
    answer: draftExpert.answer.trim(),
    reason: draftExpert.reason.trim(),
    comments: [],
  })
  expertAnswersByQuestion[selectedQuestionId.value] = list

  draftExpert.name = ''
  draftExpert.answer = ''
  draftExpert.reason = ''
}

function addExpertComment(expertId: string): void {
  const content = (draftExpertComments[expertId] ?? '').trim()
  if (!content || !selectedQuestionId.value) {
    return
  }

  const list = expertAnswersByQuestion[selectedQuestionId.value] ?? []
  const target = list.find((item) => item.id === expertId)
  if (!target) {
    return
  }

  target.comments.push({
    id: `ec-${Date.now()}`,
    author: '同侪分析员',
    content,
  })
  draftExpertComments[expertId] = ''
}

function normalizeLevel(value: number): Level {
  if (value <= 1) {
    return 'L1'
  }
  if (value === 2) {
    return 'L2'
  }
  if (value === 3) {
    return 'L3'
  }
  return 'L4'
}

function severityFromCredibility(value: number): EventItem['severity'] {
  if (value >= 4) {
    return 'high'
  }
  if (value === 3) {
    return 'medium'
  }
  return 'low'
}

function credibilityFromSeverity(value: EventItem['severity']): number {
  if (value === 'high') {
    return 5
  }
  if (value === 'medium') {
    return 3
  }
  return 2
}

function levelToNumber(value: Level): number {
  if (value === 'L1') {
    return 1
  }
  if (value === 'L2') {
    return 2
  }
  if (value === 'L3') {
    return 3
  }
  return 4
}

function makeTraceId(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `${Date.now()}-${Math.random()}`
}

async function fetchJson<T>(path: string): Promise<T> {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || 'http://127.0.0.1:8000'
  const response = await fetch(`${base}${path}`)
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
  return (await response.json()) as T
}

async function sendJson<T>(path: string, method: 'POST' | 'PATCH' | 'DELETE', body: object): Promise<T> {
  const base = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || 'http://127.0.0.1:8000'
  const response = await fetch(`${base}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
  if (response.status === 204) {
    return {} as T
  }
  return (await response.json()) as T
}

async function createEvent(): Promise<void> {
  try {
    const codename = draftEvent.codename.trim()
    const theater = draftEvent.theater.trim()
    const summary = draftEvent.summary.trim()
    if (!codename || !theater || !summary) {
      backendStatus.value = '事件新增失败：请完整填写代号、来源和内容'
      return
    }

    if (!backendOnline.value) {
      const localId = `evt-local-${Date.now()}`
      events.value.unshift({
        id: localId,
        codename,
        theater,
        summary,
        severity: draftEvent.severity,
        timestamp: new Date().toISOString(),
      })
      selectedEventId.value = localId
      backendStatus.value = '后端离线：已在模拟数据中新增事件'
    } else {
      await sendJson<{ id: string }>('/events', 'POST', {
        event_key: codename,
        content: summary,
        source_system: theater,
        credibility_level: credibilityFromSeverity(draftEvent.severity),
        event_time: new Date().toISOString(),
        trace_id: makeTraceId(),
      })
      await hydrateFromBackend()
      backendStatus.value = '事件新增成功（后端）'
    }

    draftEvent.codename = ''
    draftEvent.theater = ''
    draftEvent.summary = ''
  } catch {
    backendStatus.value = '事件新增失败：请检查后端接口或参数格式'
  }
}

async function updateSelectedEvent(): Promise<void> {
  try {
    const current = selectedEvent.value
    if (!current) {
      return
    }

    if (!backendOnline.value) {
      backendStatus.value = '后端离线：当前仅支持模拟新增，不支持模拟更新'
      return
    }

    await sendJson(`/events/${current.id}`, 'PATCH', {
      content: current.summary,
      source_system: current.theater,
      credibility_level: credibilityFromSeverity(current.severity),
    })
    await hydrateFromBackend()
    backendStatus.value = '事件更新成功（后端）'
  } catch {
    backendStatus.value = '事件更新失败：请检查后端接口或参数格式'
  }
}

async function deleteSelectedEvent(): Promise<void> {
  try {
    const currentId = selectedEventId.value
    if (!currentId) {
      return
    }

    if (!backendOnline.value) {
      events.value = events.value.filter((item) => item.id !== currentId)
      questions.value = questions.value.filter((item) => item.eventId !== currentId)
      selectedEventId.value = events.value[0]?.id ?? ''
      selectedQuestionId.value = questions.value.find((item) => item.eventId === selectedEventId.value)?.id ?? ''
      backendStatus.value = '后端离线：已在模拟数据中删除事件及关联问题'
      return
    }

    await sendJson('/events', 'DELETE', { ids: [currentId] })
    await hydrateFromBackend()
    backendStatus.value = '事件删除成功（后端）'
  } catch {
    backendStatus.value = '事件删除失败：请检查后端接口或参数格式'
  }
}

async function createQuestion(): Promise<void> {
  try {
    const title = draftQuestion.title.trim()
    if (!selectedEventId.value || !title || !draftQuestion.deadline) {
      backendStatus.value = '问题新增失败：请选择事件并填写标题与截止时间'
      return
    }

    if (!backendOnline.value) {
      const localId = `q-local-${Date.now()}`
      questions.value.unshift({
        id: localId,
        eventId: selectedEventId.value,
        level: draftQuestion.level,
        title,
        hypothesis: '由人工创建，待补充假设。',
        deadline: draftQuestion.deadline,
        status: draftQuestion.status,
        groundTruth: '待真实结果回填。',
      })
      selectedQuestionId.value = localId
      backendStatus.value = '后端离线：已在模拟数据中新增问题'
      draftQuestion.title = ''
      return
    }

    await sendJson<{ id: string }>('/questions', 'POST', {
      event_id: selectedEventId.value,
      level: levelToNumber(draftQuestion.level),
      content: title,
      deadline: draftQuestion.deadline,
      trace_id: makeTraceId(),
    })
    await hydrateFromBackend()
    backendStatus.value = '问题新增成功（后端）'
    draftQuestion.title = ''
  } catch {
    backendStatus.value = '问题新增失败：请检查后端接口或参数格式'
  }
}

async function updateSelectedQuestion(): Promise<void> {
  try {
    const current = selectedQuestion.value
    if (!current) {
      return
    }

    if (!backendOnline.value) {
      backendStatus.value = '后端离线：当前仅支持模拟新增，不支持模拟更新'
      return
    }

    await sendJson(`/questions/${current.id}`, 'PATCH', {
      content: current.title,
      deadline: current.deadline,
      status: current.status,
    })
    await hydrateFromBackend()
    backendStatus.value = '问题更新成功（后端）'
  } catch {
    backendStatus.value = '问题更新失败：请检查后端接口或参数格式'
  }
}

async function deleteSelectedQuestion(): Promise<void> {
  try {
    const currentId = selectedQuestionId.value
    if (!currentId) {
      return
    }

    if (!backendOnline.value) {
      questions.value = questions.value.filter((item) => item.id !== currentId)
      selectedQuestionId.value = questions.value.find((item) => item.eventId === selectedEventId.value)?.id ?? ''
      backendStatus.value = '后端离线：已在模拟数据中删除问题'
      return
    }

    await sendJson('/questions', 'DELETE', { ids: [currentId] })
    await hydrateFromBackend()
    backendStatus.value = '问题删除成功（后端）'
  } catch {
    backendStatus.value = '问题删除失败：请检查后端接口或参数格式'
  }
}

async function hydrateFromBackend(): Promise<void> {
  try {
    const health = await fetchJson<BackendHealth>('/health')
    backendOnline.value = health.database
    if (!health.database) {
      backendStatus.value = '后端在线但数据库不可用，继续使用模拟数据'
      return
    }

    const [eventResult, questionResult] = await Promise.allSettled([
      fetchJson<BackendPage<BackendEventItem>>('/events?page=1&page_size=3'),
      fetchJson<BackendPage<BackendQuestionItem>>('/questions?page=1&page_size=100'),
    ])

    const loadedParts: string[] = []

    if (eventResult.status === 'fulfilled' && eventResult.value.items.length > 0) {
      const mappedEvents: EventItem[] = eventResult.value.items.map((item) => ({
        id: item.id,
        codename: item.event_key,
        theater: item.source_system,
        summary: item.content,
        severity: severityFromCredibility(item.credibility_level),
        timestamp: item.event_time,
      }))
      events.value = mappedEvents
      selectedEventId.value = mappedEvents[0]?.id ?? selectedEventId.value
      loadedParts.push(`事件 ${mappedEvents.length} 条`)
    }

    if (questionResult.status === 'fulfilled' && questionResult.value.items.length > 0) {
      const mappedQuestions: QuestionItem[] = questionResult.value.items.map((item) => ({
        id: item.id,
        eventId: item.event_id,
        level: normalizeLevel(item.level),
        title: item.content,
        hypothesis: '由后端问题内容导入，待补充可证伪假设。',
        deadline: item.deadline,
        status: item.status === 'resolved' ? 'resolved' : item.status === 'locked' ? 'locked' : 'collecting',
        groundTruth: item.status === 'resolved' ? '后端状态显示已解析，请补充真实结果详情。' : '待真实结果回填。',
      }))
      questions.value = mappedQuestions
      const firstQuestion = mappedQuestions.find((question) => question.eventId === selectedEventId.value)
      selectedQuestionId.value = firstQuestion?.id ?? mappedQuestions[0]?.id ?? selectedQuestionId.value
      loadedParts.push(`问题 ${mappedQuestions.length} 条`)
    }

    if (loadedParts.length === 0) {
      backendStatus.value = '后端已连接，但当前接口未返回可展示数据，继续使用模拟数据'
      return
    }

    backendStatus.value = `后端已连接：已载入 ${loadedParts.join('，')}`
  } catch {
    backendStatus.value = '后端连接失败，已自动回退模拟数据'
    backendOnline.value = false
  }
}

onMounted(() => {
  void hydrateFromBackend()
})
</script>

<template>
  <div class="mission-shell">
    <header class="topbar panel">
      <div>
        <p class="eyebrow">MOPPA 战术控制台</p>
        <h1>模型预测指挥甲板</h1>
      </div>
      <div class="status-pills">
        <span class="chip">数据源：{{ dataSourceLabel }}</span>
        <span class="chip">模式：训练沙盘</span>
        <span class="chip">后端状态：{{ backendOnline ? '在线' : '离线' }}</span>
      </div>
    </header>

    <section class="panel">
      <div class="panel-head">
        <h2>后端接入状态</h2>
        <span>/health + /events + /questions</span>
      </div>
      <p>{{ backendStatus }}</p>
    </section>

    <section class="panel nav-panel">
      <div class="view-switch">
        <button :class="['level-btn', { active: currentView === 'home' }]" @click="currentView = 'home'">首页总览</button>
        <button :class="['level-btn', { active: currentView === 'events' }]" @click="currentView = 'events'">事件管理</button>
        <button :class="['level-btn', { active: currentView === 'questions' }]" @click="currentView = 'questions'">问题管理</button>
      </div>
    </section>

    <main v-if="currentView === 'home'" class="layout-grid">
      <section class="left-column">
        <article class="panel">
          <div class="panel-head">
            <h2>1) 事件监看</h2>
            <span>首页仅展示最新 3 条</span>
          </div>
          <ul class="event-list">
            <li
              v-for="eventItem in previewEvents"
              :key="eventItem.id"
              :class="['event-card', { active: eventItem.id === selectedEventId }]"
              @click="selectEvent(eventItem.id)"
            >
              <div class="row-between">
                <strong>{{ eventItem.codename }}</strong>
                <span class="badge">{{ severityLabel[eventItem.severity] }}</span>
              </div>
              <p>{{ eventItem.theater }}</p>
              <small>{{ eventItem.summary }}</small>
              <span class="time">{{ formatDate(eventItem.timestamp) }}</span>
            </li>
          </ul>
        </article>

        <article class="panel">
          <div class="panel-head">
            <h2>2) 模板配置</h2>
            <span>按等级</span>
          </div>
          <div class="level-switch">
            <button
              v-for="level in levels"
              :key="level"
              :class="['level-btn', { active: level === selectedLevel }]"
              @click="selectedLevel = level"
            >
              {{ level }}
            </button>
          </div>

          <div class="field-block">
            <label>目标</label>
            <textarea v-model="selectedTemplate.objective" rows="2"></textarea>
          </div>
          <div class="field-block">
            <label>约束</label>
            <textarea v-model="selectedTemplate.constraints" rows="2"></textarea>
          </div>
          <div class="field-block">
            <label>输出格式</label>
            <textarea v-model="selectedTemplate.outputFormat" rows="2"></textarea>
          </div>
          <div class="field-block">
            <label>质量规则</label>
            <textarea v-model="selectedTemplate.qualityRule" rows="2"></textarea>
          </div>
          <button class="action-btn" @click="saveTemplate">保存模板（模拟）</button>
        </article>

        <article class="panel">
          <div class="panel-head">
            <h2>5) 模型排行榜</h2>
            <span>等级筛选</span>
          </div>
          <div class="level-switch">
            <button
              :class="['level-btn', { active: rankingLevel === 'ALL' }]"
              @click="rankingLevel = 'ALL'"
            >
              全部
            </button>
            <button
              v-for="level in levels"
              :key="`rank-${level}`"
              :class="['level-btn', { active: rankingLevel === level }]"
              @click="rankingLevel = level"
            >
              {{ level }}
            </button>
          </div>

          <div class="rank-table">
            <div class="rank-head">
              <span>模型</span>
              <span>分数</span>
              <span>准确率%</span>
              <span>耗时</span>
            </div>
            <div v-for="row in displayedRanking" :key="`${row.model}-${row.level}`" class="rank-row">
              <span>{{ row.model }} ({{ row.level }})</span>
              <span>{{ row.score.toFixed(1) }}</span>
              <span>{{ row.accuracy }}</span>
              <span>{{ row.avgLatency }}ms</span>
            </div>
          </div>
        </article>
      </section>

      <section class="right-column">
        <article class="panel">
          <div class="panel-head">
            <h2>3) 自动生成问题</h2>
            <span>{{ selectedEvent?.codename ?? '未选择事件' }}</span>
          </div>
          <div class="question-grid">
            <div
              v-for="question in filteredQuestions"
              :key="question.id"
              :class="['question-card', { active: question.id === selectedQuestionId }]"
              @click="selectedQuestionId = question.id"
            >
              <div class="row-between">
                <strong>{{ question.level }}</strong>
                <span class="status">{{ statusLabel[question.status] }}</span>
              </div>
              <p>{{ question.title }}</p>
              <small>截止时间：{{ formatDate(question.deadline) }}</small>
            </div>
          </div>
        </article>

        <article v-if="selectedQuestion" class="panel">
          <div class="panel-head">
            <h2>6) 问题详情</h2>
            <span>{{ selectedQuestion.id }}</span>
          </div>

          <div class="detail-block">
            <h3>{{ selectedQuestion.title }}</h3>
            <p>{{ selectedQuestion.hypothesis }}</p>
            <p class="truth">真实结果：{{ selectedQuestion.groundTruth }}</p>
          </div>

          <div class="split-grid">
            <section class="subpanel">
              <h3>4) 模型答案与分析</h3>
              <div v-for="item in selectedQuestionAnswers" :key="item.model" class="answer-card">
                <div class="row-between">
                  <strong>{{ item.model }}</strong>
                  <span>置信度 {{ item.confidence }}%</span>
                </div>
                <p>{{ item.answer }}</p>
                <small>原因：{{ item.reason }}</small>
                <span class="time">推理耗时：{{ item.latencyMs }}ms</span>
              </div>
            </section>

            <section class="subpanel">
              <h3>7) 专家答案与互评</h3>
              <div class="expert-inputs">
                <input v-model="draftExpert.name" placeholder="专家姓名" />
                <textarea v-model="draftExpert.answer" rows="2" placeholder="专家答案"></textarea>
                <textarea v-model="draftExpert.reason" rows="3" placeholder="专家推理过程"></textarea>
                <button class="action-btn" @click="addExpertAnswer">提交专家答案</button>
              </div>

              <div v-for="expert in selectedExpertAnswers" :key="expert.id" class="answer-card">
                <strong>{{ expert.expert }}</strong>
                <p>{{ expert.answer }}</p>
                <small>推理：{{ expert.reason }}</small>

                <div class="comment-list">
                  <p v-for="comment in expert.comments" :key="comment.id">
                    <span>{{ comment.author }}:</span> {{ comment.content }}
                  </p>
                </div>
                <div class="inline-comment">
                  <input
                    v-model="draftExpertComments[expert.id]"
                    placeholder="对该专家分析发表评论"
                  />
                  <button @click="addExpertComment(expert.id)">回复</button>
                </div>
              </div>
            </section>
          </div>

          <section class="subpanel">
            <h3>8) 问题讨论区</h3>
            <div class="comment-list">
              <p v-for="comment in selectedQuestionComments" :key="comment.id">
                <span>{{ comment.author }}:</span> {{ comment.content }}
              </p>
            </div>
            <div class="inline-comment">
              <input v-model="draftQuestionComment" placeholder="添加问题级评论" />
              <button @click="addQuestionComment">发布</button>
            </div>
          </section>
        </article>
      </section>
    </main>

    <main v-if="currentView === 'events'" class="manage-grid">
      <article class="panel">
        <div class="panel-head">
          <h2>事件列表</h2>
          <span>{{ events.length }} 条</span>
        </div>
        <ul class="event-list">
          <li
            v-for="eventItem in events"
            :key="`manage-${eventItem.id}`"
            :class="['event-card', { active: eventItem.id === selectedEventId }]"
            @click="selectEvent(eventItem.id)"
          >
            <div class="row-between">
              <strong>{{ eventItem.codename }}</strong>
              <span class="badge">{{ severityLabel[eventItem.severity] }}</span>
            </div>
            <p>{{ eventItem.theater }}</p>
            <small>{{ eventItem.summary }}</small>
          </li>
        </ul>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>新增事件</h2>
          <span>支持后端写入</span>
        </div>
        <div class="field-block">
          <label>事件代号</label>
          <input v-model="draftEvent.codename" placeholder="例如：海隼预警" />
        </div>
        <div class="field-block">
          <label>来源系统 / 战区</label>
          <input v-model="draftEvent.theater" placeholder="例如：边境雷达站" />
        </div>
        <div class="field-block">
          <label>事件内容</label>
          <textarea v-model="draftEvent.summary" rows="3" placeholder="填写事件摘要"></textarea>
        </div>
        <div class="field-block">
          <label>可信等级映射</label>
          <select v-model="draftEvent.severity">
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
          </select>
        </div>
        <button class="action-btn" @click="createEvent">新增事件</button>
      </article>

      <article class="panel" v-if="selectedEvent">
        <div class="panel-head">
          <h2>编辑事件</h2>
          <span>{{ selectedEvent.id }}</span>
        </div>
        <div class="field-block">
          <label>事件代号</label>
          <input v-model="selectedEvent.codename" />
        </div>
        <div class="field-block">
          <label>来源系统 / 战区</label>
          <input v-model="selectedEvent.theater" />
        </div>
        <div class="field-block">
          <label>事件内容</label>
          <textarea v-model="selectedEvent.summary" rows="3"></textarea>
        </div>
        <div class="field-block">
          <label>可信等级映射</label>
          <select v-model="selectedEvent.severity">
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
          </select>
        </div>
        <div class="action-row">
          <button class="action-btn" @click="updateSelectedEvent">保存修改</button>
          <button class="action-btn danger" @click="deleteSelectedEvent">删除事件</button>
        </div>
      </article>
    </main>

    <main v-if="currentView === 'questions'" class="manage-grid">
      <article class="panel">
        <div class="panel-head">
          <h2>问题列表</h2>
          <span>{{ questions.length }} 条</span>
        </div>
        <ul class="event-list">
          <li
            v-for="question in questions"
            :key="`manage-${question.id}`"
            :class="['question-card', { active: question.id === selectedQuestionId }]"
            @click="selectedQuestionId = question.id"
          >
            <div class="row-between">
              <strong>{{ question.level }}</strong>
              <span class="status">{{ statusLabel[question.status] }}</span>
            </div>
            <p>{{ question.title }}</p>
            <small>事件ID：{{ question.eventId }}</small>
          </li>
        </ul>
      </article>

      <article class="panel">
        <div class="panel-head">
          <h2>新增问题</h2>
          <span>支持后端写入</span>
        </div>
        <div class="field-block">
          <label>绑定事件</label>
          <select v-model="selectedEventId">
            <option v-for="eventItem in events" :key="`question-target-${eventItem.id}`" :value="eventItem.id">
              {{ eventItem.codename }} ({{ eventItem.id }})
            </option>
          </select>
        </div>
        <div class="field-block">
          <label>问题标题</label>
          <input v-model="draftQuestion.title" placeholder="输入预测问题" />
        </div>
        <div class="field-block">
          <label>问题等级</label>
          <select v-model="draftQuestion.level">
            <option v-for="level in levels" :key="`new-question-${level}`" :value="level">{{ level }}</option>
          </select>
        </div>
        <div class="field-block">
          <label>截止时间（ISO）</label>
          <input v-model="draftQuestion.deadline" placeholder="2026-03-20T12:00:00Z" />
        </div>
        <div class="field-block">
          <label>初始状态</label>
          <select v-model="draftQuestion.status">
            <option value="collecting">收集中</option>
            <option value="locked">已封存</option>
            <option value="resolved">已解析</option>
          </select>
        </div>
        <button class="action-btn" @click="createQuestion">新增问题</button>
      </article>

      <article class="panel" v-if="selectedQuestion">
        <div class="panel-head">
          <h2>编辑问题</h2>
          <span>{{ selectedQuestion.id }}</span>
        </div>
        <div class="field-block">
          <label>问题标题</label>
          <input v-model="selectedQuestion.title" />
        </div>
        <div class="field-block">
          <label>截止时间（ISO）</label>
          <input v-model="selectedQuestion.deadline" />
        </div>
        <div class="field-block">
          <label>状态</label>
          <select v-model="selectedQuestion.status">
            <option value="collecting">收集中</option>
            <option value="locked">已封存</option>
            <option value="resolved">已解析</option>
          </select>
        </div>
        <div class="action-row">
          <button class="action-btn" @click="updateSelectedQuestion">保存修改</button>
          <button class="action-btn danger" @click="deleteSelectedQuestion">删除问题</button>
        </div>
      </article>
    </main>
  </div>
</template>
