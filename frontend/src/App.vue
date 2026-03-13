<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import ManageDataSourcesPanel from './components/ManageDataSourcesPanel.vue'
import ManageEventsPanel from './components/ManageEventsPanel.vue'
import ManageFilterRulesPanel from './components/ManageFilterRulesPanel.vue'
import ManageQuestionsPanel from './components/ManageQuestionsPanel.vue'
import ManageTasksPanel from './components/ManageTasksPanel.vue'
import ManageTemplatesPanel from './components/ManageTemplatesPanel.vue'
import QuestionFeedPanel from './components/QuestionFeedPanel.vue'
import SidebarNav from './components/SidebarNav.vue'
import TopbarPanel from './components/TopbarPanel.vue'

type Level = 'L1' | 'L2' | 'L3' | 'L4'
type AppView = 'home' | 'events' | 'questions' | 'questionStream' | 'templates' | 'tasks' | 'dataSources' | 'filterRules'
type ToastKind = 'success' | 'error' | 'info'

interface ToastItem {
  id: number
  kind: ToastKind
  message: string
}

interface EventItem {
  id: string
  codename: string
  title: string
  theater: string
  summary: string
  tags: string[]
  severity: 'low' | 'medium' | 'high'
  filterStatus: string
  timestamp: string
}

interface QuestionItem {
  id: string
  eventIds: string[]
  level: Level
  title: string
  answerSpace: string
  hypothesis: string
  deadline: string
  status: 'collecting' | 'locked' | 'resolved'
  groundTruth: string
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

interface AuthUser {
  id: string
  username: string
  role: string
  is_active: boolean
}

interface AuthLoginApiResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: AuthUser
}

interface BackendEventItem {
  id: string
  event_key: string
  title: string
  content: string
  source_system: string
  credibility_level: number
  event_time: string
  tags: string[]
  filter_status: string
  trace_id: string
}

interface BackendQuestionItem {
  id: string
  event_id?: string
  event_ids?: string[]
  level: number
  content: string
  answer_space?: string | null
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

interface TaskItem {
  id: string
  taskType: string
  idempotencyKey: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'dead_letter'
  attemptCount: number
  traceId: string
}

interface BackendTaskItem {
  id: string
  task_type: string
  idempotency_key: string
  status: TaskItem['status']
  attempt_count: number
  trace_id: string
}

interface S1TaskResponse {
  task_id: string
  status: string
  result: Record<string, unknown>
}

interface S1JobDetail {
  task_id: string
  task_type: string
  idempotency_key: string
  status: string
  attempt_count: number
  result: Record<string, unknown>
  metrics: Record<string, unknown>
  error_message: string | null
  next_retry_at: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
  trace_id: string
}

interface DataSourceItem {
  id: string
  name: string
  sourceSystem: string
  sourceType: 'api' | 'database' | 'file' | 'websocket'
  connectionConfig: Record<string, unknown>
  secretRef: string | null
  credibilityLevel: number
  syncFrequency: string
  isActive: boolean
  version: string
  createdAt: string
  updatedAt: string
}

interface BackendDataSourceItem {
  id: string
  name: string
  source_system: string
  source_type: DataSourceItem['sourceType']
  connection_config: Record<string, unknown>
  secret_ref: string | null
  credibility_level: number
  sync_frequency: string
  is_active: boolean
  version: string
  created_at: string
  updated_at: string
}

interface FilterRuleItem {
  id: string
  name: string
  level: number
  ruleScope: 'db_import' | 'scrapy' | 'document' | 'use' | 'other'
  filterExpression: string
  filterPrompts: string[]
  filterConfig: Record<string, unknown>
  priority: number
  status: 'active' | 'inactive' | 'archived'
  version: string
  createdAt: string
  updatedAt: string
}

interface BackendFilterRuleItem {
  id: string
  name: string
  level: number
  rule_scope: FilterRuleItem['ruleScope']
  filter_expression: string
  filter_prompts: string[]
  filter_config: Record<string, unknown>
  priority: number
  status: FilterRuleItem['status']
  version: string
  created_at: string
  updated_at: string
}

interface QuestionTemplateItem {
  id: string
  questionTemplate: string
  majorTopic: string
  minorTopic: string
  difficultyLevel: Level
  constructionRationale: string
  candidateAnswers: string
  answerDeadline: string
  status: 'active' | 'inactive' | 'archived'
  version: string
  usageCount: number
  createdAt: string
  updatedAt: string
}

interface BackendQuestionTemplateItem {
  id: string
  question_template: string
  major_topic: string
  minor_topic: string
  difficulty_level: Level
  construction_rationale: string
  candidate_answers: string
  answer_deadline: string
  status: QuestionTemplateItem['status']
  version: string
  usage_count: number
  created_at: string
  updated_at: string
}

const levels: Level[] = ['L1', 'L2', 'L3', 'L4']
const filterRuleScopes: FilterRuleItem['ruleScope'][] = ['db_import', 'scrapy', 'document', 'use', 'other']
const eventManagePageSizeOptions = [5, 10, 20, 50, 100]

const homeEvents = ref<EventItem[]>([
  {
    id: 'evt-001',
    codename: '铁砂行动',
    title: '边境补给车队改道异常',
    theater: '边境 A7 扇区',
    summary: '在争议走廊附近监测到补给车队改道。',
    tags: ['大国博弈与战略竞争'],
    severity: 'high',
    filterStatus: 'passed',
    timestamp: '2026-03-08T05:20:00Z',
  },
  {
    id: 'evt-002',
    codename: '静港回波',
    title: '未标绘海底通道声呐异常',
    theater: '沿海 C2 网格',
    summary: '未标绘海底通道出现异常声呐回波。',
    tags: [],
    severity: 'medium',
    filterStatus: 'pending',
    timestamp: '2026-03-09T13:15:00Z',
  },
  {
    id: 'evt-003',
    codename: '北境极光',
    title: '极地中继丢包与干扰并发',
    theater: '极地中继枢纽',
    summary: '卫星丢包与风暴前沿及干扰信号同时出现。',
    tags: ['亚太军事与安全'],
    severity: 'high',
    filterStatus: 'filtered',
    timestamp: '2026-03-10T01:45:00Z',
  },
])

const questions = ref<QuestionItem[]>([
  {
    id: 'q-101',
    eventIds: ['evt-001'],
    level: 'L2',
    title: 'A7 走廊车队流量会在 72 小时内上升吗？',
    answerSpace: '会上升\n不会上升\n不确定',
    hypothesis: '若流量持续上升 20%，可判定存在前置部署行为。',
    deadline: '2026-03-12T00:00:00Z',
    status: 'collecting',
    groundTruth: '待遥测数据复核。',
  },
  {
    id: 'q-102',
    eventIds: ['evt-002'],
    level: 'L1',
    title: '声呐异常会持续到下一个潮汐周期吗？',
    answerSpace: '会\n不会',
    hypothesis: '若异常高于基线持续 18 小时，说明来源并非环境因素。',
    deadline: '2026-03-11T06:00:00Z',
    status: 'locked',
    groundTruth: '待信号归因报告。',
  },
  {
    id: 'q-103',
    eventIds: ['evt-003'],
    level: 'L3',
    title: '本周中继故障会使指挥吞吐降到 65% 以下吗？',
    answerSpace: '',
    hypothesis: '天气与干扰叠加可能导致吞吐持续下降。',
    deadline: '2026-03-15T12:00:00Z',
    status: 'resolved',
    groundTruth: '观测平均吞吐 61.7%，已确认跌破阈值。',
  },
])

const rankingRows = ref<RankRow[]>([
  { model: 'Aegis-7B', level: 'L1', score: 86.2, avgLatency: 940, accuracy: 82 },
  { model: 'Aegis-7B', level: 'L2', score: 84.1, avgLatency: 1010, accuracy: 79 },
  { model: 'Falcon-13', level: 'L2', score: 80.8, avgLatency: 1310, accuracy: 76 },
  { model: 'Falcon-13', level: 'L3', score: 83.5, avgLatency: 1240, accuracy: 78 },
  { model: 'Orion-XL', level: 'L1', score: 78.7, avgLatency: 1810, accuracy: 74 },
  { model: 'Orion-XL', level: 'L3', score: 77.2, avgLatency: 1960, accuracy: 70 },
  { model: 'Sentinel-R', level: 'L4', score: 75.9, avgLatency: 2210, accuracy: 68 },
])

const selectedEventId = ref(homeEvents.value[0]?.id ?? '')
const selectedEventIdsForQuestion = ref<string[]>(selectedEventId.value ? [selectedEventId.value] : [])
const selectedQuestionId = ref(questions.value[0]?.id ?? '')
const rankingLevel = ref<'ALL' | Level>('ALL')
const currentView = ref<AppView>('home')
const backendStatus = ref('后端未连接，当前使用模拟数据')
const backendOnline = ref(false)
const authUser = ref<AuthUser | null>(null)
const authLoading = ref(false)
const authError = ref('')
const authDialogOpen = ref(false)
const authMode = ref<'login' | 'register'>('login')
const authAccessToken = ref(localStorage.getItem('moppa_access_token') ?? '')
const authRefreshToken = ref(localStorage.getItem('moppa_refresh_token') ?? '')
const authForm = reactive({ username: '', password: '', email: '' })
let authRefreshPromise: Promise<boolean> | null = null
const toasts = ref<ToastItem[]>([])
let toastSeed = 0

const draftEvent = reactive({ title: '', theater: '', summary: '', severity: 'medium' as EventItem['severity'] })
const draftQuestion = reactive({
  title: '',
  level: 'L2' as Level,
  deadline: '',
  status: 'collecting' as QuestionItem['status'],
  answerSpace: '',
})
const homeDetailEvent = ref<EventItem | null>(null)
const manageDetailEvent = ref<EventItem | null>(null)
const eventEditDialogOpen = ref(false)
const eventDetailDialogOpen = ref(false)
const homeDetailDialogOpen = ref(false)
const createEventDialogOpen = ref(false)
const createQuestionDialogOpen = ref(false)
const questionEventSearch = ref('')
const questionEditEventSearch = ref('')
const questionEventSearchLoading = ref(false)
const questionEventSearchTotal = ref(0)
const questionEventOptions = ref<EventItem[]>([])
const questionEventSearchSeq = ref(0)
let questionEventSearchTimer: number | undefined
const questionDetailDialogOpen = ref(false)
const questionEditDialogOpen = ref(false)
const templateEditDialogOpen = ref(false)
const templateDetailDialogOpen = ref(false)
const createTemplateDialogOpen = ref(false)
const eventEditForm = reactive({
  id: '',
  title: '',
  theater: '',
  summary: '',
  severity: 'medium' as EventItem['severity'],
  filterStatus: '',
})
const questionEditForm = reactive({
  id: '',
  title: '',
  level: 'L2' as Level,
  answerSpace: '',
  eventIds: [] as string[],
  deadline: '',
  status: 'collecting' as QuestionItem['status'],
})
const templateEditForm = reactive({
  id: '',
  questionTemplate: '',
  majorTopic: '',
  minorTopic: '',
  difficultyLevel: 'L2' as Level,
  constructionRationale: '',
  candidateAnswers: '',
  answerDeadline: '',
  status: 'active' as QuestionTemplateItem['status'],
  version: 'v1.0',
})
const createTemplateForm = reactive({
  questionTemplate: '',
  majorTopic: '',
  minorTopic: '',
  difficultyLevel: 'L2' as Level,
  constructionRationale: '',
  candidateAnswers: '',
  answerDeadline: '',
  status: 'active' as QuestionTemplateItem['status'],
  version: 'v1.0',
})
const selectedTemplate = ref<QuestionTemplateItem | null>(null)
const templates = ref<QuestionTemplateItem[]>([])
const templateManagePage = ref(1)
const templateManagePageSize = ref(6)
const templateManageJumpPage = ref('1')
const templateManageTotal = ref(0)
const templateManageSearchKeyword = ref('')
const selectedManageTemplateIds = ref<string[]>([])
const homeEventPage = ref(1)
const homeEventPageSize = 3
const homeEventTotal = ref(homeEvents.value.length)
const homeEventJumpPage = ref('1')
const eventManagePage = ref(1)
const eventManagePageSize = ref(10)
const eventManageJumpPage = ref('1')
const eventManageSearchKeyword = ref('')
const eventManageFilterStatus = ref('')
const eventManageTimeFrom = ref('')
const eventManageTimeTo = ref('')
const eventManageSearchLoading = ref(false)
const eventManageSearchSeq = ref(0)
let eventManageSearchTimer: number | undefined
const manageEvents = ref<EventItem[]>([])
const manageEventTotal = ref(0)
const selectedManageEventIds = ref<string[]>([])
const eventReviewProcessing = ref(false)
const questionManagePage = ref(1)
const questionManagePageSize = ref(6)
const questionManageJumpPage = ref('1')
const questionManageSearchKeyword = ref('')
const questionManageSearchLoading = ref(false)
const questionManageSearchSeq = ref(0)
let questionManageSearchTimer: number | undefined
const manageQuestions = ref<QuestionItem[]>([])
const questionManageTotal = ref(questions.value.length)
const questionFeedItems = ref<QuestionItem[]>([])
const questionFeedPage = ref(0)
const questionFeedTotal = ref(0)
const questionFeedLoading = ref(false)
const questionFeedHasMore = ref(true)
const selectedManageQuestionIds = ref<string[]>([])
const manageDetailQuestion = ref<QuestionItem | null>(null)
const tasks = ref<TaskItem[]>([])
const taskManagePage = ref(1)
const taskManagePageSize = ref(10)
const taskManageJumpPage = ref('1')
const taskManageTotal = ref(0)
const selectedManageTaskIds = ref<string[]>([])
const createTaskDialogOpen = ref(false)
const taskDetailDialogOpen = ref(false)
const triggerPullDialogOpen = ref(false)
const autoReviewProcessing = ref(false)
const selectedTask = ref<TaskItem | null>(null)
const selectedTaskDetail = ref<S1JobDetail | null>(null)
const createTaskForm = reactive({ taskType: 's1_ingest_pull', idempotencyKey: '', traceId: '' })
const triggerPullForm = reactive({ sourceSystem: '' })
const sourceSystemOptions = ref<string[]>([])
const dataSources = ref<DataSourceItem[]>([])
const dataSourceManagePage = ref(1)
const dataSourceManagePageSize = ref(10)
const dataSourceManageJumpPage = ref('1')
const dataSourceManageTotal = ref(0)
const selectedManageDataSourceIds = ref<string[]>([])
const selectedDataSource = ref<DataSourceItem | null>(null)
const dataSourceDetailDialogOpen = ref(false)
const createDataSourceDialogOpen = ref(false)
const editDataSourceDialogOpen = ref(false)
const createDataSourceForm = reactive({
  name: '',
  sourceSystem: '',
  sourceType: 'database' as DataSourceItem['sourceType'],
  connectionConfig: '{}',
  secretRef: '',
  credibilityLevel: 3,
  syncFrequency: '1 hour',
  isActive: true,
  version: 'v1.0',
})
const editDataSourceForm = reactive({
  id: '',
  name: '',
  sourceSystem: '',
  sourceType: 'database' as DataSourceItem['sourceType'],
  connectionConfig: '{}',
  secretRef: '',
  credibilityLevel: 3,
  syncFrequency: '1 hour',
  isActive: true,
  version: 'v1.0',
})
const filterRules = ref<FilterRuleItem[]>([])
const filterRuleManagePage = ref(1)
const filterRuleManagePageSize = ref(10)
const filterRuleManageJumpPage = ref('1')
const filterRuleManageTotal = ref(0)
const selectedManageFilterRuleIds = ref<string[]>([])
const selectedFilterRule = ref<FilterRuleItem | null>(null)
const filterRuleDetailDialogOpen = ref(false)
const createFilterRuleDialogOpen = ref(false)
const editFilterRuleDialogOpen = ref(false)
const createFilterRuleForm = reactive({
  name: '',
  level: 1,
  ruleScope: 'db_import' as FilterRuleItem['ruleScope'],
  filterExpression: 'keyword_exclude',
  filterPrompts: [''],
  filterConfigItems: [{ key: 'keywords', value: '["rumor"]' }],
  priority: 100,
  status: 'active' as FilterRuleItem['status'],
  version: 'v1.0',
})
const editFilterRuleForm = reactive({
  id: '',
  name: '',
  level: 1,
  ruleScope: 'db_import' as FilterRuleItem['ruleScope'],
  filterExpression: 'keyword_exclude',
  filterPrompts: [''],
  filterConfigItems: [{ key: '', value: '' }],
  priority: 0,
  status: 'active' as FilterRuleItem['status'],
  version: 'v1.0',
})

const selectedTemplateDetail = computed(() => selectedTemplate.value)
const isAuthenticated = computed(() => Boolean(authUser.value))
const isAdmin = computed(() => authUser.value?.role === 'admin')
const previewEvents = computed(() => homeEvents.value.filter((item) => item.filterStatus === 'passed'))
const homeEventTotalPages = computed(() => Math.max(1, Math.ceil(homeEventTotal.value / homeEventPageSize)))
const homeHasEvents = computed(() => previewEvents.value.length > 0)
const localFilteredManageEvents = computed(() => {
  const keyword = eventManageSearchKeyword.value.trim().toLowerCase()
  const status = eventManageFilterStatus.value.trim()
  const fromMs = parseLocalDateTimeToMs(eventManageTimeFrom.value)
  const toMs = parseLocalDateTimeToMs(eventManageTimeTo.value)
  return manageEvents.value.filter((item) => {
    if (status === 'reviewed') {
      if (!['passed', 'filtered'].includes(item.filterStatus)) {
        return false
      }
    } else if (status && item.filterStatus !== status) {
      return false
    }
    if (!keyword) {
      return true
    }
    const haystack = `${item.title}\n${item.summary}\n${item.theater}`.toLowerCase()
    if (keyword && !haystack.includes(keyword)) {
      return false
    }
    const eventMs = Date.parse(item.timestamp)
    if (fromMs !== null && Number.isFinite(eventMs) && eventMs < fromMs) {
      return false
    }
    if (toMs !== null && Number.isFinite(eventMs) && eventMs > toMs) {
      return false
    }
    return true
  })
})
const eventManageTotalPages = computed(() => {
  const total = backendOnline.value ? manageEventTotal.value : localFilteredManageEvents.value.length
  return Math.max(1, Math.ceil(total / eventManagePageSize.value))
})
const pagedManageEvents = computed(() => {
  if (backendOnline.value) {
    return manageEvents.value
  }
  const start = (eventManagePage.value - 1) * eventManagePageSize.value
  return localFilteredManageEvents.value.slice(start, start + eventManagePageSize.value)
})
const hasManageEvents = computed(() => pagedManageEvents.value.length > 0)
const allEventsOnPageSelected = computed(() =>
  pagedManageEvents.value.length > 0 && pagedManageEvents.value.every((item) => selectedManageEventIds.value.includes(item.id)),
)
const selectedManageEvents = computed(() =>
  manageEvents.value.filter((item) => selectedManageEventIds.value.includes(item.id)),
)
const selectedPendingManageEventIds = computed(() =>
  selectedManageEvents.value.filter((item) => item.filterStatus === 'pending').map((item) => item.id),
)

const localFilteredManageQuestions = computed(() => {
  const keyword = questionManageSearchKeyword.value.trim().toLowerCase()
  if (!keyword) {
    return questions.value
  }
  return questions.value.filter((item) => {
    const haystack = `${item.title}\n${item.hypothesis}\n${item.groundTruth}`.toLowerCase()
    return haystack.includes(keyword)
  })
})
const questionManageTotalPages = computed(() => {
  const total = backendOnline.value ? questionManageTotal.value : localFilteredManageQuestions.value.length
  return Math.max(1, Math.ceil(total / questionManagePageSize.value))
})
const pagedManageQuestions = computed(() => {
  if (backendOnline.value) {
    return manageQuestions.value
  }
  const start = (questionManagePage.value - 1) * questionManagePageSize.value
  return localFilteredManageQuestions.value.slice(start, start + questionManagePageSize.value)
})
const hasManageQuestions = computed(() => pagedManageQuestions.value.length > 0)
const allQuestionsOnPageSelected = computed(() =>
  pagedManageQuestions.value.length > 0 && pagedManageQuestions.value.every((item) => selectedManageQuestionIds.value.includes(item.id)),
)
const hasTemplates = computed(() => templates.value.length > 0)
const hasTasks = computed(() => tasks.value.length > 0)
const hasDataSources = computed(() => dataSources.value.length > 0)
const hasFilterRules = computed(() => filterRules.value.length > 0)

const templateManageTotalPages = computed(() => Math.max(1, Math.ceil(templateManageTotal.value / templateManagePageSize.value)))
const allTemplatesOnPageSelected = computed(
  () => templates.value.length > 0 && templates.value.every((item) => selectedManageTemplateIds.value.includes(item.id)),
)
const allKnownEvents = computed(() => {
  const map = new Map<string, EventItem>()
  for (const item of homeEvents.value) {
    map.set(item.id, item)
  }
  for (const item of manageEvents.value) {
    map.set(item.id, item)
  }
  for (const item of questionEventOptions.value) {
    map.set(item.id, item)
  }
  return Array.from(map.values())
})
const localFilteredKnownEventsForQuestion = computed(() => {
  const passedEvents = allKnownEvents.value.filter((item) => item.filterStatus === 'passed')
  const keyword = questionEventSearch.value.trim().toLowerCase()
  if (!keyword) {
    return passedEvents
  }
  return passedEvents.filter((item) => {
    const haystack = `${item.title}\n${item.summary}`.toLowerCase()
    return haystack.includes(keyword)
  })
})
const filteredKnownEventsForQuestion = computed(() =>
  backendOnline.value ? questionEventOptions.value : localFilteredKnownEventsForQuestion.value,
)
const filteredKnownEventsForQuestionEdit = computed(() => {
  const keyword = questionEditEventSearch.value.trim().toLowerCase()
  if (!keyword) {
    return allKnownEvents.value
  }
  return allKnownEvents.value.filter((item) => {
    const haystack = `${item.title}\n${item.theater}\n${item.summary}`.toLowerCase()
    return haystack.includes(keyword)
  })
})
const questionEventMatchedTotal = computed(() =>
  backendOnline.value ? questionEventSearchTotal.value : filteredKnownEventsForQuestion.value.length,
)
const taskManageTotalPages = computed(() => Math.max(1, Math.ceil(taskManageTotal.value / taskManagePageSize.value)))
const allTasksOnPageSelected = computed(
  () => tasks.value.length > 0 && tasks.value.every((item) => selectedManageTaskIds.value.includes(item.id)),
)
const dataSourceManageTotalPages = computed(
  () => Math.max(1, Math.ceil(dataSourceManageTotal.value / dataSourceManagePageSize.value)),
)
const allDataSourcesOnPageSelected = computed(
  () =>
    dataSources.value.length > 0 &&
    dataSources.value.every((item) => selectedManageDataSourceIds.value.includes(item.id)),
)
const filterRuleManageTotalPages = computed(
  () => Math.max(1, Math.ceil(filterRuleManageTotal.value / filterRuleManagePageSize.value)),
)
const allFilterRulesOnPageSelected = computed(
  () =>
    filterRules.value.length > 0 &&
    filterRules.value.every((item) => selectedManageFilterRuleIds.value.includes(item.id)),
)

const displayedRanking = computed(() => {
  const filtered =
    rankingLevel.value === 'ALL'
      ? rankingRows.value
      : rankingRows.value.filter((row) => row.level === rankingLevel.value)
  return [...filtered].sort((a, b) => b.score - a.score)
})
const hasDisplayedRanking = computed(() => displayedRanking.value.length > 0)
const totalEventCount = ref(0)
const pendingEventCount = ref(0)
const runningTaskCount = ref(0)
let topMetricRefreshTimer: number | undefined
const skeletonRows = [1, 2, 3, 4]

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

function severityBadgeTone(value: EventItem['severity']): string {
  if (value === 'high') {
    return 'badge-error'
  }
  if (value === 'medium') {
    return 'badge-warning'
  }
  return 'badge-info'
}

function eventFilterBadgeTone(status: string): string {
  if (status === 'passed') {
    return 'badge-success'
  }
  if (status === 'filtered') {
    return 'badge-error'
  }
  if (status === 'pending') {
    return 'badge-warning'
  }
  if (status === 'reviewed') {
    return 'badge-info'
  }
  return 'badge-muted'
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function toDateTimeLocalValue(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  const year = String(date.getFullYear())
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${year}-${month}-${day}T${hour}:${minute}`
}

function selectEvent(id: string): void {
  selectedEventId.value = id
  const firstQuestion = questions.value.find((question) => question.eventIds.includes(id))
  if (firstQuestion) {
    selectedQuestionId.value = firstQuestion.id
  }
}

function openHomeDetail(eventItem: EventItem): void {
  homeDetailEvent.value = eventItem
  homeDetailDialogOpen.value = true
}

function openManageDetail(eventItem: EventItem): void {
  selectedEventId.value = eventItem.id
  manageDetailEvent.value = eventItem
  eventDetailDialogOpen.value = true
}

function openEventEdit(eventItem: EventItem): void {
  void fetchSourceSystemOptions()
  selectedEventId.value = eventItem.id
  eventEditForm.id = eventItem.id
  eventEditForm.title = eventItem.title
  eventEditForm.theater = eventItem.theater
  eventEditForm.summary = eventItem.summary
  eventEditForm.severity = eventItem.severity
  eventEditForm.filterStatus = eventItem.filterStatus
  eventEditDialogOpen.value = true
}

function openManageQuestionDetail(questionItem: QuestionItem): void {
  selectedQuestionId.value = questionItem.id
  manageDetailQuestion.value = questionItem
  void ensureQuestionEventOptionsByIds(questionItem.eventIds)
  questionDetailDialogOpen.value = true
}

function openQuestionEdit(questionItem: QuestionItem): void {
  selectedQuestionId.value = questionItem.id
  questionEditEventSearch.value = ''
  questionEditForm.id = questionItem.id
  questionEditForm.title = questionItem.title
  questionEditForm.level = questionItem.level
  questionEditForm.answerSpace = questionItem.answerSpace
  questionEditForm.eventIds = [...questionItem.eventIds]
  questionEditForm.deadline = toDateTimeLocalValue(questionItem.deadline)
  questionEditForm.status = questionItem.status
  void ensureQuestionEventOptionsByIds(questionItem.eventIds)
  questionEditDialogOpen.value = true
}

function openCreateQuestionDialog(): void {
  questionEventSearch.value = ''
  selectedEventIdsForQuestion.value = selectedEventId.value ? [selectedEventId.value] : []
  createQuestionDialogOpen.value = true
  if (backendOnline.value) {
    void fetchQuestionEventOptions('')
  }
}

function closeCreateQuestionDialog(): void {
  if (questionEventSearchTimer !== undefined) {
    window.clearTimeout(questionEventSearchTimer)
    questionEventSearchTimer = undefined
  }
  questionEventSearchSeq.value += 1
  questionEventOptions.value = []
  questionEventSearchTotal.value = 0
  questionEventSearchLoading.value = false
  questionEventSearch.value = ''
  selectedEventIdsForQuestion.value = []
  createQuestionDialogOpen.value = false
}

function closeAllDialogs(): void {
  taskDetailDialogOpen.value = false
  createTaskDialogOpen.value = false
  triggerPullDialogOpen.value = false
  dataSourceDetailDialogOpen.value = false
  createDataSourceDialogOpen.value = false
  editDataSourceDialogOpen.value = false
  filterRuleDetailDialogOpen.value = false
  createFilterRuleDialogOpen.value = false
  editFilterRuleDialogOpen.value = false
  homeDetailDialogOpen.value = false
  eventDetailDialogOpen.value = false
  eventEditDialogOpen.value = false
  questionDetailDialogOpen.value = false
  questionEditDialogOpen.value = false
  templateDetailDialogOpen.value = false
  templateEditDialogOpen.value = false
  createTemplateDialogOpen.value = false
  createEventDialogOpen.value = false
  if (createQuestionDialogOpen.value) {
    closeCreateQuestionDialog()
  }
}

function hasAnyDialogOpen(): boolean {
  return (
    taskDetailDialogOpen.value ||
    createTaskDialogOpen.value ||
    triggerPullDialogOpen.value ||
    dataSourceDetailDialogOpen.value ||
    createDataSourceDialogOpen.value ||
    editDataSourceDialogOpen.value ||
    filterRuleDetailDialogOpen.value ||
    createFilterRuleDialogOpen.value ||
    editFilterRuleDialogOpen.value ||
    homeDetailDialogOpen.value ||
    eventDetailDialogOpen.value ||
    eventEditDialogOpen.value ||
    questionDetailDialogOpen.value ||
    questionEditDialogOpen.value ||
    templateDetailDialogOpen.value ||
    templateEditDialogOpen.value ||
    createTemplateDialogOpen.value ||
    createEventDialogOpen.value ||
    createQuestionDialogOpen.value
  )
}

function handleGlobalKeydown(event: KeyboardEvent): void {
  if (event.key !== 'Escape' || !hasAnyDialogOpen()) {
    return
  }
  event.preventDefault()
  closeAllDialogs()
}

function clearQuestionEventSearch(): void {
  questionEventSearch.value = ''
  if (backendOnline.value && createQuestionDialogOpen.value) {
    void fetchQuestionEventOptions('')
  }
}

function toggleQuestionEventSelection(eventId: string): void {
  if (selectedEventIdsForQuestion.value.includes(eventId)) {
    selectedEventIdsForQuestion.value = selectedEventIdsForQuestion.value.filter((id) => id !== eventId)
    return
  }
  selectedEventIdsForQuestion.value = [...selectedEventIdsForQuestion.value, eventId]
}

function toggleQuestionEditEventSelection(eventId: string): void {
  if (questionEditForm.eventIds.includes(eventId)) {
    questionEditForm.eventIds = questionEditForm.eventIds.filter((id) => id !== eventId)
    return
  }
  questionEditForm.eventIds = [...questionEditForm.eventIds, eventId]
}

async function submitCreateQuestionFromDialog(): Promise<void> {
  const before = draftQuestion.title
  await createQuestion()
  if (!draftQuestion.title && before.trim()) {
    closeCreateQuestionDialog()
  }
}

async function submitCreateEventFromDialog(): Promise<void> {
  const hadInputBeforeSubmit = [draftEvent.title, draftEvent.theater, draftEvent.summary].some((value) => value.trim())
  await createEvent()
  if (!draftEvent.title && !draftEvent.theater && !draftEvent.summary && hadInputBeforeSubmit) {
    createEventDialogOpen.value = false
  }
}

function toggleManageEventSelection(eventId: string): void {
  if (selectedManageEventIds.value.includes(eventId)) {
    selectedManageEventIds.value = selectedManageEventIds.value.filter((id) => id !== eventId)
    return
  }
  selectedManageEventIds.value = [...selectedManageEventIds.value, eventId]
}

function toggleSelectAllEventsOnPage(): void {
  if (allEventsOnPageSelected.value) {
    selectedManageEventIds.value = selectedManageEventIds.value.filter(
      (id) => !pagedManageEvents.value.some((item) => item.id === id),
    )
    return
  }

  const pageIds = pagedManageEvents.value.map((item) => item.id)
  selectedManageEventIds.value = Array.from(new Set([...selectedManageEventIds.value, ...pageIds]))
}

function setEventManagePageSize(size: number): void {
  eventManagePageSize.value = size
  eventManagePage.value = 1
  eventManageJumpPage.value = '1'
  selectedManageEventIds.value = []
  if (backendOnline.value) {
    void fetchManageEvents(1)
  }
}

function goToEventManagePage(page: number): void {
  if (page < 1 || page > eventManageTotalPages.value) {
    return
  }
  eventManagePage.value = page
  eventManageJumpPage.value = String(page)
  if (backendOnline.value) {
    void fetchManageEvents(page)
  }
}

function goHomeEventPage(delta: number): void {
  const next = homeEventPage.value + delta
  if (next < 1 || next > homeEventTotalPages.value) {
    return
  }
  if (backendOnline.value) {
    void fetchHomeEvents(next)
    return
  }
  homeEventPage.value = next
  homeEventJumpPage.value = String(next)
}

function jumpToHomeEventPageFromInput(): void {
  const page = Number(homeEventJumpPage.value)
  if (!Number.isFinite(page)) {
    return
  }
  const target = Math.min(Math.max(1, Math.trunc(page)), homeEventTotalPages.value)
  if (backendOnline.value) {
    void fetchHomeEvents(target)
    return
  }
  homeEventPage.value = target
  homeEventJumpPage.value = String(target)
}

function goManageEventPage(delta: number): void {
  const next = eventManagePage.value + delta
  if (next < 1 || next > eventManageTotalPages.value) {
    return
  }
  goToEventManagePage(next)
}

function toggleManageQuestionSelection(questionId: string): void {
  if (selectedManageQuestionIds.value.includes(questionId)) {
    selectedManageQuestionIds.value = selectedManageQuestionIds.value.filter((id) => id !== questionId)
    return
  }
  selectedManageQuestionIds.value = [...selectedManageQuestionIds.value, questionId]
}

function toggleSelectAllQuestionsOnPage(): void {
  if (allQuestionsOnPageSelected.value) {
    selectedManageQuestionIds.value = selectedManageQuestionIds.value.filter(
      (id) => !pagedManageQuestions.value.some((item) => item.id === id),
    )
    return
  }

  const pageIds = pagedManageQuestions.value.map((item) => item.id)
  selectedManageQuestionIds.value = Array.from(new Set([...selectedManageQuestionIds.value, ...pageIds]))
}

function setQuestionManagePageSize(size: number): void {
  questionManagePageSize.value = size
  questionManagePage.value = 1
  questionManageJumpPage.value = '1'
  selectedManageQuestionIds.value = []
  if (backendOnline.value) {
    void fetchManageQuestions(1)
  }
}

function goManageQuestionPage(delta: number): void {
  const next = questionManagePage.value + delta
  if (next < 1 || next > questionManageTotalPages.value) {
    return
  }
  goToQuestionManagePage(next)
}

function goToQuestionManagePage(page: number): void {
  if (page < 1 || page > questionManageTotalPages.value) {
    return
  }
  questionManagePage.value = page
  questionManageJumpPage.value = String(page)
  selectedManageQuestionIds.value = []
  if (backendOnline.value) {
    void fetchManageQuestions(page)
  }
}

function jumpToEventPageFromInput(): void {
  const page = Number(eventManageJumpPage.value)
  if (!Number.isFinite(page)) {
    return
  }
  goToEventManagePage(Math.min(Math.max(1, Math.trunc(page)), eventManageTotalPages.value))
}

function jumpToQuestionPageFromInput(): void {
  const page = Number(questionManageJumpPage.value)
  if (!Number.isFinite(page)) {
    return
  }
  goToQuestionManagePage(Math.min(Math.max(1, Math.trunc(page)), questionManageTotalPages.value))
}

function openTaskDetail(task: TaskItem): void {
  selectedTask.value = task
  taskDetailDialogOpen.value = true
  void fetchTaskDetail(task.id)
}

function toggleManageTaskSelection(taskId: string): void {
  if (selectedManageTaskIds.value.includes(taskId)) {
    selectedManageTaskIds.value = selectedManageTaskIds.value.filter((id) => id !== taskId)
    return
  }
  selectedManageTaskIds.value = [...selectedManageTaskIds.value, taskId]
}

function toggleSelectAllTasksOnPage(): void {
  if (allTasksOnPageSelected.value) {
    selectedManageTaskIds.value = []
    return
  }
  selectedManageTaskIds.value = tasks.value.map((item) => item.id)
}

function setTaskManagePageSize(size: number): void {
  taskManagePageSize.value = size
  taskManagePage.value = 1
  taskManageJumpPage.value = '1'
  selectedManageTaskIds.value = []
  if (backendOnline.value) {
    void fetchTasks(1)
  }
}

function goTaskManagePage(delta: number): void {
  const next = taskManagePage.value + delta
  if (next < 1 || next > taskManageTotalPages.value) {
    return
  }
  goToTaskManagePage(next)
}

function goToTaskManagePage(page: number): void {
  if (page < 1 || page > taskManageTotalPages.value) {
    return
  }
  taskManagePage.value = page
  taskManageJumpPage.value = String(page)
  selectedManageTaskIds.value = []
  if (backendOnline.value) {
    void fetchTasks(page)
  }
}

function jumpToTaskPageFromInput(): void {
  const page = Number(taskManageJumpPage.value)
  if (!Number.isFinite(page)) {
    return
  }
  goToTaskManagePage(Math.min(Math.max(1, Math.trunc(page)), taskManageTotalPages.value))
}

async function fetchTasks(page = 1): Promise<void> {
  const pageData = await fetchJson<BackendPage<BackendTaskItem>>(`/tasks?page=${page}&page_size=${taskManagePageSize.value}`)
  tasks.value = pageData.items.map(toTaskItem)
  taskManageTotal.value = pageData.total
  taskManagePage.value = pageData.page
  taskManageJumpPage.value = String(pageData.page)
  selectedManageTaskIds.value = []
}

async function fetchTaskDetail(taskId: string): Promise<void> {
  try {
    selectedTaskDetail.value = await fetchJson<S1JobDetail>(`/s1/jobs/${taskId}`)
  } catch {
    const basic = await fetchJson<BackendTaskItem>(`/tasks/${taskId}`)
    selectedTaskDetail.value = {
      task_id: basic.id,
      task_type: basic.task_type,
      idempotency_key: basic.idempotency_key,
      status: basic.status,
      attempt_count: basic.attempt_count,
      result: {},
      metrics: {},
      error_message: null,
      next_retry_at: null,
      started_at: null,
      finished_at: null,
      created_at: new Date().toISOString(),
      trace_id: basic.trace_id,
    }
  }
}

async function submitCreateTask(): Promise<void> {
  try {
    if (!createTaskForm.taskType.trim() || !createTaskForm.idempotencyKey.trim()) {
      backendStatus.value = '任务新增失败：请填写任务类型与幂等键'
      return
    }
    const traceId = createTaskForm.traceId.trim() || makeTraceId()
    await sendJson<{ id: string }>('/tasks', 'POST', {
      task_type: createTaskForm.taskType.trim(),
      idempotency_key: createTaskForm.idempotencyKey.trim(),
      trace_id: traceId,
    })
    await fetchTasks(1)
    backendStatus.value = '任务新增成功'
    createTaskDialogOpen.value = false
    createTaskForm.taskType = 's1_ingest_pull'
    createTaskForm.idempotencyKey = ''
    createTaskForm.traceId = ''
  } catch {
    backendStatus.value = '任务新增失败：请检查后端接口或参数格式'
  }
}

async function deleteSelectedTasksBatch(): Promise<void> {
  if (selectedManageTaskIds.value.length === 0) {
    backendStatus.value = '请先勾选要删除的任务'
    return
  }
  try {
    await sendJson('/tasks', 'DELETE', { ids: selectedManageTaskIds.value })
    await fetchTasks(taskManagePage.value)
    backendStatus.value = `任务批量删除成功（${selectedManageTaskIds.value.length} 条）`
  } catch {
    backendStatus.value = '任务批量删除失败：请检查后端接口或参数格式'
  }
}

async function triggerPullNow(): Promise<void> {
  try {
    const payload = triggerPullForm.sourceSystem.trim() ? { source_system: triggerPullForm.sourceSystem.trim() } : {}
    const result = await sendJson<S1TaskResponse>('/s1/jobs/pull-now', 'POST', payload)
    backendStatus.value = `烽火事件拉取已触发：${result.task_id}`
    triggerPullDialogOpen.value = false
    triggerPullForm.sourceSystem = ''
    await fetchTasks(1)
    const matched = tasks.value.find((item) => item.id === result.task_id)
    if (matched) {
      openTaskDetail(matched)
    }
  } catch {
    backendStatus.value = '烽火事件拉取触发失败：请检查后端接口或参数格式'
  }
}

async function triggerAutoReviewNow(): Promise<void> {
  if (!backendOnline.value) {
    backendStatus.value = '后端离线：无法触发自动评审'
    return
  }

  autoReviewProcessing.value = true
  try {
    const result = await sendJson<S1TaskResponse>('/s1/jobs/auto-review-now', 'POST', {})
    backendStatus.value = `自动评审已触发：${result.task_id}`
    await fetchTasks(1)
    const matched = tasks.value.find((item) => item.id === result.task_id)
    if (matched) {
      openTaskDetail(matched)
    }
  } catch {
    backendStatus.value = '自动评审触发失败：请检查后端接口或参数格式'
  } finally {
    autoReviewProcessing.value = false
  }
}

async function fetchDataSources(page = 1): Promise<void> {
  const pageData = await fetchJson<BackendPage<BackendDataSourceItem>>(
    `/data-sources?page=${page}&page_size=${dataSourceManagePageSize.value}`,
  )
  dataSources.value = pageData.items.map(toDataSourceItem)
  dataSourceManageTotal.value = pageData.total
  dataSourceManagePage.value = pageData.page
  dataSourceManageJumpPage.value = String(pageData.page)
  selectedManageDataSourceIds.value = []
}

function openDataSourceDetail(item: DataSourceItem): void {
  selectedDataSource.value = item
  dataSourceDetailDialogOpen.value = true
}

function openDataSourceEdit(item: DataSourceItem): void {
  selectedDataSource.value = item
  editDataSourceForm.id = item.id
  editDataSourceForm.name = item.name
  editDataSourceForm.sourceSystem = item.sourceSystem
  editDataSourceForm.sourceType = item.sourceType
  editDataSourceForm.connectionConfig = JSON.stringify(item.connectionConfig, null, 2)
  editDataSourceForm.secretRef = item.secretRef ?? ''
  editDataSourceForm.credibilityLevel = item.credibilityLevel
  editDataSourceForm.syncFrequency = item.syncFrequency
  editDataSourceForm.isActive = item.isActive
  editDataSourceForm.version = item.version
  editDataSourceDialogOpen.value = true
}

function toggleManageDataSourceSelection(id: string): void {
  if (selectedManageDataSourceIds.value.includes(id)) {
    selectedManageDataSourceIds.value = selectedManageDataSourceIds.value.filter((item) => item !== id)
    return
  }
  selectedManageDataSourceIds.value = [...selectedManageDataSourceIds.value, id]
}

function toggleSelectAllDataSourcesOnPage(): void {
  if (allDataSourcesOnPageSelected.value) {
    selectedManageDataSourceIds.value = []
    return
  }
  selectedManageDataSourceIds.value = dataSources.value.map((item) => item.id)
}

function setDataSourceManagePageSize(size: number): void {
  dataSourceManagePageSize.value = size
  dataSourceManagePage.value = 1
  dataSourceManageJumpPage.value = '1'
  selectedManageDataSourceIds.value = []
  if (backendOnline.value) {
    void fetchDataSources(1)
  }
}

function goDataSourceManagePage(delta: number): void {
  const next = dataSourceManagePage.value + delta
  if (next < 1 || next > dataSourceManageTotalPages.value) {
    return
  }
  goToDataSourceManagePage(next)
}

function goToDataSourceManagePage(page: number): void {
  if (page < 1 || page > dataSourceManageTotalPages.value) {
    return
  }
  dataSourceManagePage.value = page
  dataSourceManageJumpPage.value = String(page)
  selectedManageDataSourceIds.value = []
  if (backendOnline.value) {
    void fetchDataSources(page)
  }
}

function jumpToDataSourcePageFromInput(): void {
  const page = Number(dataSourceManageJumpPage.value)
  if (!Number.isFinite(page)) {
    return
  }
  goToDataSourceManagePage(Math.min(Math.max(1, Math.trunc(page)), dataSourceManageTotalPages.value))
}

async function submitCreateDataSource(): Promise<void> {
  try {
    await sendJson<{ id: string }>('/data-sources', 'POST', {
      name: createDataSourceForm.name.trim(),
      source_system: createDataSourceForm.sourceSystem.trim(),
      source_type: createDataSourceForm.sourceType,
      connection_config: parseJsonObject(createDataSourceForm.connectionConfig),
      secret_ref: createDataSourceForm.secretRef.trim() || null,
      credibility_level: createDataSourceForm.credibilityLevel,
      sync_frequency: createDataSourceForm.syncFrequency.trim(),
      is_active: createDataSourceForm.isActive,
      version: createDataSourceForm.version.trim(),
    })
    await fetchDataSources(1)
    backendStatus.value = '数据源新增成功'
    createDataSourceDialogOpen.value = false
    createDataSourceForm.name = ''
    createDataSourceForm.sourceSystem = ''
    createDataSourceForm.connectionConfig = '{}'
    createDataSourceForm.secretRef = ''
  } catch {
    backendStatus.value = '数据源新增失败：请检查字段与后端接口'
  }
}

async function submitEditDataSource(): Promise<void> {
  try {
    await sendJson(`/data-sources/${editDataSourceForm.id}`, 'PATCH', {
      name: editDataSourceForm.name.trim(),
      source_system: editDataSourceForm.sourceSystem.trim(),
      source_type: editDataSourceForm.sourceType,
      connection_config: parseJsonObject(editDataSourceForm.connectionConfig),
      secret_ref: editDataSourceForm.secretRef.trim() || null,
      credibility_level: editDataSourceForm.credibilityLevel,
      sync_frequency: editDataSourceForm.syncFrequency.trim(),
      is_active: editDataSourceForm.isActive,
      version: editDataSourceForm.version.trim(),
    })
    await fetchDataSources(dataSourceManagePage.value)
    backendStatus.value = '数据源更新成功'
    editDataSourceDialogOpen.value = false
  } catch {
    backendStatus.value = '数据源更新失败：请检查字段与后端接口'
  }
}

async function deleteDataSourceInEditDialog(): Promise<void> {
  try {
    await sendJson('/data-sources', 'DELETE', { ids: [editDataSourceForm.id] })
    await fetchDataSources(dataSourceManagePage.value)
    backendStatus.value = '数据源删除成功'
    editDataSourceDialogOpen.value = false
  } catch {
    backendStatus.value = '数据源删除失败：请检查后端接口'
  }
}

async function deleteSelectedDataSourcesBatch(): Promise<void> {
  if (selectedManageDataSourceIds.value.length === 0) {
    backendStatus.value = '请先勾选要删除的数据源'
    return
  }
  try {
    const count = selectedManageDataSourceIds.value.length
    await sendJson('/data-sources', 'DELETE', { ids: selectedManageDataSourceIds.value })
    await fetchDataSources(dataSourceManagePage.value)
    backendStatus.value = `数据源批量删除成功（${count} 条）`
  } catch {
    backendStatus.value = '数据源批量删除失败：请检查后端接口'
  }
}

async function fetchFilterRules(page = 1): Promise<void> {
  const pageData = await fetchJson<BackendPage<BackendFilterRuleItem>>(
    `/event-filter-rules?page=${page}&page_size=${filterRuleManagePageSize.value}`,
  )
  filterRules.value = pageData.items.map(toFilterRuleItem)
  filterRuleManageTotal.value = pageData.total
  filterRuleManagePage.value = pageData.page
  filterRuleManageJumpPage.value = String(pageData.page)
  selectedManageFilterRuleIds.value = []
}

function openFilterRuleDetail(item: FilterRuleItem): void {
  selectedFilterRule.value = item
  filterRuleDetailDialogOpen.value = true
}

function openFilterRuleEdit(item: FilterRuleItem): void {
  selectedFilterRule.value = item
  editFilterRuleForm.id = item.id
  editFilterRuleForm.name = item.name
  editFilterRuleForm.level = item.level
  editFilterRuleForm.ruleScope = item.ruleScope
  editFilterRuleForm.filterExpression = item.filterExpression
  editFilterRuleForm.filterPrompts = item.filterPrompts.length > 0 ? [...item.filterPrompts] : ['']
  editFilterRuleForm.filterConfigItems = toFilterConfigItems(item.filterConfig)
  editFilterRuleForm.priority = item.priority
  editFilterRuleForm.status = item.status
  editFilterRuleForm.version = item.version
  editFilterRuleDialogOpen.value = true
}

function toggleManageFilterRuleSelection(id: string): void {
  if (selectedManageFilterRuleIds.value.includes(id)) {
    selectedManageFilterRuleIds.value = selectedManageFilterRuleIds.value.filter((item) => item !== id)
    return
  }
  selectedManageFilterRuleIds.value = [...selectedManageFilterRuleIds.value, id]
}

function toggleSelectAllFilterRulesOnPage(): void {
  if (allFilterRulesOnPageSelected.value) {
    selectedManageFilterRuleIds.value = []
    return
  }
  selectedManageFilterRuleIds.value = filterRules.value.map((item) => item.id)
}

function setFilterRuleManagePageSize(size: number): void {
  filterRuleManagePageSize.value = size
  filterRuleManagePage.value = 1
  filterRuleManageJumpPage.value = '1'
  selectedManageFilterRuleIds.value = []
  if (backendOnline.value) {
    void fetchFilterRules(1)
  }
}

function goFilterRuleManagePage(delta: number): void {
  const next = filterRuleManagePage.value + delta
  if (next < 1 || next > filterRuleManageTotalPages.value) {
    return
  }
  goToFilterRuleManagePage(next)
}

function goToFilterRuleManagePage(page: number): void {
  if (page < 1 || page > filterRuleManageTotalPages.value) {
    return
  }
  filterRuleManagePage.value = page
  filterRuleManageJumpPage.value = String(page)
  selectedManageFilterRuleIds.value = []
  if (backendOnline.value) {
    void fetchFilterRules(page)
  }
}

function jumpToFilterRulePageFromInput(): void {
  const page = Number(filterRuleManageJumpPage.value)
  if (!Number.isFinite(page)) {
    return
  }
  goToFilterRuleManagePage(Math.min(Math.max(1, Math.trunc(page)), filterRuleManageTotalPages.value))
}

async function submitCreateFilterRule(): Promise<void> {
  try {
    await sendJson('/event-filter-rules', 'POST', {
      name: createFilterRuleForm.name.trim(),
      level: createFilterRuleForm.level,
      rule_scope: createFilterRuleForm.ruleScope,
      filter_expression: createFilterRuleForm.filterExpression.trim(),
      filter_prompts: normalizePromptList(createFilterRuleForm.filterPrompts),
      filter_config: buildFilterConfigObject(createFilterRuleForm.filterConfigItems),
      priority: createFilterRuleForm.priority,
      status: createFilterRuleForm.status,
      version: createFilterRuleForm.version.trim(),
    })
    await fetchFilterRules(1)
    backendStatus.value = '过滤规则新增成功'
    createFilterRuleDialogOpen.value = false
    createFilterRuleForm.name = ''
    createFilterRuleForm.ruleScope = 'db_import'
    createFilterRuleForm.filterPrompts = ['']
    createFilterRuleForm.filterConfigItems = [{ key: 'keywords', value: '["rumor"]' }]
  } catch {
    backendStatus.value = '过滤规则新增失败：请检查字段与后端接口'
  }
}

async function submitEditFilterRule(): Promise<void> {
  try {
    await sendJson(`/event-filter-rules/${editFilterRuleForm.id}`, 'PATCH', {
      name: editFilterRuleForm.name.trim(),
      level: editFilterRuleForm.level,
      rule_scope: editFilterRuleForm.ruleScope,
      filter_expression: editFilterRuleForm.filterExpression.trim(),
      filter_prompts: normalizePromptList(editFilterRuleForm.filterPrompts),
      filter_config: buildFilterConfigObject(editFilterRuleForm.filterConfigItems),
      priority: editFilterRuleForm.priority,
      status: editFilterRuleForm.status,
      version: editFilterRuleForm.version.trim(),
    })
    await fetchFilterRules(filterRuleManagePage.value)
    backendStatus.value = '过滤规则更新成功'
    editFilterRuleDialogOpen.value = false
  } catch {
    backendStatus.value = '过滤规则更新失败：请检查字段与后端接口'
  }
}

async function deleteFilterRuleInEditDialog(): Promise<void> {
  try {
    await sendJson(`/event-filter-rules/${editFilterRuleForm.id}`, 'DELETE', {})
    await fetchFilterRules(filterRuleManagePage.value)
    backendStatus.value = '过滤规则删除成功'
    editFilterRuleDialogOpen.value = false
  } catch {
    backendStatus.value = '过滤规则删除失败：请检查后端接口'
  }
}

async function deleteSelectedFilterRulesBatch(): Promise<void> {
  if (selectedManageFilterRuleIds.value.length === 0) {
    backendStatus.value = '请先勾选要删除的过滤规则'
    return
  }
  try {
    const ids = [...selectedManageFilterRuleIds.value]
    await Promise.all(ids.map((id) => sendJson(`/event-filter-rules/${id}`, 'DELETE', {})))
    await fetchFilterRules(filterRuleManagePage.value)
    backendStatus.value = `过滤规则批量删除成功（${ids.length} 条）`
  } catch {
    backendStatus.value = '过滤规则批量删除失败：请检查后端接口'
  }
}

async function fetchTemplates(page = 1): Promise<void> {
  const keyword = encodeURIComponent(templateManageSearchKeyword.value.trim())
  const pageData = await fetchJson<BackendPage<BackendQuestionTemplateItem>>(
    `/question-templates?keyword=${keyword}&page=${page}&page_size=${templateManagePageSize.value}`,
  )
  templates.value = pageData.items.map(toQuestionTemplateItem)
  if (selectedTemplate.value) {
    selectedTemplate.value = templates.value.find((item) => item.id === selectedTemplate.value?.id) ?? null
  }
  templateManageTotal.value = pageData.total
  templateManagePage.value = pageData.page
  templateManageJumpPage.value = String(pageData.page)
  selectedManageTemplateIds.value = []
}

function openTemplateDetail(item: QuestionTemplateItem): void {
  selectedTemplate.value = item
  templateDetailDialogOpen.value = true
}

function openTemplateEdit(item: QuestionTemplateItem): void {
  selectedTemplate.value = item
  templateEditForm.id = item.id
  templateEditForm.questionTemplate = item.questionTemplate
  templateEditForm.majorTopic = item.majorTopic
  templateEditForm.minorTopic = item.minorTopic
  templateEditForm.difficultyLevel = item.difficultyLevel
  templateEditForm.constructionRationale = item.constructionRationale
  templateEditForm.candidateAnswers = item.candidateAnswers
  templateEditForm.answerDeadline = toDateTimeLocalValue(item.answerDeadline)
  templateEditForm.status = item.status
  templateEditForm.version = item.version
  templateEditDialogOpen.value = true
}

function toggleManageTemplateSelection(id: string): void {
  if (selectedManageTemplateIds.value.includes(id)) {
    selectedManageTemplateIds.value = selectedManageTemplateIds.value.filter((item) => item !== id)
    return
  }
  selectedManageTemplateIds.value = [...selectedManageTemplateIds.value, id]
}

function toggleSelectAllTemplatesOnPage(): void {
  if (allTemplatesOnPageSelected.value) {
    selectedManageTemplateIds.value = []
    return
  }
  selectedManageTemplateIds.value = templates.value.map((item) => item.id)
}

function setTemplateManagePageSize(size: number): void {
  templateManagePageSize.value = size
  templateManagePage.value = 1
  templateManageJumpPage.value = '1'
  selectedManageTemplateIds.value = []
  if (backendOnline.value) {
    void fetchTemplates(1)
  }
}

function goTemplateManagePage(delta: number): void {
  const next = templateManagePage.value + delta
  if (next < 1 || next > templateManageTotalPages.value) {
    return
  }
  goToTemplateManagePage(next)
}

function goToTemplateManagePage(page: number): void {
  if (page < 1 || page > templateManageTotalPages.value) {
    return
  }
  templateManagePage.value = page
  templateManageJumpPage.value = String(page)
  selectedManageTemplateIds.value = []
  if (backendOnline.value) {
    void fetchTemplates(page)
  }
}

function jumpToTemplatePageFromInput(): void {
  const page = Number(templateManageJumpPage.value)
  if (!Number.isFinite(page)) {
    return
  }
  goToTemplateManagePage(Math.min(Math.max(1, Math.trunc(page)), templateManageTotalPages.value))
}

async function submitCreateTemplate(): Promise<void> {
  try {
    const parsedDeadline = new Date(createTemplateForm.answerDeadline)
    if (Number.isNaN(parsedDeadline.getTime())) {
      backendStatus.value = '问题模板新增失败：截止时间格式无效'
      return
    }

    await sendJson('/question-templates', 'POST', {
      question_template: createTemplateForm.questionTemplate.trim(),
      major_topic: createTemplateForm.majorTopic.trim(),
      minor_topic: createTemplateForm.minorTopic.trim(),
      difficulty_level: createTemplateForm.difficultyLevel,
      construction_rationale: createTemplateForm.constructionRationale.trim(),
      candidate_answers: createTemplateForm.candidateAnswers.trim(),
      answer_deadline: parsedDeadline.toISOString(),
      status: createTemplateForm.status,
      version: createTemplateForm.version.trim(),
    })
    await fetchTemplates(1)
    backendStatus.value = '问题模板新增成功'
    createTemplateDialogOpen.value = false
    createTemplateForm.questionTemplate = ''
    createTemplateForm.majorTopic = ''
    createTemplateForm.minorTopic = ''
    createTemplateForm.difficultyLevel = 'L2'
    createTemplateForm.constructionRationale = ''
    createTemplateForm.candidateAnswers = ''
    createTemplateForm.answerDeadline = ''
    createTemplateForm.status = 'active'
    createTemplateForm.version = 'v1.0'
  } catch {
    backendStatus.value = '问题模板新增失败：请检查字段与后端接口'
  }
}

async function submitEditTemplate(): Promise<void> {
  try {
    const parsedDeadline = new Date(templateEditForm.answerDeadline)
    if (Number.isNaN(parsedDeadline.getTime())) {
      backendStatus.value = '问题模板更新失败：截止时间格式无效'
      return
    }

    await sendJson(`/question-templates/${templateEditForm.id}`, 'PATCH', {
      question_template: templateEditForm.questionTemplate.trim(),
      major_topic: templateEditForm.majorTopic.trim(),
      minor_topic: templateEditForm.minorTopic.trim(),
      difficulty_level: templateEditForm.difficultyLevel,
      construction_rationale: templateEditForm.constructionRationale.trim(),
      candidate_answers: templateEditForm.candidateAnswers.trim(),
      answer_deadline: parsedDeadline.toISOString(),
      status: templateEditForm.status,
      version: templateEditForm.version.trim(),
    })
    await fetchTemplates(templateManagePage.value)
    backendStatus.value = '问题模板更新成功'
    templateEditDialogOpen.value = false
    if (selectedTemplate.value && selectedTemplate.value.id === templateEditForm.id) {
      selectedTemplate.value = templates.value.find((item) => item.id === templateEditForm.id) ?? null
    }
  } catch {
    backendStatus.value = '问题模板更新失败：请检查字段与后端接口'
  }
}

async function deleteTemplateInEditDialog(): Promise<void> {
  try {
    await sendJson('/question-templates', 'DELETE', { ids: [templateEditForm.id] })
    await fetchTemplates(templateManagePage.value)
    backendStatus.value = '问题模板删除成功'
    templateEditDialogOpen.value = false
    if (selectedTemplate.value?.id === templateEditForm.id) {
      selectedTemplate.value = null
    }
  } catch {
    backendStatus.value = '问题模板删除失败：请检查后端接口'
  }
}

async function deleteSelectedTemplatesBatch(): Promise<void> {
  if (selectedManageTemplateIds.value.length === 0) {
    backendStatus.value = '请先勾选要删除的问题模板'
    return
  }
  try {
    const count = selectedManageTemplateIds.value.length
    await sendJson('/question-templates', 'DELETE', { ids: selectedManageTemplateIds.value })
    await fetchTemplates(templateManagePage.value)
    backendStatus.value = `问题模板批量删除成功（${count} 条）`
  } catch {
    backendStatus.value = '问题模板批量删除失败：请检查后端接口'
  }
}

async function deleteSelectedEventsBatch(): Promise<void> {
  if (selectedManageEventIds.value.length === 0) {
    backendStatus.value = '请先勾选要删除的事件'
    return
  }

  try {
    const ids = [...selectedManageEventIds.value]
    if (!backendOnline.value) {
      homeEvents.value = homeEvents.value.filter((item) => !ids.includes(item.id))
      manageEvents.value = manageEvents.value.filter((item) => !ids.includes(item.id))
      homeEventTotal.value = Math.max(0, homeEventTotal.value - ids.length)
      manageEventTotal.value = Math.max(0, manageEventTotal.value - ids.length)
    questions.value = questions.value.filter((item) => !item.eventIds.some((eventId) => ids.includes(eventId)))
      backendStatus.value = `后端离线：已删除 ${ids.length} 条模拟事件`
    } else {
      await sendJson('/events', 'DELETE', { ids })
      await Promise.all([fetchHomeEvents(), fetchManageEvents(eventManagePage.value)])
      backendStatus.value = `事件批量删除成功（${ids.length} 条）`
    }
    selectedManageEventIds.value = []
    if (eventManagePage.value > eventManageTotalPages.value) {
      eventManagePage.value = eventManageTotalPages.value
    }
  } catch {
    backendStatus.value = '事件批量删除失败：请检查后端接口或参数格式'
  }
}

async function reviewSelectedEvents(targetStatus: 'passed' | 'filtered'): Promise<void> {
  const ids = [...selectedPendingManageEventIds.value]
  if (ids.length === 0) {
    backendStatus.value = '请先勾选待审核（pending）的事件'
    return
  }

  eventReviewProcessing.value = true
  try {
    if (!backendOnline.value) {
      for (const target of homeEvents.value) {
        if (ids.includes(target.id)) {
          target.filterStatus = targetStatus
        }
      }
      for (const target of manageEvents.value) {
        if (ids.includes(target.id)) {
          target.filterStatus = targetStatus
        }
      }
      backendStatus.value = `后端离线：已审核 ${ids.length} 条模拟事件 -> ${targetStatus}`
    } else {
      await Promise.all(
        ids.map((id) =>
          sendJson(`/events/${id}`, 'PATCH', {
            filter_status: targetStatus,
          }),
        ),
      )
      await Promise.all([fetchManageEvents(eventManagePage.value), fetchHomeEvents()])
      backendStatus.value = `事件审核完成：${ids.length} 条 -> ${targetStatus}`
    }
    selectedManageEventIds.value = selectedManageEventIds.value.filter((id) => !ids.includes(id))
  } catch {
    backendStatus.value = '事件审核失败：请检查后端接口或参数格式'
  } finally {
    eventReviewProcessing.value = false
  }
}

async function deleteSelectedQuestionsBatch(): Promise<void> {
  if (selectedManageQuestionIds.value.length === 0) {
    backendStatus.value = '请先勾选要删除的问题'
    return
  }

  try {
    const ids = [...selectedManageQuestionIds.value]
    if (!backendOnline.value) {
      questions.value = questions.value.filter((item) => !ids.includes(item.id))
      backendStatus.value = `后端离线：已删除 ${ids.length} 条模拟问题`
    } else {
      await sendJson('/questions', 'DELETE', { ids })
      await Promise.all([hydrateFromBackend(), fetchManageQuestions(questionManagePage.value)])
      backendStatus.value = `问题批量删除成功（${ids.length} 条）`
    }
    if (ids.includes(selectedQuestionId.value)) {
      selectedQuestionId.value = questions.value[0]?.id ?? ''
    }
    selectedManageQuestionIds.value = []
    if (questionManagePage.value > questionManageTotalPages.value) {
      questionManagePage.value = questionManageTotalPages.value
    }
  } catch {
    backendStatus.value = '问题批量删除失败：请检查后端接口或参数格式'
  }
}

async function submitQuestionEdit(): Promise<void> {
  if (!questionEditForm.id) {
    return
  }

  try {
    const title = questionEditForm.title.trim()
    const deadline = questionEditForm.deadline.trim()
    const eventIds = Array.from(new Set(questionEditForm.eventIds)).filter((value) => value.trim().length > 0)
    const answerSpace = questionEditForm.answerSpace.trim()
    if (!title || !deadline) {
      backendStatus.value = '问题更新失败：请填写标题与截止时间'
      return
    }
    if ((questionEditForm.level === 'L1' || questionEditForm.level === 'L2') && !answerSpace) {
      backendStatus.value = '问题更新失败：L1/L2 需填写答案范围'
      return
    }
    const parsedDeadline = new Date(deadline)
    if (Number.isNaN(parsedDeadline.getTime())) {
      backendStatus.value = '问题更新失败：截止时间格式无效'
      return
    }
    const normalizedDeadline = parsedDeadline.toISOString()

    if (!backendOnline.value) {
      const target = questions.value.find((item) => item.id === questionEditForm.id)
      if (target) {
        target.title = title
        target.level = questionEditForm.level
        target.answerSpace = answerSpace
        target.eventIds = eventIds
        target.deadline = normalizedDeadline
        target.status = questionEditForm.status
      }
      backendStatus.value = '后端离线：已更新模拟问题'
      questionEditDialogOpen.value = false
      return
    }

    await sendJson(`/questions/${questionEditForm.id}`, 'PATCH', {
      level: levelToNumber(questionEditForm.level),
      content: title,
      answer_space: answerSpace || null,
      event_ids: eventIds,
      deadline: normalizedDeadline,
      status: questionEditForm.status,
    })
    await Promise.all([hydrateFromBackend(), fetchManageQuestions(questionManagePage.value)])
    backendStatus.value = '问题更新成功（后端）'
    questionEditDialogOpen.value = false
    questionEditEventSearch.value = ''
  } catch {
    backendStatus.value = '问题更新失败：请检查后端接口或参数格式'
  }
}

async function deleteQuestionInEditDialog(): Promise<void> {
  await deleteSelectedQuestion()
  questionEditDialogOpen.value = false
}

async function submitEventEdit(): Promise<void> {
  if (!eventEditForm.id) {
    return
  }
  try {
    const title = eventEditForm.title.trim()
    const theater = eventEditForm.theater.trim()
    const summary = eventEditForm.summary.trim()
    if (!title || !theater || !summary) {
      backendStatus.value = '事件更新失败：请完整填写标题、来源和内容'
      return
    }

    if (!backendOnline.value) {
      for (const target of homeEvents.value) {
        if (target.id === eventEditForm.id) {
          target.title = title
          target.theater = theater
          target.summary = summary
          target.severity = eventEditForm.severity
          target.filterStatus = eventEditForm.filterStatus || target.filterStatus
        }
      }
      for (const target of manageEvents.value) {
        if (target.id === eventEditForm.id) {
          target.title = title
          target.theater = theater
          target.summary = summary
          target.severity = eventEditForm.severity
          target.filterStatus = eventEditForm.filterStatus || target.filterStatus
        }
      }
      backendStatus.value = '后端离线：已更新模拟事件'
      eventEditDialogOpen.value = false
      return
    }

    await sendJson(`/events/${eventEditForm.id}`, 'PATCH', {
      title,
      source_system: theater,
      content: summary,
      credibility_level: credibilityFromSeverity(eventEditForm.severity),
      filter_status: eventEditForm.filterStatus,
    })
    await Promise.all([fetchHomeEvents(), fetchManageEvents(eventManagePage.value)])
    backendStatus.value = '事件更新成功（后端）'
    eventEditDialogOpen.value = false
  } catch {
    backendStatus.value = '事件更新失败：请检查后端接口或参数格式'
  }
}

async function deleteEventInEditDialog(): Promise<void> {
  await deleteSelectedEvent()
  eventEditDialogOpen.value = false
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

function inferToastKind(message: string): ToastKind {
  if (message.includes('失败') || message.includes('错误') || message.includes('不可用')) {
    return 'error'
  }
  if (message.includes('成功') || message.includes('已触发') || message.includes('已更新') || message.includes('已删除') || message.includes('已连接')) {
    return 'success'
  }
  return 'info'
}

function dismissToast(id: number): void {
  toasts.value = toasts.value.filter((item) => item.id !== id)
}

function pushToast(message: string, kind?: ToastKind): void {
  const text = message.trim()
  if (!text) {
    return
  }
  const id = ++toastSeed
  const resolvedKind = kind ?? inferToastKind(text)
  toasts.value = [...toasts.value, { id, kind: resolvedKind, message: text }].slice(-4)
  window.setTimeout(() => {
    dismissToast(id)
  }, 3200)
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
  const cryptoApi = globalThis.crypto
  if (cryptoApi && typeof cryptoApi.randomUUID === 'function') {
    return cryptoApi.randomUUID()
  }
  if (cryptoApi && typeof cryptoApi.getRandomValues === 'function') {
    const bytes = new Uint8Array(16)
    cryptoApi.getRandomValues(bytes)
    const byte6 = bytes[6] ?? 0
    const byte8 = bytes[8] ?? 0
    bytes[6] = (byte6 & 0x0f) | 0x40
    bytes[8] = (byte8 & 0x3f) | 0x80
    const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20, 32)}`
  }
  return '00000000-0000-4000-8000-000000000000'
}

function toEventItem(item: BackendEventItem): EventItem {
  return {
    id: item.id,
    codename: item.event_key,
    title: item.title,
    theater: item.source_system,
    summary: item.content,
    tags: item.tags ?? [],
    severity: severityFromCredibility(item.credibility_level),
    filterStatus: item.filter_status,
    timestamp: item.event_time,
  }
}

function toQuestionItem(item: BackendQuestionItem): QuestionItem {
  const eventIds = Array.isArray(item.event_ids)
    ? item.event_ids
    : item.event_id
      ? [item.event_id]
      : []
  return {
    id: item.id,
    eventIds,
    level: normalizeLevel(item.level),
    title: item.content,
    answerSpace: item.answer_space ?? '',
    hypothesis: '由后端问题内容导入，待补充可证伪假设。',
    deadline: item.deadline,
    status: item.status === 'resolved' ? 'resolved' : item.status === 'locked' ? 'locked' : 'collecting',
    groundTruth: item.status === 'resolved' ? '后端状态显示已解析，请补充真实结果详情。' : '待真实结果回填。',
  }
}

function sortByEventTimeDesc(items: EventItem[]): EventItem[] {
  return [...items].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
}

function toTaskItem(item: BackendTaskItem): TaskItem {
  return {
    id: item.id,
    taskType: item.task_type,
    idempotencyKey: item.idempotency_key,
    status: item.status,
    attemptCount: item.attempt_count,
    traceId: item.trace_id,
  }
}

function toDataSourceItem(item: BackendDataSourceItem): DataSourceItem {
  return {
    id: item.id,
    name: item.name,
    sourceSystem: item.source_system,
    sourceType: item.source_type,
    connectionConfig: item.connection_config ?? {},
    secretRef: item.secret_ref,
    credibilityLevel: item.credibility_level,
    syncFrequency: item.sync_frequency,
    isActive: item.is_active,
    version: item.version,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  }
}

function toFilterRuleItem(item: BackendFilterRuleItem): FilterRuleItem {
  return {
    id: item.id,
    name: item.name,
    level: item.level,
    ruleScope: item.rule_scope,
    filterExpression: item.filter_expression,
    filterPrompts: item.filter_prompts ?? [],
    filterConfig: item.filter_config ?? {},
    priority: item.priority,
    status: item.status,
    version: item.version,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  }
}

function toQuestionTemplateItem(item: BackendQuestionTemplateItem): QuestionTemplateItem {
  return {
    id: item.id,
    questionTemplate: item.question_template,
    majorTopic: item.major_topic,
    minorTopic: item.minor_topic,
    difficultyLevel: item.difficulty_level,
    constructionRationale: item.construction_rationale,
    candidateAnswers: item.candidate_answers,
    answerDeadline: item.answer_deadline,
    status: item.status,
    version: item.version,
    usageCount: item.usage_count,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  }
}

function parseJsonObject(text: string): Record<string, unknown> {
  const trimmed = text.trim()
  if (!trimmed) {
    return {}
  }
  const parsed = JSON.parse(trimmed)
  if (typeof parsed === 'object' && parsed !== null && !Array.isArray(parsed)) {
    return parsed as Record<string, unknown>
  }
  throw new Error('JSON must be an object')
}

function parseLocalDateTimeToMs(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) {
    return null
  }
  const parsed = Date.parse(trimmed)
  return Number.isFinite(parsed) ? parsed : null
}

function toIsoFromLocalDateTime(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) {
    return ''
  }
  const parsed = Date.parse(trimmed)
  if (!Number.isFinite(parsed)) {
    return ''
  }
  return new Date(parsed).toISOString()
}

function normalizePromptList(prompts: string[]): string[] {
  return prompts.map((item) => item.trim()).filter((item) => item.length > 0)
}

function toFilterConfigItems(config: Record<string, unknown>): Array<{ key: string; value: string }> {
  const entries = Object.entries(config)
  if (entries.length === 0) {
    return [{ key: '', value: '' }]
  }
  return entries.map(([key, value]) => ({ key, value: formatFilterConfigValue(value) }))
}

function formatFilterConfigValue(value: unknown): string {
  if (typeof value === 'string') {
    return value
  }
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}

function parseFilterConfigValue(raw: string): unknown {
  const trimmed = raw.trim()
  if (!trimmed) {
    return ''
  }
  try {
    return JSON.parse(trimmed)
  } catch {
    return trimmed
  }
}

function buildFilterConfigObject(items: Array<{ key: string; value: string }>): Record<string, unknown> {
  const result: Record<string, unknown> = {}
  for (const item of items) {
    const key = item.key.trim()
    if (!key) {
      continue
    }
    result[key] = parseFilterConfigValue(item.value)
  }
  return result
}

function filterConfigDisplayEntries(config: Record<string, unknown>): Array<{ key: string; value: string }> {
  return Object.entries(config).map(([key, value]) => ({ key, value: formatFilterConfigValue(value) }))
}

function addCreateFilterPromptRow(): void {
  createFilterRuleForm.filterPrompts.push('')
}

function removeCreateFilterPromptRow(index: number): void {
  createFilterRuleForm.filterPrompts.splice(index, 1)
  if (createFilterRuleForm.filterPrompts.length === 0) {
    createFilterRuleForm.filterPrompts.push('')
  }
}

function addEditFilterPromptRow(): void {
  editFilterRuleForm.filterPrompts.push('')
}

function removeEditFilterPromptRow(index: number): void {
  editFilterRuleForm.filterPrompts.splice(index, 1)
  if (editFilterRuleForm.filterPrompts.length === 0) {
    editFilterRuleForm.filterPrompts.push('')
  }
}

function addCreateFilterConfigRow(): void {
  createFilterRuleForm.filterConfigItems.push({ key: '', value: '' })
}

function removeCreateFilterConfigRow(index: number): void {
  createFilterRuleForm.filterConfigItems.splice(index, 1)
  if (createFilterRuleForm.filterConfigItems.length === 0) {
    createFilterRuleForm.filterConfigItems.push({ key: '', value: '' })
  }
}

function addEditFilterConfigRow(): void {
  editFilterRuleForm.filterConfigItems.push({ key: '', value: '' })
}

function removeEditFilterConfigRow(index: number): void {
  editFilterRuleForm.filterConfigItems.splice(index, 1)
  if (editFilterRuleForm.filterConfigItems.length === 0) {
    editFilterRuleForm.filterConfigItems.push({ key: '', value: '' })
  }
}

async function fetchSourceSystemOptions(): Promise<void> {
  try {
    const pageData = await fetchJson<BackendPage<BackendDataSourceItem>>('/data-sources?page=1&page_size=100')
    const options = Array.from(
      new Set(pageData.items.filter((item) => item.is_active).map((item) => item.source_system)),
    )
    sourceSystemOptions.value = options
    const firstSource = options.length > 0 ? options[0] : undefined
    if (!draftEvent.theater && firstSource) {
      draftEvent.theater = firstSource
    }
  } catch {
    sourceSystemOptions.value = []
  }
}

async function fetchQuestionEventOptions(keyword: string): Promise<void> {
  if (!backendOnline.value) {
    questionEventOptions.value = []
    questionEventSearchTotal.value = 0
    questionEventSearchLoading.value = false
    return
  }

  const requestSeq = questionEventSearchSeq.value + 1
  questionEventSearchSeq.value = requestSeq
  questionEventSearchLoading.value = true

  try {
    const query = encodeURIComponent(keyword.trim())
    const eventPage = await fetchJson<BackendPage<BackendEventItem>>(
      `/events/search?keyword=${query}&filter_status=passed&page=1&page_size=50`,
    )
    if (requestSeq !== questionEventSearchSeq.value) {
      return
    }

    const mapped = sortByEventTimeDesc(eventPage.items.map(toEventItem))
    questionEventOptions.value = mapped
    questionEventSearchTotal.value = eventPage.total

    if (mapped.length > 0 && !mapped.some((item) => item.id === selectedEventId.value)) {
      selectedEventId.value = mapped[0]?.id ?? selectedEventId.value
    }
    if (selectedEventIdsForQuestion.value.length === 0) {
      selectedEventIdsForQuestion.value = selectedEventId.value ? [selectedEventId.value] : []
    }
  } catch {
    if (requestSeq !== questionEventSearchSeq.value) {
      return
    }
    questionEventOptions.value = []
    questionEventSearchTotal.value = 0
    backendStatus.value = '事件搜索失败：请检查后端搜索接口'
  } finally {
    if (requestSeq === questionEventSearchSeq.value) {
      questionEventSearchLoading.value = false
    }
  }
}

async function ensureQuestionEventOptionsByIds(eventIds: string[]): Promise<void> {
  if (!backendOnline.value || eventIds.length === 0) {
    return
  }
  const known = new Set(allKnownEvents.value.map((item) => item.id))
  const missing = eventIds.filter((id) => !known.has(id))
  if (missing.length === 0) {
    return
  }
  const fetched = await Promise.all(
    missing.map(async (id) => {
      try {
        const item = await fetchJson<BackendEventItem>(`/events/${id}`)
        return toEventItem(item)
      } catch {
        return null
      }
    }),
  )
  const merged = [...questionEventOptions.value]
  for (const item of fetched) {
    if (!item) {
      continue
    }
    if (!merged.some((target) => target.id === item.id)) {
      merged.push(item)
    }
  }
  questionEventOptions.value = merged
}

function apiBaseUrl(): string {
  return (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() || 'http://127.0.0.1:8000'
}

function applyAuthSession(payload: AuthLoginApiResponse): void {
  authAccessToken.value = payload.access_token
  authRefreshToken.value = payload.refresh_token
  authUser.value = payload.user
  localStorage.setItem('moppa_access_token', payload.access_token)
  localStorage.setItem('moppa_refresh_token', payload.refresh_token)
}

function clearAuthSession(openDialog = true): void {
  authAccessToken.value = ''
  authRefreshToken.value = ''
  authUser.value = null
  localStorage.removeItem('moppa_access_token')
  localStorage.removeItem('moppa_refresh_token')
  if (openDialog) {
    authDialogOpen.value = true
  }
}

async function refreshAuthSession(): Promise<boolean> {
  if (!authRefreshToken.value) {
    return false
  }
  if (authRefreshPromise) {
    return authRefreshPromise
  }
  authRefreshPromise = (async () => {
    try {
      const response = await fetch(`${apiBaseUrl()}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: authRefreshToken.value }),
      })
      if (!response.ok) {
        return false
      }
      const payload = (await response.json()) as AuthLoginApiResponse
      applyAuthSession(payload)
      return true
    } catch {
      return false
    } finally {
      authRefreshPromise = null
    }
  })()
  const refreshed = await authRefreshPromise
  if (!refreshed) {
    clearAuthSession(true)
  }
  return refreshed
}

async function requestJson<T>(
  path: string,
  init: RequestInit,
  withAuth: boolean,
  retryOnUnauthorized: boolean,
): Promise<T> {
  const headers = new Headers(init.headers ?? {})
  if (!headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json')
  }
  if (withAuth && authAccessToken.value) {
    headers.set('Authorization', `Bearer ${authAccessToken.value}`)
  }

  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers,
  })

  if (response.status === 401 && retryOnUnauthorized && withAuth) {
    const refreshed = await refreshAuthSession()
    if (refreshed) {
      return requestJson<T>(path, init, withAuth, false)
    }
  }

  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`)
  }
  if (response.status === 204) {
    return {} as T
  }
  return (await response.json()) as T
}

async function fetchJson<T>(path: string): Promise<T> {
  const shouldAttachAuth = !path.startsWith('/auth/login') && !path.startsWith('/auth/register') && !path.startsWith('/auth/refresh')
  return requestJson<T>(path, { method: 'GET' }, shouldAttachAuth, true)
}

async function sendJson<T>(path: string, method: 'POST' | 'PATCH' | 'DELETE', body: object): Promise<T> {
  const shouldAttachAuth = !path.startsWith('/auth/login') && !path.startsWith('/auth/register') && !path.startsWith('/auth/refresh')
  return requestJson<T>(
    path,
    {
      method,
      body: JSON.stringify(body),
    },
    shouldAttachAuth,
    true,
  )
}

async function bootstrapAuthSession(): Promise<void> {
  authLoading.value = true
  try {
    if (authAccessToken.value) {
      const me = await fetchJson<AuthUser>('/auth/me')
      authUser.value = me
      authDialogOpen.value = false
      authError.value = ''
      return
    }
    if (authRefreshToken.value) {
      const refreshed = await refreshAuthSession()
      if (refreshed) {
        authDialogOpen.value = false
        authError.value = ''
        return
      }
    }
    authDialogOpen.value = true
  } catch {
    clearAuthSession(true)
  } finally {
    authLoading.value = false
  }
}

async function submitAuth(): Promise<void> {
  const username = authForm.username.trim()
  const password = authForm.password.trim()
  const email = authForm.email.trim()
  if (!username || !password) {
    authError.value = '请输入用户名和密码'
    return
  }

  authLoading.value = true
  authError.value = ''
  try {
    if (authMode.value === 'register') {
      await sendJson<AuthUser>('/auth/register', 'POST', {
        username,
        password,
        email: email || null,
      })
    }
    const payload = await sendJson<AuthLoginApiResponse>('/auth/login', 'POST', {
      username,
      password,
    })
    applyAuthSession(payload)
    authDialogOpen.value = false
    authForm.password = ''
    await hydrateFromBackend()
  } catch {
    authError.value = authMode.value === 'register' ? '注册或登录失败，请检查输入' : '登录失败，请检查用户名或密码'
  } finally {
    authLoading.value = false
  }
}

async function logout(): Promise<void> {
  try {
    if (authRefreshToken.value) {
      await sendJson('/auth/logout', 'POST', { refresh_token: authRefreshToken.value })
    }
  } catch {
    // ignore
  } finally {
    clearAuthSession(true)
    currentView.value = 'home'
  }
}

async function fetchEventTotalByStatus(status: string): Promise<number> {
  const query = encodeURIComponent(status)
  const page = await fetchJson<BackendPage<BackendEventItem>>(
    `/events/search?keyword=&filter_status=${query}&page=1&page_size=1`,
  )
  return page.total
}

async function fetchTaskTotalByStatus(status: string): Promise<number> {
  const query = encodeURIComponent(status)
  const page = await fetchJson<BackendPage<BackendTaskItem>>(`/tasks?status=${query}&page=1&page_size=1`)
  return page.total
}

async function refreshTopMetrics(): Promise<void> {
  if (!backendOnline.value) {
    totalEventCount.value = allKnownEvents.value.length
    pendingEventCount.value = allKnownEvents.value.filter((item) => item.filterStatus === 'pending').length
    runningTaskCount.value = tasks.value.filter((item) => item.status === 'running' || item.status === 'pending').length
    return
  }

  try {
    const [eventTotal, pendingTotal, runningTotal, pendingTaskTotal] = await Promise.all([
      fetchEventTotalByStatus(''),
      fetchEventTotalByStatus('pending'),
      fetchTaskTotalByStatus('running'),
      fetchTaskTotalByStatus('pending'),
    ])
    totalEventCount.value = eventTotal
    pendingEventCount.value = pendingTotal
    runningTaskCount.value = runningTotal + pendingTaskTotal
  } catch {
    totalEventCount.value = allKnownEvents.value.length
    pendingEventCount.value = allKnownEvents.value.filter((item) => item.filterStatus === 'pending').length
    runningTaskCount.value = tasks.value.filter((item) => item.status === 'running' || item.status === 'pending').length
  }
}

function scheduleTopMetricRefresh(delayMs = 180): void {
  if (topMetricRefreshTimer !== undefined) {
    window.clearTimeout(topMetricRefreshTimer)
  }
  topMetricRefreshTimer = window.setTimeout(() => {
    void refreshTopMetrics()
  }, delayMs)
}

async function fetchHomeEvents(page = 1): Promise<void> {
  const eventPage = await fetchJson<BackendPage<BackendEventItem>>(
    `/events/search?keyword=&filter_status=passed&page=${page}&page_size=${homeEventPageSize}`,
  )
  if (eventPage.items.length === 0) {
    homeEvents.value = []
    homeEventTotal.value = eventPage.total
    homeEventPage.value = page
    homeEventJumpPage.value = String(page)
    return
  }
  const mapped = sortByEventTimeDesc(eventPage.items.map(toEventItem))
  homeEvents.value = mapped
  homeEventTotal.value = eventPage.total
  homeEventPage.value = page
  homeEventJumpPage.value = String(page)
  if (!mapped.some((item) => item.id === selectedEventId.value)) {
    selectedEventId.value = mapped[0]?.id ?? ''
  }
}

async function fetchManageEvents(page: number): Promise<void> {
  if (!backendOnline.value) {
    return
  }
  const requestSeq = eventManageSearchSeq.value + 1
  eventManageSearchSeq.value = requestSeq
  eventManageSearchLoading.value = true

  try {
    const keyword = encodeURIComponent(eventManageSearchKeyword.value.trim())
    const status = encodeURIComponent(eventManageFilterStatus.value.trim())
    const fromIso = encodeURIComponent(toIsoFromLocalDateTime(eventManageTimeFrom.value))
    const toIso = encodeURIComponent(toIsoFromLocalDateTime(eventManageTimeTo.value))
    const timeQuery = [
      fromIso ? `event_time_from=${fromIso}` : '',
      toIso ? `event_time_to=${toIso}` : '',
    ]
      .filter((item) => item.length > 0)
      .join('&')
    const eventPage = await fetchJson<BackendPage<BackendEventItem>>(
      `/events/search?keyword=${keyword}&filter_status=${status}${timeQuery ? `&${timeQuery}` : ''}&page=${page}&page_size=${eventManagePageSize.value}`,
    )
    if (requestSeq !== eventManageSearchSeq.value) {
      return
    }

    manageEvents.value = sortByEventTimeDesc(eventPage.items.map(toEventItem))
    manageEventTotal.value = eventPage.total
    eventManagePage.value = page
    eventManageJumpPage.value = String(page)
  } finally {
    if (requestSeq === eventManageSearchSeq.value) {
      eventManageSearchLoading.value = false
    }
  }
}

async function fetchManageQuestions(page: number): Promise<void> {
  if (!backendOnline.value) {
    return
  }
  const requestSeq = questionManageSearchSeq.value + 1
  questionManageSearchSeq.value = requestSeq
  questionManageSearchLoading.value = true

  try {
    const keyword = encodeURIComponent(questionManageSearchKeyword.value.trim())
    const questionPage = await fetchJson<BackendPage<BackendQuestionItem>>(
      `/questions/search?keyword=${keyword}&page=${page}&page_size=${questionManagePageSize.value}`,
    )
    if (requestSeq !== questionManageSearchSeq.value) {
      return
    }

    manageQuestions.value = questionPage.items.map(toQuestionItem)
    questionManageTotal.value = questionPage.total
    questionManagePage.value = page
    questionManageJumpPage.value = String(page)
    selectedManageQuestionIds.value = []
  } finally {
    if (requestSeq === questionManageSearchSeq.value) {
      questionManageSearchLoading.value = false
    }
  }
}

function resetQuestionFeed(): void {
  questionFeedItems.value = []
  questionFeedPage.value = 0
  questionFeedTotal.value = 0
  questionFeedHasMore.value = true
}

async function loadQuestionFeedNextPage(): Promise<void> {
  if (questionFeedLoading.value || !questionFeedHasMore.value) {
    return
  }

  questionFeedLoading.value = true
  try {
    const nextPage = questionFeedPage.value + 1
    if (!backendOnline.value) {
      const source = [...questions.value].sort(
        (a, b) => new Date(b.deadline).getTime() - new Date(a.deadline).getTime(),
      )
      const start = (nextPage - 1) * 10
      const batch = source.slice(start, start + 10)
      questionFeedItems.value = [...questionFeedItems.value, ...batch]
      questionFeedPage.value = nextPage
      questionFeedTotal.value = source.length
      questionFeedHasMore.value = questionFeedItems.value.length < source.length && batch.length > 0
      return
    }

    const pageData = await fetchJson<BackendPage<BackendQuestionItem>>(
      `/questions/search?keyword=&page=${nextPage}&page_size=10`,
    )
    const batch = pageData.items.map(toQuestionItem)
    questionFeedItems.value = [...questionFeedItems.value, ...batch]
    questionFeedPage.value = nextPage
    questionFeedTotal.value = pageData.total
    questionFeedHasMore.value = questionFeedItems.value.length < pageData.total && batch.length > 0
  } catch {
    backendStatus.value = '问题社区加载失败：请检查后端问题搜索接口'
    questionFeedHasMore.value = false
  } finally {
    questionFeedLoading.value = false
  }
}

async function createEvent(): Promise<void> {
  try {
    const title = draftEvent.title.trim()
    const theater = draftEvent.theater.trim()
    const summary = draftEvent.summary.trim()
    if (!title || !theater || !summary) {
      backendStatus.value = '事件新增失败：请完整填写标题、来源和内容'
      return
    }

    const codename = `EVENT-${Date.now()}`

    if (!backendOnline.value) {
      const localId = `evt-local-${Date.now()}`
      const newItem: EventItem = {
        id: localId,
        codename,
        title,
        theater,
        summary,
        tags: [],
        severity: draftEvent.severity,
        filterStatus: 'mock_new',
        timestamp: new Date().toISOString(),
      }
      homeEvents.value.unshift(newItem)
      if (currentView.value === 'events') {
        manageEvents.value.unshift({ ...newItem })
      }
      selectedEventId.value = localId
      homeEventTotal.value += 1
      manageEventTotal.value += 1
      backendStatus.value = '后端离线：已在模拟数据中新增事件'
    } else {
      await sendJson<{ id: string }>('/events', 'POST', {
        event_key: codename,
        title,
        content: summary,
        source_system: theater,
        credibility_level: credibilityFromSeverity(draftEvent.severity),
        event_time: new Date().toISOString(),
        trace_id: makeTraceId(),
      })
      await Promise.all([fetchHomeEvents(), fetchManageEvents(1)])
      eventManagePage.value = 1
      backendStatus.value = '事件新增成功（后端）'
    }

    draftEvent.title = ''
    draftEvent.theater = ''
    draftEvent.summary = ''
  } catch {
    backendStatus.value = '事件新增失败：请检查后端接口或参数格式'
  }
}

async function deleteSelectedEvent(): Promise<void> {
  try {
    const currentId = selectedEventId.value
    if (!currentId) {
      return
    }

    if (!backendOnline.value) {
      homeEvents.value = homeEvents.value.filter((item) => item.id !== currentId)
      manageEvents.value = manageEvents.value.filter((item) => item.id !== currentId)
      homeEventTotal.value = Math.max(0, homeEventTotal.value - 1)
      manageEventTotal.value = Math.max(0, manageEventTotal.value - 1)
      questions.value = questions.value.filter((item) => !item.eventIds.includes(currentId))
      selectedEventId.value = homeEvents.value[0]?.id ?? ''
      selectedQuestionId.value = questions.value.find((item) => item.eventIds.includes(selectedEventId.value))?.id ?? ''
      backendStatus.value = '后端离线：已在模拟数据中删除事件及关联问题'
      return
    }

    await sendJson('/events', 'DELETE', { ids: [currentId] })
    await Promise.all([fetchHomeEvents(), fetchManageEvents(eventManagePage.value)])
    backendStatus.value = '事件删除成功（后端）'
  } catch {
    backendStatus.value = '事件删除失败：请检查后端接口或参数格式'
  }
}

async function createQuestion(): Promise<void> {
  try {
    const title = draftQuestion.title.trim()
    const deadline = draftQuestion.deadline.trim()
    const eventIds = Array.from(new Set(selectedEventIdsForQuestion.value)).filter((value) => value.trim().length > 0)
    const answerSpace = draftQuestion.answerSpace.trim()
    if (!title || !deadline) {
      backendStatus.value = '问题新增失败：请填写标题与截止时间'
      return
    }
    if ((draftQuestion.level === 'L1' || draftQuestion.level === 'L2') && !answerSpace) {
      backendStatus.value = '问题新增失败：L1/L2 需填写答案范围'
      return
    }

    const parsedDeadline = new Date(deadline)
    if (Number.isNaN(parsedDeadline.getTime())) {
      backendStatus.value = '问题新增失败：截止时间格式无效'
      return
    }
    const normalizedDeadline = parsedDeadline.toISOString()

    if (!backendOnline.value) {
      const localId = `q-local-${Date.now()}`
      questions.value.unshift({
        id: localId,
        eventIds,
        level: draftQuestion.level,
        title,
        answerSpace,
        hypothesis: '由人工创建，待补充假设。',
        deadline: normalizedDeadline,
        status: draftQuestion.status,
        groundTruth: '待真实结果回填。',
      })
      selectedQuestionId.value = localId
      backendStatus.value = '后端离线：已在模拟数据中新增问题'
      draftQuestion.title = ''
      draftQuestion.answerSpace = ''
      return
    }

    await sendJson<{ id: string }>('/questions', 'POST', {
      event_ids: eventIds,
      level: levelToNumber(draftQuestion.level),
      content: title,
      answer_space: answerSpace || null,
      deadline: normalizedDeadline,
      trace_id: makeTraceId(),
    })
    await Promise.all([hydrateFromBackend(), fetchManageQuestions(1)])
    backendStatus.value = '问题新增成功（后端）'
    draftQuestion.title = ''
    draftQuestion.answerSpace = ''
  } catch {
    backendStatus.value = '问题新增失败：请检查后端接口或参数格式'
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
      selectedQuestionId.value = questions.value.find((item) => item.eventIds.includes(selectedEventId.value))?.id ?? ''
      backendStatus.value = '后端离线：已在模拟数据中删除问题'
      return
    }

    await sendJson('/questions', 'DELETE', { ids: [currentId] })
    await Promise.all([hydrateFromBackend(), fetchManageQuestions(questionManagePage.value)])
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

    const [homeEventResult, questionResult] = await Promise.allSettled([
      fetchHomeEvents(),
      fetchJson<BackendPage<BackendQuestionItem>>('/questions?page=1&page_size=100'),
    ])

    const loadedParts: string[] = []

    if (homeEventResult.status === 'fulfilled') {
      loadedParts.push(`事件首页 ${homeEvents.value.length} 条`)
    }

    if (questionResult.status === 'fulfilled') {
      const mappedQuestions: QuestionItem[] = questionResult.value.items.map(toQuestionItem)
      questions.value = mappedQuestions
      questionManageTotal.value = mappedQuestions.length
      const firstQuestion = mappedQuestions.find((question) => question.eventIds.includes(selectedEventId.value))
      selectedQuestionId.value = firstQuestion?.id ?? mappedQuestions[0]?.id ?? selectedQuestionId.value
      questionManagePage.value = 1
      selectedManageQuestionIds.value = []
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
  void (async () => {
    await bootstrapAuthSession()
    if (isAuthenticated.value) {
      await hydrateFromBackend()
      await fetchSourceSystemOptions()
    }
  })()
  scheduleTopMetricRefresh(0)
  window.addEventListener('keydown', handleGlobalKeydown)
})

onBeforeUnmount(() => {
  if (topMetricRefreshTimer !== undefined) {
    window.clearTimeout(topMetricRefreshTimer)
    topMetricRefreshTimer = undefined
  }
  window.removeEventListener('keydown', handleGlobalKeydown)
})

watch(currentView, (view) => {
  if (!isAuthenticated.value) {
    authDialogOpen.value = true
    if (view !== 'home' && view !== 'questionStream') {
      currentView.value = 'home'
    }
    return
  }

  if (!isAdmin.value && view !== 'home' && view !== 'questionStream') {
    currentView.value = 'home'
    backendStatus.value = '当前账号仅允许访问首页和问题社区'
    return
  }

  if (view === 'events') {
    if (backendOnline.value) {
      void fetchManageEvents(1)
    } else {
      manageEvents.value = [...homeEvents.value]
      manageEventTotal.value = homeEvents.value.length
      eventManagePage.value = 1
      eventManageJumpPage.value = '1'
      selectedManageEventIds.value = []
    }
  }
  if (view === 'questions') {
    if (backendOnline.value) {
      void fetchManageQuestions(1)
    } else {
      manageQuestions.value = []
      questionManageTotal.value = localFilteredManageQuestions.value.length
      questionManagePage.value = 1
      questionManageJumpPage.value = '1'
      selectedManageQuestionIds.value = []
    }
  }
  if (view === 'questionStream') {
    resetQuestionFeed()
    void loadQuestionFeedNextPage()
  }
  if (view === 'templates') {
    if (backendOnline.value) {
      void fetchTemplates(1)
    } else {
      templates.value = []
      templateManageTotal.value = 0
      templateManagePage.value = 1
      templateManageJumpPage.value = '1'
      selectedManageTemplateIds.value = []
    }
  }
  if (view === 'tasks') {
    if (backendOnline.value) {
      void fetchTasks(1)
    } else {
      tasks.value = []
      taskManageTotal.value = 0
      taskManagePage.value = 1
      taskManageJumpPage.value = '1'
      selectedManageTaskIds.value = []
    }
  }
  if (view === 'dataSources') {
    if (backendOnline.value) {
      void fetchDataSources(1)
    } else {
      dataSources.value = []
      dataSourceManageTotal.value = 0
      dataSourceManagePage.value = 1
      dataSourceManageJumpPage.value = '1'
      selectedManageDataSourceIds.value = []
    }
  }
  if (view === 'filterRules') {
    if (backendOnline.value) {
      void fetchFilterRules(1)
    } else {
      filterRules.value = []
      filterRuleManageTotal.value = 0
      filterRuleManagePage.value = 1
      filterRuleManageJumpPage.value = '1'
      selectedManageFilterRuleIds.value = []
    }
  }
})

watch(eventManageSearchKeyword, () => {
  eventManagePage.value = 1
  eventManageJumpPage.value = '1'
  selectedManageEventIds.value = []
  if (!backendOnline.value || currentView.value !== 'events') {
    return
  }
  if (eventManageSearchTimer !== undefined) {
    window.clearTimeout(eventManageSearchTimer)
  }
  eventManageSearchTimer = window.setTimeout(() => {
    void fetchManageEvents(1)
  }, 250)
})

watch(eventManageFilterStatus, () => {
  eventManagePage.value = 1
  eventManageJumpPage.value = '1'
  selectedManageEventIds.value = []
  if (!backendOnline.value || currentView.value !== 'events') {
    return
  }
  void fetchManageEvents(1)
})

watch([eventManageTimeFrom, eventManageTimeTo], () => {
  eventManagePage.value = 1
  eventManageJumpPage.value = '1'
  if (!backendOnline.value || currentView.value !== 'events') {
    return
  }
  void fetchManageEvents(1)
})

watch(questionManageSearchKeyword, () => {
  questionManagePage.value = 1
  questionManageJumpPage.value = '1'
  selectedManageQuestionIds.value = []
  if (!backendOnline.value || currentView.value !== 'questions') {
    return
  }
  if (questionManageSearchTimer !== undefined) {
    window.clearTimeout(questionManageSearchTimer)
  }
  questionManageSearchTimer = window.setTimeout(() => {
    void fetchManageQuestions(1)
  }, 250)
})

watch(templateManageSearchKeyword, () => {
  templateManagePage.value = 1
  templateManageJumpPage.value = '1'
  selectedManageTemplateIds.value = []
  if (!backendOnline.value || currentView.value !== 'templates') {
    return
  }
  void fetchTemplates(1)
})

watch(questionEventSearch, (keyword) => {
  if (!createQuestionDialogOpen.value || !backendOnline.value) {
    return
  }
  if (questionEventSearchTimer !== undefined) {
    window.clearTimeout(questionEventSearchTimer)
  }
  questionEventSearchTimer = window.setTimeout(() => {
    void fetchQuestionEventOptions(keyword)
  }, 250)
})

watch(backendOnline, (online) => {
  scheduleTopMetricRefresh(0)
  if (!isAuthenticated.value) {
    return
  }
  if (online && currentView.value === 'events') {
    void fetchManageEvents(1)
  }
  if (online && currentView.value === 'questions') {
    void fetchManageQuestions(1)
  }
  if (currentView.value === 'questionStream') {
    resetQuestionFeed()
    void loadQuestionFeedNextPage()
  }
  if (online && currentView.value === 'templates') {
    void fetchTemplates(1)
  }
  if (online && createQuestionDialogOpen.value) {
    void fetchQuestionEventOptions(questionEventSearch.value)
  }
})

watch(isAuthenticated, (authenticated) => {
  if (!authenticated) {
    authDialogOpen.value = true
    backendOnline.value = false
    currentView.value = 'home'
    return
  }
  authDialogOpen.value = false
  void hydrateFromBackend()
})

watch(backendStatus, (status, prev) => {
  if (!status || status === prev) {
    return
  }
  pushToast(status)
  scheduleTopMetricRefresh()
})
</script>

<template>
  <div class="mission-shell">
    <TopbarPanel
      :current-user-label="isAuthenticated ? `${authUser?.username}（${authUser?.role}）` : '未登录'"
      :is-authenticated="isAuthenticated"
      @open-auth="authDialogOpen = true"
      @logout="logout"
    />

    <div class="workspace-shell">
      <SidebarNav :current-view="currentView" :is-admin="isAdmin" @update:view="currentView = $event" />

      <div class="workspace-main">
        <main v-if="currentView === 'home'" class="home-stack">
          <article class="panel">
            <div class="panel-head">
              <h2>事件监看</h2>
            </div>
            <div v-if="!homeHasEvents" class="empty-state">暂无事件数据</div>
            <ul v-else class="event-list home-event-grid">
              <li
                v-for="eventItem in previewEvents"
                :key="eventItem.id"
                :class="['event-card', { active: eventItem.id === selectedEventId }]"
                @click="selectEvent(eventItem.id)"
              >
                <div class="row-between">
                  <strong>{{ eventItem.title }}</strong>
                  <div class="tag-group">
                    <span :class="['badge', severityBadgeTone(eventItem.severity)]">{{ severityLabel[eventItem.severity] }}</span>
                    <span :class="['badge', eventFilterBadgeTone(eventItem.filterStatus)]">{{ eventItem.filterStatus }}</span>
                  </div>
                </div>
                <p>{{ eventItem.theater }}</p>
                <small>{{ eventItem.summary }}</small>
                <div v-if="eventItem.tags.length > 0" class="tag-group">
                  <span v-for="tag in eventItem.tags" :key="`home-tag-${eventItem.id}-${tag}`" class="badge">
                    {{ tag }}
                  </span>
                </div>
                <span class="time">{{ formatDate(eventItem.timestamp) }}</span>
                <div class="action-row action-right">
                  <button class="action-btn mini-btn" @click.stop="openHomeDetail(eventItem)">详情</button>
                </div>
              </li>
            </ul>
            <div class="action-row pagination-row pagination-center mini-pagination">
              <button class="action-btn mini-btn" @click="goHomeEventPage(-1)">上一页</button>
              <span>{{ homeEventPage }} / {{ homeEventTotalPages }}</span>
              <input v-model="homeEventJumpPage" class="jump-input mini-jump-input" placeholder="页码" />
              <button class="action-btn mini-btn" @click="jumpToHomeEventPageFromInput">跳转</button>
              <button class="action-btn mini-btn" @click="goHomeEventPage(1)">下一页</button>
            </div>
          </article>

          <article class="panel">
            <div class="panel-head">
              <h2>模型排行榜</h2>
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

            <div v-if="!hasDisplayedRanking" class="empty-state">暂无模型排行数据</div>
            <div v-else class="home-rank-grid">
              <article v-for="row in displayedRanking" :key="`${row.model}-${row.level}`" class="rank-card">
                <div class="row-between">
                  <strong>{{ row.model }}</strong>
                  <span class="badge">{{ row.level }}</span>
                </div>
                <p class="rank-score">{{ row.score.toFixed(1) }}</p>
                <small class="rank-meta">准确率 {{ row.accuracy }}%</small>
                <small class="rank-meta">耗时 {{ row.avgLatency }}ms</small>
              </article>
            </div>
          </article>
        </main>

    <ManageEventsPanel
      v-if="currentView === 'events'"
      :event-manage-page="eventManagePage"
      :event-manage-total-pages="eventManageTotalPages"
      :all-events-on-page-selected="allEventsOnPageSelected"
      :event-review-processing="eventReviewProcessing"
      :event-manage-search-keyword="eventManageSearchKeyword"
      :event-manage-filter-status="eventManageFilterStatus"
      :event-manage-time-from="eventManageTimeFrom"
      :event-manage-time-to="eventManageTimeTo"
      :event-manage-search-loading="eventManageSearchLoading"
      :backend-online="backendOnline"
      :manage-event-total="manageEventTotal"
      :local-filtered-manage-events-length="localFilteredManageEvents.length"
      :skeleton-rows="skeletonRows"
      :has-manage-events="hasManageEvents"
      :paged-manage-events="pagedManageEvents"
      :selected-event-id="selectedEventId"
      :selected-manage-event-ids="selectedManageEventIds"
      :event-manage-page-size="eventManagePageSize"
      :event-manage-page-size-options="eventManagePageSizeOptions"
      :event-manage-jump-page="eventManageJumpPage"
      @open-create-event="createEventDialogOpen = true; void fetchSourceSystemOptions()"
      @toggle-select-all="toggleSelectAllEventsOnPage"
      @review-events="reviewSelectedEvents"
      @delete-selected-batch="deleteSelectedEventsBatch"
      @update:search-keyword="eventManageSearchKeyword = $event"
      @update:filter-status="eventManageFilterStatus = $event"
      @update:time-from="eventManageTimeFrom = $event"
      @update:time-to="eventManageTimeTo = $event"
      @select-event="selectEvent"
      @open-manage-detail="openManageDetail"
      @toggle-selection="toggleManageEventSelection"
      @open-edit="openEventEdit"
      @set-page-size="setEventManagePageSize"
      @go-page="goManageEventPage"
      @update:jump-page="eventManageJumpPage = $event"
      @jump-to-page="jumpToEventPageFromInput"
    />

    <ManageQuestionsPanel
      v-if="currentView === 'questions'"
      :question-manage-page="questionManagePage"
      :question-manage-total-pages="questionManageTotalPages"
      :all-questions-on-page-selected="allQuestionsOnPageSelected"
      :question-manage-search-keyword="questionManageSearchKeyword"
      :question-manage-search-loading="questionManageSearchLoading"
      :backend-online="backendOnline"
      :question-manage-total="questionManageTotal"
      :local-filtered-manage-questions-length="localFilteredManageQuestions.length"
      :skeleton-rows="skeletonRows"
      :has-manage-questions="hasManageQuestions"
      :paged-manage-questions="pagedManageQuestions"
      :selected-question-id="selectedQuestionId"
      :selected-manage-question-ids="selectedManageQuestionIds"
      :question-manage-page-size="questionManagePageSize"
      :question-manage-jump-page="questionManageJumpPage"
      :all-known-events="allKnownEvents"
      @open-create-question="openCreateQuestionDialog"
      @toggle-select-all="toggleSelectAllQuestionsOnPage"
      @delete-selected-batch="deleteSelectedQuestionsBatch"
      @update:search-keyword="questionManageSearchKeyword = $event"
      @select-question="selectedQuestionId = $event"
      @open-manage-detail="openManageQuestionDetail"
      @toggle-selection="toggleManageQuestionSelection"
      @open-edit="openQuestionEdit"
      @set-page-size="setQuestionManagePageSize"
      @go-page="goManageQuestionPage"
      @update:jump-page="questionManageJumpPage = $event"
      @jump-to-page="jumpToQuestionPageFromInput"
    />

    <QuestionFeedPanel
      v-if="currentView === 'questionStream'"
      :items="questionFeedItems"
      :loading="questionFeedLoading"
      :has-more="questionFeedHasMore"
      :backend-online="backendOnline"
      :all-known-events="allKnownEvents"
      @load-more="loadQuestionFeedNextPage"
      @open-question="openManageQuestionDetail"
    />

    <ManageTemplatesPanel
      v-if="currentView === 'templates'"
      :template-manage-page="templateManagePage"
      :template-manage-total-pages="templateManageTotalPages"
      :all-templates-on-page-selected="allTemplatesOnPageSelected"
      :template-manage-search-keyword="templateManageSearchKeyword"
      :template-manage-total="templateManageTotal"
      :has-templates="hasTemplates"
      :templates="templates"
      :selected-template-id="selectedTemplate?.id ?? ''"
      :selected-manage-template-ids="selectedManageTemplateIds"
      :template-manage-page-size="templateManagePageSize"
      :template-manage-jump-page="templateManageJumpPage"
      @open-create-template="createTemplateDialogOpen = true"
      @toggle-select-all="toggleSelectAllTemplatesOnPage"
      @delete-selected-batch="deleteSelectedTemplatesBatch"
      @update:search-keyword="templateManageSearchKeyword = $event"
      @open-detail="openTemplateDetail"
      @toggle-selection="toggleManageTemplateSelection"
      @open-edit="openTemplateEdit"
      @set-page-size="setTemplateManagePageSize"
      @go-page="goTemplateManagePage"
      @update:jump-page="templateManageJumpPage = $event"
      @jump-to-page="jumpToTemplatePageFromInput"
    />

    <ManageTasksPanel
      v-if="currentView === 'tasks'"
      :auto-review-processing="autoReviewProcessing"
      :all-tasks-on-page-selected="allTasksOnPageSelected"
      :has-tasks="hasTasks"
      :tasks="tasks"
      :selected-task-id="selectedTask?.id ?? ''"
      :selected-manage-task-ids="selectedManageTaskIds"
      :task-manage-page-size="taskManagePageSize"
      :task-manage-jump-page="taskManageJumpPage"
      @open-trigger-pull="triggerPullDialogOpen = true; void fetchSourceSystemOptions()"
      @trigger-auto-review="triggerAutoReviewNow"
      @open-create-task="createTaskDialogOpen = true"
      @toggle-select-all="toggleSelectAllTasksOnPage"
      @delete-selected-batch="deleteSelectedTasksBatch"
      @open-detail="openTaskDetail"
      @toggle-selection="toggleManageTaskSelection"
      @set-page-size="setTaskManagePageSize"
      @go-page="goTaskManagePage"
      @update:jump-page="taskManageJumpPage = $event"
      @jump-to-page="jumpToTaskPageFromInput"
    />

    <ManageDataSourcesPanel
      v-if="currentView === 'dataSources'"
      :all-data-sources-on-page-selected="allDataSourcesOnPageSelected"
      :has-data-sources="hasDataSources"
      :data-sources="dataSources"
      :selected-data-source-id="selectedDataSource?.id ?? ''"
      :selected-manage-data-source-ids="selectedManageDataSourceIds"
      :data-source-manage-page-size="dataSourceManagePageSize"
      :data-source-manage-jump-page="dataSourceManageJumpPage"
      @open-create="createDataSourceDialogOpen = true"
      @toggle-select-all="toggleSelectAllDataSourcesOnPage"
      @delete-selected-batch="deleteSelectedDataSourcesBatch"
      @open-detail="openDataSourceDetail"
      @toggle-selection="toggleManageDataSourceSelection"
      @open-edit="openDataSourceEdit"
      @set-page-size="setDataSourceManagePageSize"
      @go-page="goDataSourceManagePage"
      @update:jump-page="dataSourceManageJumpPage = $event"
      @jump-to-page="jumpToDataSourcePageFromInput"
    />

    <ManageFilterRulesPanel
      v-if="currentView === 'filterRules'"
      :all-filter-rules-on-page-selected="allFilterRulesOnPageSelected"
      :has-filter-rules="hasFilterRules"
      :filter-rules="filterRules"
      :selected-filter-rule-id="selectedFilterRule?.id ?? ''"
      :selected-manage-filter-rule-ids="selectedManageFilterRuleIds"
      :filter-rule-manage-page-size="filterRuleManagePageSize"
      :filter-rule-manage-jump-page="filterRuleManageJumpPage"
      @open-create="createFilterRuleDialogOpen = true"
      @toggle-select-all="toggleSelectAllFilterRulesOnPage"
      @delete-selected-batch="deleteSelectedFilterRulesBatch"
      @open-detail="openFilterRuleDetail"
      @toggle-selection="toggleManageFilterRuleSelection"
      @open-edit="openFilterRuleEdit"
      @set-page-size="setFilterRuleManagePageSize"
      @go-page="goFilterRuleManagePage"
      @update:jump-page="filterRuleManageJumpPage = $event"
      @jump-to-page="jumpToFilterRulePageFromInput"
    />
      </div>

    </div>

    <div v-if="taskDetailDialogOpen && selectedTaskDetail" class="dialog-backdrop" @click.self="taskDetailDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>任务执行详情</h2>
          <div class="action-row">
            <button class="action-btn" @click="taskDetailDialogOpen = false">关闭</button>
          </div>
        </div>
        <div class="detail-grid">
          <p><strong>任务ID：</strong>{{ selectedTaskDetail.task_id }}</p>
          <p><strong>任务类型：</strong>{{ selectedTaskDetail.task_type }}</p>
          <p><strong>状态：</strong>{{ selectedTaskDetail.status }}</p>
          <p><strong>幂等键：</strong>{{ selectedTaskDetail.idempotency_key }}</p>
          <p><strong>尝试次数：</strong>{{ selectedTaskDetail.attempt_count }}</p>
          <p><strong>创建时间：</strong>{{ formatDate(selectedTaskDetail.created_at) }}</p>
          <p><strong>开始时间：</strong>{{ selectedTaskDetail.started_at ? formatDate(selectedTaskDetail.started_at) : '-' }}</p>
          <p><strong>结束时间：</strong>{{ selectedTaskDetail.finished_at ? formatDate(selectedTaskDetail.finished_at) : '-' }}</p>
          <p><strong>下次重试：</strong>{{ selectedTaskDetail.next_retry_at ? formatDate(selectedTaskDetail.next_retry_at) : '-' }}</p>
          <p><strong>错误信息：</strong>{{ selectedTaskDetail.error_message ?? '-' }}</p>
          <p><strong>结果：</strong>{{ JSON.stringify(selectedTaskDetail.result) }}</p>
          <p><strong>指标：</strong>{{ JSON.stringify(selectedTaskDetail.metrics) }}</p>
        </div>
      </section>
    </div>

    <div v-if="createTaskDialogOpen" class="dialog-backdrop" @click.self="createTaskDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>新增任务</h2>
          <button class="action-btn" @click="createTaskDialogOpen = false">关闭</button>
        </div>
        <div class="field-block">
          <label>任务类型</label>
          <input v-model="createTaskForm.taskType" placeholder="例如 s1_ingest_pull" />
        </div>
        <div class="field-block">
          <label>幂等键</label>
          <input v-model="createTaskForm.idempotencyKey" placeholder="手动输入唯一键" />
        </div>
        <div class="field-block">
          <label>Trace ID（可选，不填自动生成）</label>
          <input v-model="createTaskForm.traceId" placeholder="UUID" />
        </div>
        <div class="action-row action-right">
          <button class="action-btn" @click="submitCreateTask">提交任务</button>
        </div>
      </section>
    </div>

    <div v-if="triggerPullDialogOpen" class="dialog-backdrop" @click.self="triggerPullDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>拉取烽火事件</h2>
          <button class="action-btn" @click="triggerPullDialogOpen = false">关闭</button>
        </div>
        <div class="field-block">
          <label>来源系统（可选）</label>
          <select v-model="triggerPullForm.sourceSystem">
            <option value="">默认数据源（配置项）</option>
            <option v-for="source in sourceSystemOptions" :key="`pull-source-${source}`" :value="source">
              {{ source }}
            </option>
          </select>
        </div>
        <div class="action-row action-right">
          <button class="action-btn" @click="triggerPullNow">立即拉取</button>
        </div>
      </section>
    </div>

    <div v-if="dataSourceDetailDialogOpen && selectedDataSource" class="dialog-backdrop" @click.self="dataSourceDetailDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>数据源详情</h2>
          <div class="action-row">
            <button class="action-btn" @click="openDataSourceEdit(selectedDataSource)">编辑</button>
            <button class="action-btn" @click="dataSourceDetailDialogOpen = false">关闭</button>
          </div>
        </div>
        <div class="detail-grid">
          <p><strong>ID：</strong>{{ selectedDataSource.id }}</p>
          <p><strong>名称：</strong>{{ selectedDataSource.name }}</p>
          <p><strong>source_system：</strong>{{ selectedDataSource.sourceSystem }}</p>
          <p><strong>来源类型：</strong>{{ selectedDataSource.sourceType }}</p>
          <p><strong>可信度：</strong>{{ selectedDataSource.credibilityLevel }}</p>
          <p><strong>同步频率：</strong>{{ selectedDataSource.syncFrequency }}</p>
          <p><strong>启用状态：</strong>{{ selectedDataSource.isActive ? 'active' : 'inactive' }}</p>
          <p><strong>版本：</strong>{{ selectedDataSource.version }}</p>
          <p><strong>Secret Ref：</strong>{{ selectedDataSource.secretRef ?? '-' }}</p>
          <p><strong>连接配置：</strong>{{ JSON.stringify(selectedDataSource.connectionConfig) }}</p>
          <p><strong>创建时间：</strong>{{ formatDate(selectedDataSource.createdAt) }}</p>
          <p><strong>更新时间：</strong>{{ formatDate(selectedDataSource.updatedAt) }}</p>
        </div>
      </section>
    </div>

    <div v-if="createDataSourceDialogOpen" class="dialog-backdrop" @click.self="createDataSourceDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>新增数据源</h2>
          <button class="action-btn" @click="createDataSourceDialogOpen = false">关闭</button>
        </div>
        <div class="field-block"><label>名称</label><input v-model="createDataSourceForm.name" /></div>
        <div class="field-block"><label>source_system</label><input v-model="createDataSourceForm.sourceSystem" /></div>
        <div class="field-block">
          <label>来源类型</label>
          <select v-model="createDataSourceForm.sourceType">
            <option value="api">api</option>
            <option value="database">database</option>
            <option value="file">file</option>
            <option value="websocket">websocket</option>
          </select>
        </div>
        <div class="field-block"><label>connection_config(JSON)</label><textarea v-model="createDataSourceForm.connectionConfig" rows="4"></textarea></div>
        <div class="field-block"><label>secret_ref</label><input v-model="createDataSourceForm.secretRef" /></div>
        <div class="field-block"><label>可信度</label><input v-model.number="createDataSourceForm.credibilityLevel" type="number" min="1" max="5" /></div>
        <div class="field-block"><label>同步频率</label><input v-model="createDataSourceForm.syncFrequency" placeholder="1 hour" /></div>
        <div class="field-block"><label>版本</label><input v-model="createDataSourceForm.version" /></div>
        <div class="field-block">
          <label>启用状态</label>
          <select v-model="createDataSourceForm.isActive">
            <option :value="true">active</option>
            <option :value="false">inactive</option>
          </select>
        </div>
        <div class="action-row action-right">
          <button class="action-btn" @click="submitCreateDataSource">提交</button>
        </div>
      </section>
    </div>

    <div v-if="editDataSourceDialogOpen" class="dialog-backdrop" @click.self="editDataSourceDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>编辑数据源</h2>
          <button class="action-btn" @click="editDataSourceDialogOpen = false">关闭</button>
        </div>
        <div class="field-block"><label>名称</label><input v-model="editDataSourceForm.name" /></div>
        <div class="field-block"><label>source_system</label><input v-model="editDataSourceForm.sourceSystem" /></div>
        <div class="field-block">
          <label>来源类型</label>
          <select v-model="editDataSourceForm.sourceType">
            <option value="api">api</option>
            <option value="database">database</option>
            <option value="file">file</option>
            <option value="websocket">websocket</option>
          </select>
        </div>
        <div class="field-block"><label>connection_config(JSON)</label><textarea v-model="editDataSourceForm.connectionConfig" rows="4"></textarea></div>
        <div class="field-block"><label>secret_ref</label><input v-model="editDataSourceForm.secretRef" /></div>
        <div class="field-block"><label>可信度</label><input v-model.number="editDataSourceForm.credibilityLevel" type="number" min="1" max="5" /></div>
        <div class="field-block"><label>同步频率</label><input v-model="editDataSourceForm.syncFrequency" /></div>
        <div class="field-block"><label>版本</label><input v-model="editDataSourceForm.version" /></div>
        <div class="field-block">
          <label>启用状态</label>
          <select v-model="editDataSourceForm.isActive">
            <option :value="true">active</option>
            <option :value="false">inactive</option>
          </select>
        </div>
        <div class="action-row action-right">
          <button class="action-btn" @click="submitEditDataSource">保存</button>
          <button class="action-btn danger" @click="deleteDataSourceInEditDialog">删除</button>
        </div>
      </section>
    </div>

    <div v-if="filterRuleDetailDialogOpen && selectedFilterRule" class="dialog-backdrop" @click.self="filterRuleDetailDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>过滤规则详情</h2>
          <div class="action-row">
            <button class="action-btn" @click="openFilterRuleEdit(selectedFilterRule)">编辑</button>
            <button class="action-btn" @click="filterRuleDetailDialogOpen = false">关闭</button>
          </div>
        </div>
        <div class="detail-grid">
          <p><strong>ID：</strong>{{ selectedFilterRule.id }}</p>
          <p><strong>名称：</strong>{{ selectedFilterRule.name }}</p>
          <p><strong>等级：</strong>{{ selectedFilterRule.level }}</p>
          <p><strong>表达式：</strong>{{ selectedFilterRule.filterExpression }}</p>
          <p><strong>规则归属：</strong>{{ selectedFilterRule.ruleScope }}</p>
          <p><strong>提示词列表：</strong>{{ selectedFilterRule.filterPrompts.join(' | ') || '-' }}</p>
          <div>
            <strong>配置：</strong>
            <div v-if="filterConfigDisplayEntries(selectedFilterRule.filterConfig).length === 0">-</div>
            <div
              v-for="(entry, index) in filterConfigDisplayEntries(selectedFilterRule.filterConfig)"
              :key="`detail-config-${index}`"
            >
              {{ entry.key }} = {{ entry.value }}
            </div>
          </div>
          <p><strong>优先级：</strong>{{ selectedFilterRule.priority }}</p>
          <p><strong>状态：</strong>{{ selectedFilterRule.status }}</p>
          <p><strong>版本：</strong>{{ selectedFilterRule.version }}</p>
          <p><strong>创建时间：</strong>{{ formatDate(selectedFilterRule.createdAt) }}</p>
          <p><strong>更新时间：</strong>{{ formatDate(selectedFilterRule.updatedAt) }}</p>
        </div>
      </section>
    </div>

    <div v-if="createFilterRuleDialogOpen" class="dialog-backdrop" @click.self="createFilterRuleDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>新增过滤规则</h2>
          <button class="action-btn" @click="createFilterRuleDialogOpen = false">关闭</button>
        </div>
        <div class="field-block"><label>名称</label><input v-model="createFilterRuleForm.name" /></div>
        <div class="field-block"><label>等级</label><input v-model.number="createFilterRuleForm.level" type="number" min="1" max="4" /></div>
        <div class="field-block">
          <label>规则归属</label>
          <select v-model="createFilterRuleForm.ruleScope">
            <option v-for="scope in filterRuleScopes" :key="scope" :value="scope">{{ scope }}</option>
          </select>
        </div>
        <div class="field-block">
          <label>表达式</label>
          <select v-model="createFilterRuleForm.filterExpression">
            <option value="keyword_include">keyword_include</option>
            <option value="keyword_exclude">keyword_exclude</option>
            <option value="credibility_min">credibility_min</option>
            <option value="event_time_within_hours">event_time_within_hours</option>
            <option value="content_length_min">content_length_min</option>
          </select>
        </div>
        <div class="field-block">
          <label>提示词列表（可空）</label>
          <div v-for="(_, index) in createFilterRuleForm.filterPrompts" :key="`create-prompt-${index}`" class="prompt-row">
            <input v-model="createFilterRuleForm.filterPrompts[index]" placeholder="输入一条提示词" />
            <button class="action-btn" @click="removeCreateFilterPromptRow(index)">-</button>
          </div>
          <button class="action-btn" @click="addCreateFilterPromptRow">+ 添加提示词</button>
        </div>
        <div class="field-block">
          <label>规则配置（键值，可空）</label>
          <div
            v-for="(item, index) in createFilterRuleForm.filterConfigItems"
            :key="`create-config-${index}`"
            class="prompt-row"
          >
            <input v-model="item.key" placeholder="key，如 keywords" />
            <input v-model="item.value" placeholder="value，可写文本或 JSON（如 [rumor]）" />
            <button class="action-btn" @click="removeCreateFilterConfigRow(index)">-</button>
          </div>
          <button class="action-btn" @click="addCreateFilterConfigRow">+ 添加配置项</button>
        </div>
        <div class="field-block"><label>优先级</label><input v-model.number="createFilterRuleForm.priority" type="number" /></div>
        <div class="field-block">
          <label>状态</label>
          <select v-model="createFilterRuleForm.status">
            <option value="active">active</option>
            <option value="inactive">inactive</option>
            <option value="archived">archived</option>
          </select>
        </div>
        <div class="field-block"><label>版本</label><input v-model="createFilterRuleForm.version" /></div>
        <div class="action-row action-right">
          <button class="action-btn" @click="submitCreateFilterRule">提交</button>
        </div>
      </section>
    </div>

    <div v-if="editFilterRuleDialogOpen" class="dialog-backdrop" @click.self="editFilterRuleDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>编辑过滤规则</h2>
          <button class="action-btn" @click="editFilterRuleDialogOpen = false">关闭</button>
        </div>
        <div class="field-block"><label>名称</label><input v-model="editFilterRuleForm.name" /></div>
        <div class="field-block"><label>等级</label><input v-model.number="editFilterRuleForm.level" type="number" min="1" max="4" /></div>
        <div class="field-block">
          <label>规则归属</label>
          <select v-model="editFilterRuleForm.ruleScope">
            <option v-for="scope in filterRuleScopes" :key="scope" :value="scope">{{ scope }}</option>
          </select>
        </div>
        <div class="field-block">
          <label>表达式</label>
          <select v-model="editFilterRuleForm.filterExpression">
            <option value="keyword_include">keyword_include</option>
            <option value="keyword_exclude">keyword_exclude</option>
            <option value="credibility_min">credibility_min</option>
            <option value="event_time_within_hours">event_time_within_hours</option>
            <option value="content_length_min">content_length_min</option>
          </select>
        </div>
        <div class="field-block">
          <label>提示词列表（可空）</label>
          <div v-for="(_, index) in editFilterRuleForm.filterPrompts" :key="`edit-prompt-${index}`" class="prompt-row">
            <input v-model="editFilterRuleForm.filterPrompts[index]" placeholder="输入一条提示词" />
            <button class="action-btn" @click="removeEditFilterPromptRow(index)">-</button>
          </div>
          <button class="action-btn" @click="addEditFilterPromptRow">+ 添加提示词</button>
        </div>
        <div class="field-block">
          <label>规则配置（键值，可空）</label>
          <div
            v-for="(item, index) in editFilterRuleForm.filterConfigItems"
            :key="`edit-config-${index}`"
            class="prompt-row"
          >
            <input v-model="item.key" placeholder="key，如 keywords" />
            <input v-model="item.value" placeholder="value，可写文本或 JSON（如 [rumor]）" />
            <button class="action-btn" @click="removeEditFilterConfigRow(index)">-</button>
          </div>
          <button class="action-btn" @click="addEditFilterConfigRow">+ 添加配置项</button>
        </div>
        <div class="field-block"><label>优先级</label><input v-model.number="editFilterRuleForm.priority" type="number" /></div>
        <div class="field-block">
          <label>状态</label>
          <select v-model="editFilterRuleForm.status">
            <option value="active">active</option>
            <option value="inactive">inactive</option>
            <option value="archived">archived</option>
          </select>
        </div>
        <div class="field-block"><label>版本</label><input v-model="editFilterRuleForm.version" /></div>
        <div class="action-row action-right">
          <button class="action-btn" @click="submitEditFilterRule">保存</button>
          <button class="action-btn danger" @click="deleteFilterRuleInEditDialog">删除</button>
        </div>
      </section>
    </div>

    <div v-if="homeDetailDialogOpen && homeDetailEvent" class="dialog-backdrop" @click.self="homeDetailDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>事件详情（只读）</h2>
          <button class="action-btn" @click="homeDetailDialogOpen = false">关闭</button>
        </div>
        <div class="detail-grid">
          <p><strong>ID：</strong>{{ homeDetailEvent.id }}</p>
          <p><strong>标题：</strong>{{ homeDetailEvent.title }}</p>
          <p><strong>event_key：</strong>{{ homeDetailEvent.codename }}</p>
          <p><strong>来源系统：</strong>{{ homeDetailEvent.theater }}</p>
          <p><strong>可信等级：</strong>{{ severityLabel[homeDetailEvent.severity] }}</p>
          <p><strong>filter_status：</strong>{{ homeDetailEvent.filterStatus }}</p>
          <p><strong>tags：</strong>{{ homeDetailEvent.tags.length > 0 ? homeDetailEvent.tags.join(', ') : '-' }}</p>
          <p><strong>事件时间：</strong>{{ formatDate(homeDetailEvent.timestamp) }}</p>
          <p><strong>内容：</strong>{{ homeDetailEvent.summary }}</p>
        </div>
      </section>
    </div>

    <div v-if="eventDetailDialogOpen && manageDetailEvent" class="dialog-backdrop" @click.self="eventDetailDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>事件详情（只读）</h2>
          <div class="action-row">
            <button class="action-btn" @click="openEventEdit(manageDetailEvent)">编辑</button>
            <button class="action-btn" @click="eventDetailDialogOpen = false">关闭</button>
          </div>
        </div>
        <div class="detail-grid">
          <p><strong>ID：</strong>{{ manageDetailEvent.id }}</p>
          <p><strong>标题：</strong>{{ manageDetailEvent.title }}</p>
          <p><strong>event_key：</strong>{{ manageDetailEvent.codename }}</p>
          <p><strong>来源系统：</strong>{{ manageDetailEvent.theater }}</p>
          <p><strong>可信等级：</strong>{{ severityLabel[manageDetailEvent.severity] }}</p>
          <p><strong>filter_status：</strong>{{ manageDetailEvent.filterStatus }}</p>
          <p><strong>tags：</strong>{{ manageDetailEvent.tags.length > 0 ? manageDetailEvent.tags.join(', ') : '-' }}</p>
          <p><strong>事件时间：</strong>{{ formatDate(manageDetailEvent.timestamp) }}</p>
          <p><strong>内容：</strong>{{ manageDetailEvent.summary }}</p>
        </div>
      </section>
    </div>

    <div v-if="eventEditDialogOpen" class="dialog-backdrop" @click.self="eventEditDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>编辑事件</h2>
          <button class="action-btn" @click="eventEditDialogOpen = false">关闭</button>
        </div>
        <div class="field-block">
          <label>事件标题</label>
          <input v-model="eventEditForm.title" />
        </div>
        <div class="field-block">
          <label>来源系统 / 战区</label>
          <select v-model="eventEditForm.theater">
            <option value="" disabled>请选择数据源</option>
            <option
              v-if="eventEditForm.theater && !sourceSystemOptions.includes(eventEditForm.theater)"
              :value="eventEditForm.theater"
            >
              {{ eventEditForm.theater }}
            </option>
            <option v-for="source in sourceSystemOptions" :key="`event-edit-source-${source}`" :value="source">
              {{ source }}
            </option>
          </select>
        </div>
        <div class="field-block">
          <label>事件内容</label>
          <textarea v-model="eventEditForm.summary" rows="3"></textarea>
        </div>
        <div class="field-block">
          <label>可信等级映射</label>
          <select v-model="eventEditForm.severity">
            <option value="low">低</option>
            <option value="medium">中</option>
            <option value="high">高</option>
          </select>
        </div>
        <div class="field-block">
          <label>filter_status</label>
          <select v-model="eventEditForm.filterStatus">
            <option value="" disabled>请选择状态</option>
            <option
              v-if="eventEditForm.filterStatus && !['pending', 'passed', 'filtered'].includes(eventEditForm.filterStatus)"
              :value="eventEditForm.filterStatus"
            >
              {{ eventEditForm.filterStatus }}
            </option>
            <option value="pending">pending</option>
            <option value="passed">passed</option>
            <option value="filtered">filtered</option>
          </select>
        </div>
        <div class="action-row">
          <button class="action-btn" @click="submitEventEdit">保存修改</button>
          <button class="action-btn danger" @click="deleteEventInEditDialog">删除该事件</button>
        </div>
      </section>
    </div>

    <div v-if="questionDetailDialogOpen && manageDetailQuestion" class="dialog-backdrop" @click.self="questionDetailDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>问题详情（只读）</h2>
          <div class="action-row">
            <button class="action-btn" @click="openQuestionEdit(manageDetailQuestion!)">编辑</button>
            <button class="action-btn" @click="questionDetailDialogOpen = false">关闭</button>
          </div>
        </div>
        <div class="detail-grid">
          <p><strong>ID：</strong>{{ manageDetailQuestion.id }}</p>
          <p>
            <strong>关联事件：</strong>
            {{
              (manageDetailQuestion?.eventIds ?? [])
                .map((eventId) => allKnownEvents.find((item) => item.id === eventId)?.title)
                .filter((title): title is string => Boolean(title))
                .join('、') || '未匹配事件'
            }}
          </p>
          <p><strong>等级：</strong>{{ manageDetailQuestion.level }}</p>
          <p><strong>状态：</strong>{{ statusLabel[manageDetailQuestion.status] }}</p>
          <p><strong>截止时间：</strong>{{ formatDate(manageDetailQuestion.deadline) }}</p>
          <p><strong>标题：</strong>{{ manageDetailQuestion.title }}</p>
          <p><strong>答案范围：</strong>{{ manageDetailQuestion.answerSpace || '未填写' }}</p>
          <p><strong>假设：</strong>{{ manageDetailQuestion.hypothesis }}</p>
          <p><strong>真实结果：</strong>{{ manageDetailQuestion.groundTruth }}</p>
        </div>
      </section>
    </div>

    <div v-if="questionEditDialogOpen" class="dialog-backdrop" @click.self="questionEditDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>编辑问题</h2>
          <button class="action-btn" @click="questionEditDialogOpen = false">关闭</button>
        </div>
        <div class="field-block">
          <label>问题标题</label>
          <input v-model="questionEditForm.title" />
        </div>
        <div class="field-block">
          <label>关联事件（可多选）</label>
          <input v-model="questionEditEventSearch" placeholder="搜索可关联事件（标题/战区/内容）" />
          <div class="question-event-multi-select">
            <label v-for="eventItem in filteredKnownEventsForQuestionEdit" :key="`question-edit-target-${eventItem.id}`" class="select-row question-event-option">
              <input
                type="checkbox"
                :checked="questionEditForm.eventIds.includes(eventItem.id)"
                @change="toggleQuestionEditEventSelection(eventItem.id)"
              />
              <span>{{ eventItem.title }}（{{ eventItem.theater }}）</span>
            </label>
            <p v-if="filteredKnownEventsForQuestionEdit.length === 0" class="item-subtle">无匹配事件</p>
          </div>
        </div>
        <div class="field-block">
          <label>问题等级</label>
          <select v-model="questionEditForm.level">
            <option v-for="level in levels" :key="`edit-question-${level}`" :value="level">{{ level }}</option>
          </select>
        </div>
        <div v-if="questionEditForm.level === 'L1' || questionEditForm.level === 'L2'" class="field-block">
          <label>答案范围（L1/L2 必填）</label>
          <textarea v-model="questionEditForm.answerSpace" rows="2" placeholder="请输入候选答案文本"></textarea>
        </div>
        <div class="field-block">
          <label>截止时间（ISO）</label>
          <input v-model="questionEditForm.deadline" type="datetime-local" />
        </div>
        <div class="field-block">
          <label>状态</label>
          <select v-model="questionEditForm.status">
            <option value="collecting">收集中</option>
            <option value="locked">已封存</option>
            <option value="resolved">已解析</option>
          </select>
        </div>
        <div class="action-row">
          <button class="action-btn" @click="submitQuestionEdit">保存修改</button>
          <button class="action-btn danger" @click="deleteQuestionInEditDialog">删除该问题</button>
        </div>
      </section>
    </div>

    <div
      v-if="templateDetailDialogOpen && selectedTemplateDetail"
      class="dialog-backdrop"
      @click.self="templateDetailDialogOpen = false"
    >
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>模板详情</h2>
          <div class="action-row">
            <button class="action-btn" @click="openTemplateEdit(selectedTemplateDetail)">编辑</button>
            <button class="action-btn" @click="templateDetailDialogOpen = false">关闭</button>
          </div>
        </div>
        <div class="detail-grid">
          <p><strong>ID：</strong>{{ selectedTemplateDetail.id }}</p>
          <p><strong>问题模板：</strong>{{ selectedTemplateDetail.questionTemplate }}</p>
          <p><strong>大类主题：</strong>{{ selectedTemplateDetail.majorTopic }}</p>
          <p><strong>小类主题：</strong>{{ selectedTemplateDetail.minorTopic }}</p>
          <p><strong>难度等级：</strong>{{ selectedTemplateDetail.difficultyLevel }}</p>
          <p><strong>构题依据：</strong>{{ selectedTemplateDetail.constructionRationale }}</p>
          <p><strong>候选答案：</strong>{{ selectedTemplateDetail.candidateAnswers }}</p>
          <p><strong>答题截止：</strong>{{ formatDate(selectedTemplateDetail.answerDeadline) }}</p>
          <p><strong>状态：</strong>{{ selectedTemplateDetail.status }}</p>
          <p><strong>版本：</strong>{{ selectedTemplateDetail.version }}</p>
          <p><strong>使用次数：</strong>{{ selectedTemplateDetail.usageCount }}</p>
          <p><strong>更新时间：</strong>{{ formatDate(selectedTemplateDetail.updatedAt) }}</p>
        </div>
      </section>
    </div>

    <div v-if="templateEditDialogOpen" class="dialog-backdrop" @click.self="templateEditDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>编辑模板</h2>
          <button class="action-btn" @click="templateEditDialogOpen = false">关闭</button>
        </div>
        <div class="field-block">
          <label>问题模板</label>
          <textarea v-model="templateEditForm.questionTemplate" rows="3"></textarea>
        </div>
        <div class="field-block">
          <label>大类主题</label>
          <input v-model="templateEditForm.majorTopic" />
        </div>
        <div class="field-block">
          <label>小类主题</label>
          <input v-model="templateEditForm.minorTopic" />
        </div>
        <div class="field-block">
          <label>难度等级</label>
          <select v-model="templateEditForm.difficultyLevel">
            <option value="L1">L1</option>
            <option value="L2">L2</option>
            <option value="L3">L3</option>
            <option value="L4">L4</option>
          </select>
        </div>
        <div class="field-block">
          <label>构题依据</label>
          <textarea v-model="templateEditForm.constructionRationale" rows="3"></textarea>
        </div>
        <div class="field-block">
          <label>候选答案</label>
          <textarea v-model="templateEditForm.candidateAnswers" rows="3"></textarea>
        </div>
        <div class="field-block">
          <label>答题截止时间</label>
          <input v-model="templateEditForm.answerDeadline" type="datetime-local" />
        </div>
        <div class="field-block">
          <label>状态</label>
          <select v-model="templateEditForm.status">
            <option value="active">active</option>
            <option value="inactive">inactive</option>
            <option value="archived">archived</option>
          </select>
        </div>
        <div class="field-block">
          <label>版本</label>
          <input v-model="templateEditForm.version" />
        </div>
        <div class="action-row">
          <button class="action-btn" @click="submitEditTemplate">保存修改</button>
          <button class="action-btn danger" @click="deleteTemplateInEditDialog">删除该模板</button>
        </div>
      </section>
    </div>

    <div v-if="createTemplateDialogOpen" class="dialog-backdrop" @click.self="createTemplateDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>新增模板</h2>
          <button class="action-btn" @click="createTemplateDialogOpen = false">关闭</button>
        </div>
        <div class="field-block">
          <label>问题模板</label>
          <textarea v-model="createTemplateForm.questionTemplate" rows="3"></textarea>
        </div>
        <div class="field-block">
          <label>大类主题</label>
          <input v-model="createTemplateForm.majorTopic" />
        </div>
        <div class="field-block">
          <label>小类主题</label>
          <input v-model="createTemplateForm.minorTopic" />
        </div>
        <div class="field-block">
          <label>难度等级</label>
          <select v-model="createTemplateForm.difficultyLevel">
            <option value="L1">L1</option>
            <option value="L2">L2</option>
            <option value="L3">L3</option>
            <option value="L4">L4</option>
          </select>
        </div>
        <div class="field-block">
          <label>构题依据</label>
          <textarea v-model="createTemplateForm.constructionRationale" rows="3"></textarea>
        </div>
        <div class="field-block">
          <label>候选答案</label>
          <textarea v-model="createTemplateForm.candidateAnswers" rows="3"></textarea>
        </div>
        <div class="field-block">
          <label>答题截止时间</label>
          <input v-model="createTemplateForm.answerDeadline" type="datetime-local" />
        </div>
        <div class="field-block">
          <label>状态</label>
          <select v-model="createTemplateForm.status">
            <option value="active">active</option>
            <option value="inactive">inactive</option>
            <option value="archived">archived</option>
          </select>
        </div>
        <div class="field-block">
          <label>版本</label>
          <input v-model="createTemplateForm.version" />
        </div>
        <div class="action-row">
          <button class="action-btn" @click="submitCreateTemplate">提交模板</button>
        </div>
      </section>
    </div>

    <div v-if="createEventDialogOpen" class="dialog-backdrop" @click.self="createEventDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>新增事件</h2>
          <button class="action-btn" @click="createEventDialogOpen = false">关闭</button>
        </div>
        <div class="field-block">
          <label>事件标题</label>
          <input v-model="draftEvent.title" placeholder="填写事件标题" />
        </div>
        <div class="field-block">
          <label>来源系统 / 战区</label>
          <select v-model="draftEvent.theater">
            <option value="" disabled>请选择数据源</option>
            <option v-for="source in sourceSystemOptions" :key="`event-source-${source}`" :value="source">
              {{ source }}
            </option>
          </select>
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
        <div class="action-row">
          <button class="action-btn" @click="submitCreateEventFromDialog">提交事件</button>
        </div>
      </section>
    </div>

    <div v-if="createQuestionDialogOpen" class="dialog-backdrop" @click.self="closeCreateQuestionDialog">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>新增问题</h2>
          <button class="action-btn" @click="closeCreateQuestionDialog">关闭</button>
        </div>
        <div class="field-block">
          <label>搜索新闻（标题/内容）</label>
          <div class="action-row">
            <input v-model="questionEventSearch" placeholder="输入关键词筛选绑定新闻" />
            <button v-if="questionEventSearch" class="action-btn" @click="clearQuestionEventSearch">清空</button>
          </div>
          <small>
            {{ questionEventSearchLoading ? '搜索中...' : `匹配 ${questionEventMatchedTotal} 条` }}
          </small>
        </div>
        <div class="field-block">
          <label>绑定事件（可不选）</label>
          <div class="question-event-multi-select">
            <label
              v-for="eventItem in filteredKnownEventsForQuestion"
              :key="`question-target-${eventItem.id}`"
              class="select-row question-event-option"
            >
              <input
                type="checkbox"
                :checked="selectedEventIdsForQuestion.includes(eventItem.id)"
                @change="toggleQuestionEventSelection(eventItem.id)"
              />
              <span>{{ eventItem.title }}（{{ eventItem.theater }}）</span>
            </label>
            <p v-if="questionEventSearchLoading" class="item-subtle">搜索中...</p>
            <p v-else-if="filteredKnownEventsForQuestion.length === 0" class="item-subtle">无匹配新闻</p>
          </div>
          <small>已选择 {{ selectedEventIdsForQuestion.length }} 个事件</small>
        </div>
        <div class="field-block">
          <label>问题标题</label>
          <input v-model="draftQuestion.title" placeholder="输入预测问题" />
        </div>
        <div class="dialog-inline-grid">
          <div class="field-block">
            <label>问题等级</label>
            <select v-model="draftQuestion.level">
              <option v-for="level in levels" :key="`new-question-${level}`" :value="level">{{ level }}</option>
            </select>
          </div>
          <div class="field-block">
            <label>截止时间</label>
            <input v-model="draftQuestion.deadline" class="deadline-input" type="datetime-local" step="60" />
          </div>
        </div>
        <div class="field-block">
          <label>初始状态</label>
          <select v-model="draftQuestion.status">
            <option value="collecting">收集中</option>
            <option value="locked">已封存</option>
            <option value="resolved">已解析</option>
          </select>
        </div>
        <div v-if="draftQuestion.level === 'L1' || draftQuestion.level === 'L2'" class="field-block">
          <label>答案范围（L1/L2 必填）</label>
          <textarea
            v-model="draftQuestion.answerSpace"
            rows="2"
            placeholder="请输入候选答案，支持换行/中英文逗号分隔"
          ></textarea>
        </div>
        <div class="action-row">
          <button class="action-btn" @click="submitCreateQuestionFromDialog">提交问题</button>
        </div>
      </section>
    </div>

    <div v-if="authDialogOpen" class="dialog-backdrop" @click.self.prevent>
      <section class="dialog-panel auth-dialog">
        <div class="panel-head">
          <h2>{{ authMode === 'login' ? '用户登录' : '用户注册' }}</h2>
        </div>
        <div class="field-block">
          <label>用户名</label>
          <input v-model="authForm.username" placeholder="请输入用户名" />
        </div>
        <div class="field-block">
          <label>密码</label>
          <input v-model="authForm.password" type="password" placeholder="请输入密码" />
        </div>
        <div v-if="authMode === 'register'" class="field-block">
          <label>邮箱（可选）</label>
          <input v-model="authForm.email" placeholder="请输入邮箱" />
        </div>
        <p v-if="authError" class="auth-error">{{ authError }}</p>
        <div class="action-row action-right">
          <button class="action-btn" :disabled="authLoading" @click="authMode = authMode === 'login' ? 'register' : 'login'">
            {{ authMode === 'login' ? '切换到注册' : '切换到登录' }}
          </button>
          <button class="action-btn" :disabled="authLoading" @click="submitAuth">
            {{ authLoading ? '处理中...' : authMode === 'login' ? '登录' : '注册并登录' }}
          </button>
        </div>
      </section>
    </div>

    <section class="toast-stack" aria-live="polite" aria-atomic="false">
      <article v-for="toast in toasts" :key="toast.id" :class="['toast', `toast-${toast.kind}`]">
        <p>{{ toast.message }}</p>
        <button type="button" class="toast-close" @click="dismissToast(toast.id)">关闭</button>
      </article>
    </section>
  </div>
</template>
