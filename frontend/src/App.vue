<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { matchPredictionToAnswerOptionId, parseAnswerOptions } from './utils/answerOptions'
import ManageDataSourcesPanel from './components/ManageDataSourcesPanel.vue'
import ManageEventsPanel from './components/ManageEventsPanel.vue'
import ManageFilterRulesPanel from './components/ManageFilterRulesPanel.vue'
import ManageQuestionsPanel from './components/ManageQuestionsPanel.vue'
import ManageTasksPanel from './components/ManageTasksPanel.vue'
import ManageTemplatesPanel from './components/ManageTemplatesPanel.vue'
import HomeOverviewMap from './components/HomeOverviewMap.vue'
import QuestionFeedPanel from './components/QuestionFeedPanel.vue'
import SidebarNav from './components/SidebarNav.vue'
import TopbarPanel from './components/TopbarPanel.vue'

type Level = 'L1' | 'L2' | 'L3' | 'L4'
type QuestionStatus = 'draft' | 'pending_review' | 'published' | 'expired' | 'matched' | 'closed'
type AppView = 'home' | 'events' | 'questions' | 'questionStream' | 'templates' | 'tasks' | 'dataSources' | 'filterRules' | 'apiKeys' | 'modelEndpoints'
type ToastKind = 'success' | 'error' | 'info'
type ThemeId = 'olive' | 'blue' | 'sunset'

interface ToastItem {
  id: number
  kind: ToastKind
  message: string
}

interface EventItem {
  id: string
  codename: string
  title: string
  url: string | null
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
  matchScore: number | null
  eventDomain: string
  eventType: string
  area: string
  inputType: string
  background: string
  answerSpace: string
  hypothesis: string
  deadline: string
  status: QuestionStatus
  groundTruth: string
  deleteReason: string
  deletedAt: string
  createdAt?: string
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
  url: string | null
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
  match_score?: number | null
  event_domain?: string | null
  event_type?: string | null
  area?: string | null
  input_type?: string | null
  background?: string | null
  answer_space?: string | null
  hypothesis?: string | null
  deadline: string
  status: string
  trace_id: string
  delete_reason?: string | null
  deleted_at?: string | null
  created_at?: string | null
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
  templateIndex: number
  questionTemplate: string
  difficultyLevel: Level
  candidateAnswerType: 'fixed' | 'dynamic' | 'open'
  eventDomain: string
  eventType: string
  eventTypeId: string
  operationLevel: string
  status: 'active' | 'inactive' | 'archived'
  version: string
  usageCount: number
  createdAt: string
  updatedAt: string
}

interface BackendQuestionTemplateItem {
  id: string
  template_index: number
  question_template: string
  difficulty_level: Level
  candidate_answer_type: QuestionTemplateItem['candidateAnswerType']
  event_domain: string
  event_type: string
  event_type_id: string
  operation_level: string
  status: QuestionTemplateItem['status']
  version: string
  usage_count: number
  created_at: string
  updated_at: string
}

interface CommunityPredictionItem {
  id: string
  questionId: string
  userId: string
  username: string
  predictionContent: string
  confidence: number | null
  reasoning: string | null
  createdAt: string
  updatedAt: string
}

interface BackendCommunityPredictionItem {
  id: string
  question_id: string
  user_id: string
  username: string
  prediction_content: string
  confidence: number | null
  reasoning: string | null
  created_at: string
  updated_at: string
}

interface AgentPredictionItem {
  id: string
  questionId: string
  apiKeyId: string
  agentName: string
  userType: string
  purpose: string | null
  modelName: string
  predictionContent: string
  reasoning: string | null
  confidence: number | null
  evidence: { url: string; content: string }[]
  questionText: string
  isCorrect: boolean | null
  score: number | null
  status: string
  createdAt: string
}

interface BackendAgentPredictionItem {
  id: string
  question_id: string
  api_key_id: string
  agent_name: string
  user_type: string
  purpose: string | null
  model_name: string
  prediction_content: string
  reasoning: string | null
  confidence: number | null
  evidence: { url: string; content: string }[]
  question_text: string
  is_correct: boolean | null
  score: number | null
  status: string
  created_at: string
}

interface ModelEndpointItem {
  id: string
  name: string
  identifier: string
  provider: string
  endpoint_url: string
  api_key_ref: string | null
  model_name: string
  model_version: string
  max_tokens: number
  temperature: number
  timeout_seconds: number
  is_available: boolean
  status: string
  created_at: string
  updated_at: string
}

interface QuestionCommentItem {
  id: string
  questionId: string
  userId: string
  username: string
  content: string
  createdAt: string
  updatedAt: string
}

interface QuestionInteractionCount {
  predictionCount: number
  commentCount: number
}

interface QuestionParticipationSummary {
  hasPrediction: boolean
  myCommentCount: number
}

interface BackendQuestionCommentItem {
  id: string
  question_id: string
  user_id: string
  username: string
  content: string
  created_at: string
  updated_at: string
}

interface BackendQuestionCommunityStatsItem {
  question_id: string
  prediction_count: number
  comment_count: number
  has_prediction: boolean
  my_comment_count: number
}

interface BackendQuestionCommunityStatsResponse {
  items: BackendQuestionCommunityStatsItem[]
}

interface ThemeOption {
  id: ThemeId
  label: string
}

const levels: Level[] = ['L1', 'L2', 'L3', 'L4']
const questionDeleteReasonOptions = [
  '问题设计不合理',
  '问题事件不关联',
  '问题表述不清晰',
  '判定标准不可验证',
  '问题时效性不足',
  '事件信息质量不足',
]
const themeOptions: ThemeOption[] = [
  { id: 'olive', label: '橄榄夜幕' },
  { id: 'blue', label: '蓝白简约' },
  { id: 'sunset', label: '暖橙日落' },
]
const filterRuleScopes: FilterRuleItem['ruleScope'][] = ['db_import', 'scrapy', 'document', 'use', 'other']
const eventManagePageSizeOptions = [5, 10, 20, 50, 100]

const homeEvents = ref<EventItem[]>([
  {
    id: 'evt-001',
    codename: '铁砂行动',
    title: '边境补给车队改道异常',
    url: null,
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
    url: null,
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
    url: null,
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
    matchScore: null,
    eventDomain: '',
    eventType: '',
    area: '',
    inputType: '',
    background: '',
    answerSpace: '会上升\n不会上升\n不确定',
    hypothesis: '若流量持续上升 20%，可判定存在前置部署行为。',
    deadline: '2026-03-12T00:00:00Z',
    status: 'draft',
    groundTruth: '待遥测数据复核。',
    deleteReason: '',
    deletedAt: '',
  },
  {
    id: 'q-102',
    eventIds: ['evt-002'],
    level: 'L1',
    title: '声呐异常会持续到下一个潮汐周期吗？',
    matchScore: null,
    eventDomain: '',
    eventType: '',
    area: '',
    inputType: '',
    background: '',
    answerSpace: '会\n不会',
    hypothesis: '若异常高于基线持续 18 小时，说明来源并非环境因素。',
    deadline: '2026-03-11T06:00:00Z',
    status: 'pending_review',
    groundTruth: '待信号归因报告。',
    deleteReason: '',
    deletedAt: '',
  },
  {
    id: 'q-103',
    eventIds: ['evt-003'],
    level: 'L3',
    title: '本周中继故障会使指挥吞吐降到 65% 以下吗？',
    matchScore: null,
    eventDomain: '',
    eventType: '',
    area: '',
    inputType: '',
    background: '',
    answerSpace: '',
    hypothesis: '天气与干扰叠加可能导致吞吐持续下降。',
    deadline: '2026-03-15T12:00:00Z',
    status: 'closed',
    groundTruth: '观测平均吞吐 61.7%，已确认跌破阈值。',
    deleteReason: '',
    deletedAt: '',
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
const APP_VIEW_STORAGE_KEY = 'moppa_current_view'

function isAppView(value: string): value is AppView {
  return value === 'home'
    || value === 'events'
    || value === 'questions'
    || value === 'questionStream'
    || value === 'templates'
    || value === 'tasks'
    || value === 'dataSources'
    || value === 'filterRules'
}

function loadInitialView(): AppView {
  const saved = localStorage.getItem(APP_VIEW_STORAGE_KEY)
  if (saved && isAppView(saved)) {
    return saved
  }
  return 'home'
}

const currentView = ref<AppView>(loadInitialView())
const activeTheme = ref<ThemeId>('blue')
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

function isThemeId(value: string): value is ThemeId {
  return value === 'olive' || value === 'blue' || value === 'sunset'
}

function applyTheme(theme: ThemeId): void {
  document.documentElement.setAttribute('data-theme', theme)
  localStorage.setItem('moppa_theme', theme)
}

function updateTheme(nextTheme: string): void {
  if (!isThemeId(nextTheme)) {
    return
  }
  activeTheme.value = nextTheme
}

const draftEvent = reactive({ title: '', theater: '', summary: '', url: '', severity: 'medium' as EventItem['severity'] })
const draftQuestion = reactive({
  title: '',
  level: 'L2' as Level,
  deadline: '',
  status: 'draft' as QuestionItem['status'],
  matchScore: '',
  eventDomain: '',
  eventType: '',
  area: '',
  inputType: '',
  background: '',
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
const questionEventSearchLoadingMore = ref(false)
const questionEventSearchTotal = ref(0)
const questionEventOptions = ref<EventItem[]>([])
const questionEventSearchSeq = ref(0)
const questionEventSearchPage = ref(0)
const questionEventSearchHasMore = ref(true)
const questionEventSearchKeyword = ref('')
const questionEventSearchMode = ref<'create' | 'edit' | null>(null)
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
  matchScore: '',
  eventDomain: '',
  eventType: '',
  area: '',
  inputType: '',
  background: '',
  answerSpace: '',
  eventIds: [] as string[],
  deadline: '',
  status: 'draft' as QuestionItem['status'],
})
const templateEditForm = reactive({
  id: '',
  templateIndex: 1,
  questionTemplate: '',
  difficultyLevel: 'L2' as Level,
  candidateAnswerType: 'dynamic' as QuestionTemplateItem['candidateAnswerType'],
  eventDomain: '',
  eventType: '',
  eventTypeId: '',
  operationLevel: '',
  status: 'active' as QuestionTemplateItem['status'],
  version: 'v1.0',
})
const createTemplateForm = reactive({
  templateIndex: 1,
  questionTemplate: '',
  difficultyLevel: 'L2' as Level,
  candidateAnswerType: 'dynamic' as QuestionTemplateItem['candidateAnswerType'],
  eventDomain: '',
  eventType: '',
  eventTypeId: '',
  operationLevel: '',
  status: 'active' as QuestionTemplateItem['status'],
  version: 'v1.0',
})
const selectedTemplate = ref<QuestionTemplateItem | null>(null)
const templates = ref<QuestionTemplateItem[]>([])
const templateManagePage = ref(1)
const templateManagePageSize = ref(10)
const templateManageJumpPage = ref('1')
const templateManageTotal = ref(0)
const templateManageSearchKeyword = ref('')
const selectedManageTemplateIds = ref<string[]>([])
const homeEventPage = ref(1)
const homeEventPageSize = 3
const homeEventTotal = ref(homeEvents.value.length)
const homeEventJumpPage = ref('1')
const eventManagePage = ref(0)
const eventManagePageSize = ref(10)
const eventManageSearchKeyword = ref('')
const eventManageSourceSystem = ref('')
const eventManageFilterStatus = ref('')
const eventManageTimeFrom = ref('')
const eventManageTimeTo = ref('')
const eventManageSearchLoading = ref(false)
const eventManageHasMore = ref(true)
const eventManageReloadSeq = ref(0)
let eventManageReloadPending = false
let eventManageSearchTimer: number | undefined
const manageEvents = ref<EventItem[]>([])
const manageEventTotal = ref(0)
const selectedManageEventIds = ref<string[]>([])
const eventReviewProcessing = ref(false)
const questionManagePage = ref(0)
const questionManagePageSize = ref(10)
const questionManageSearchKeyword = ref('')
const questionManageFilterEventDomain = ref('')
const questionManageFilterEventType = ref('')
const questionManageFilterDeadlineFrom = ref('')
const questionManageFilterDeadlineTo = ref('')
const questionManageFilterStatus = ref('')
const questionManageFilterLevel = ref('')
const questionManageDeletedMode = ref<'active_only' | 'with_deleted' | 'deleted_only'>('active_only')
const questionManageSearchLoading = ref(false)
const questionManageHasMore = ref(true)
const questionManageReloadSeq = ref(0)
let questionManageReloadPending = false
let questionManageSearchTimer: number | undefined
const manageQuestions = ref<QuestionItem[]>([])
const questionManageTotal = ref(questions.value.length)
const questionFeedItems = ref<QuestionItem[]>([])
const questionFeedPage = ref(0)
const questionFeedTotal = ref(0)
const questionFeedLoading = ref(false)
const questionFeedHasMore = ref(true)
const questionFeedSearchKeyword = ref('')
const questionFeedFilterEventDomain = ref('')
const questionFeedFilterEventType = ref('')
const questionFeedFilterDeadlineFrom = ref('')
const questionFeedFilterDeadlineTo = ref('')
const questionFeedFilterStatus = ref('')
const questionFeedFilterLevel = ref('')
let questionFeedSearchTimer: number | undefined
let questionFeedFilterResetting = false
let questionFeedReloadPending = false
const questionFeedReloadSeq = ref(0)
const questionFeedInteractionCounts = ref<Record<string, QuestionInteractionCount>>({})
const questionFeedParticipation = ref<Record<string, QuestionParticipationSummary>>({})
const selectedManageQuestionIds = ref<string[]>([])
const questionDeleteReasonDialogOpen = ref(false)
const questionDeleteReasonPreset = ref('')
const questionDeleteReasonCustom = ref('')
const pendingDeleteQuestionIds = ref<string[]>([])
const pendingDeleteCloseQuestionEdit = ref(false)
const manageDetailQuestion = ref<QuestionItem | null>(null)
const questionPredictions = ref<Record<string, CommunityPredictionItem[]>>({})
const questionAgentPredictions = ref<Record<string, AgentPredictionItem[]>>({})
const questionComments = ref<Record<string, QuestionCommentItem[]>>({})
const questionInteractionLoading = ref(false)
const predictionSubmitting = ref(false)
const commentSubmitting = ref(false)
const predictionForm = reactive({ predictionContent: '', selectedAnswerId: '', confidence: '', reasoning: '' })
const commentDraft = ref('')
const editingCommentId = ref('')
const editingCommentContent = ref('')
const commentActionLoading = ref(false)
const questionComposerMode = ref<'prediction' | 'comment' | null>(null)
const predictionPanelCollapsed = ref(false)
const agentPredictionPanelCollapsed = ref(false)
const commentPanelCollapsed = ref(false)
const tasks = ref<TaskItem[]>([])
const taskManagePage = ref(1)
const taskManagePageSize = ref(10)
const taskManageJumpPage = ref('1')
const taskManageTotal = ref(0)
const selectedManageTaskIds = ref<string[]>([])
const createTaskDialogOpen = ref(false)
const taskDetailDialogOpen = ref(false)
const triggerPullDialogOpen = ref(false)
const tavilyIngestProcessing = ref(false)
const autoReviewProcessing = ref(false)
const autoQuestionProcessing = ref(false)
const locationAnalysisProcessing = ref(false)
const expiryProcessing = ref(false)
const selectedTask = ref<TaskItem | null>(null)
const selectedTaskDetail = ref<S1JobDetail | null>(null)
const taskDetailRefreshing = ref(false)
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

interface ApiKeyItem {
  id: string
  name: string
  token: string
  user_type: string
  purpose: string | null
  is_active: boolean
  last_used_at: string | null
  created_by: string | null
  created_at: string
}

const apiKeyList = ref<ApiKeyItem[]>([])
const apiKeyManagePage = ref(1)
const apiKeyManageTotal = ref(0)
const apiKeyManagePageSize = ref(20)
const apiKeyManageJumpPage = ref('1')
const apiKeyCreateDialogOpen = ref(false)
const apiKeyCreatedToken = ref('')
const apiKeyCreatedName = ref('')
const apiKeyFormName = ref('')
const apiKeyFormUserType = ref('agent')
const apiKeyFormPurpose = ref('')
const apiKeyEditDialogOpen = ref(false)
const apiKeyEditId = ref('')
const apiKeyEditName = ref('')
const apiKeyEditUserType = ref('agent')
const apiKeyEditPurpose = ref('')

const modelEndpointList = ref<ModelEndpointItem[]>([])
const modelEndpointManagePage = ref(1)
const modelEndpointManageTotal = ref(0)
const modelEndpointManagePageSize = ref(20)
const modelEndpointManageJumpPage = ref('1')
const modelEndpointFormDialogOpen = ref(false)
const modelEndpointFormIsEdit = ref(false)
const modelEndpointFormId = ref('')
const meFormName = ref('')
const meFormIdentifier = ref('')
const meFormProvider = ref('openai')
const meFormEndpointUrl = ref('')
const meFormApiKeyRef = ref('')
const meFormModelName = ref('')
const meFormModelVersion = ref('v1.0')
const meFormMaxTokens = ref('4096')
const meFormTemperature = ref('0.7')
const meFormTimeoutSeconds = ref('120')
const meFormIsAvailable = ref(true)
const meFormStatus = ref('active')
const meApiKeyVisible = ref(false)

const selectedTemplateDetail = computed(() => selectedTemplate.value)
const isAuthenticated = computed(() => Boolean(authUser.value))
const isAdmin = computed(() => authUser.value?.role === 'admin')
const previewEvents = computed(() => homeEvents.value.filter((item) => item.filterStatus === 'passed'))
const homeEventTotalPages = computed(() => Math.max(1, Math.ceil(homeEventTotal.value / homeEventPageSize)))
const homeHasEvents = computed(() => previewEvents.value.length > 0)
const localFilteredManageEvents = computed(() => {
  const keyword = eventManageSearchKeyword.value.trim().toLowerCase()
  const sourceSystem = eventManageSourceSystem.value.trim()
  const status = eventManageFilterStatus.value.trim()
  const fromMs = parseLocalDateTimeToMs(eventManageTimeFrom.value)
  const toMs = parseLocalDateTimeToMs(eventManageTimeTo.value)
  return sortByEventTimeDesc([...homeEvents.value]).filter((item) => {
    if (sourceSystem && item.theater !== sourceSystem) {
      return false
    }
    if (status === 'reviewed') {
      if (!['passed', 'filtered'].includes(item.filterStatus)) {
        return false
      }
    } else if (status && item.filterStatus !== status) {
      return false
    }
    const eventMs = Date.parse(item.timestamp)
    if (fromMs !== null && Number.isFinite(eventMs) && eventMs < fromMs) {
      return false
    }
    if (toMs !== null && Number.isFinite(eventMs) && eventMs > toMs) {
      return false
    }
    if (!keyword) {
      return true
    }
    const haystack = `${item.title}\n${item.summary}\n${item.theater}`.toLowerCase()
    if (!haystack.includes(keyword)) {
      return false
    }
    return true
  })
})
const manageEventMatchingTotal = computed(() =>
  backendOnline.value ? manageEventTotal.value : localFilteredManageEvents.value.length,
)
const allLoadedEventsSelected = computed(() =>
  manageEvents.value.length > 0 && manageEvents.value.every((item) => selectedManageEventIds.value.includes(item.id)),
)

const localFilteredManageQuestions = computed(() => {
  const keyword = questionManageSearchKeyword.value.trim().toLowerCase()
  const eventDomain = questionManageFilterEventDomain.value.trim().toLowerCase()
  const eventType = questionManageFilterEventType.value.trim().toLowerCase()
  const createdFromMs = parseLocalDateTimeToMs(questionManageFilterDeadlineFrom.value)
  const createdToMs = parseLocalDateTimeToMs(questionManageFilterDeadlineTo.value)
  const status = questionManageFilterStatus.value.trim()
  const level = questionManageFilterLevel.value.trim()
  const deletedMode = questionManageDeletedMode.value
  return questions.value.filter((item) => {
    if (deletedMode === 'active_only' && item.deletedAt) {
      return false
    }
    if (deletedMode === 'deleted_only' && !item.deletedAt) {
      return false
    }
    if (status && item.status !== status) {
      return false
    }
    if (level && item.level !== level) {
      return false
    }
    if (eventDomain && !item.eventDomain.toLowerCase().includes(eventDomain)) {
      return false
    }
    if (eventType && !item.eventType.toLowerCase().includes(eventType)) {
      return false
    }
    const createdMs = Date.parse(item.createdAt || item.deadline)
    if (createdFromMs !== null && Number.isFinite(createdMs) && createdMs < createdFromMs) {
      return false
    }
    if (createdToMs !== null && Number.isFinite(createdMs) && createdMs > createdToMs) {
      return false
    }
    if (!keyword) {
      return true
    }
    const haystack = `${item.title}\n${item.hypothesis}\n${item.groundTruth}\n${item.background}\n${item.answerSpace}\n${item.eventDomain}\n${item.eventType}\n${item.area}\n${item.inputType}\n${item.deleteReason}`.toLowerCase()
    return haystack.includes(keyword)
  })
})
const questionManageFiltersApplied = computed(() =>
  Boolean(
    questionManageSearchKeyword.value.trim()
    || questionManageFilterEventDomain.value.trim()
    || questionManageFilterEventType.value.trim()
    || questionManageFilterDeadlineFrom.value.trim()
    || questionManageFilterDeadlineTo.value.trim()
    || questionManageFilterStatus.value.trim()
    || questionManageFilterLevel.value.trim()
    || questionManageDeletedMode.value !== 'active_only',
  ),
)
const allLoadedQuestionsSelected = computed(() =>
  manageQuestions.value.filter((item) => !item.deletedAt).length > 0
  && manageQuestions.value
    .filter((item) => !item.deletedAt)
    .every((item) => selectedManageQuestionIds.value.includes(item.id)),
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
const questionFeedEventTitleMap = computed(() => {
  const map = new Map<string, string>()
  for (const item of allKnownEvents.value) {
    map.set(item.id, item.title)
  }
  return map
})
const questionFeedFiltersApplied = computed(() =>
  Boolean(
    questionFeedSearchKeyword.value.trim()
    || questionFeedFilterEventDomain.value.trim()
    || questionFeedFilterEventType.value.trim()
    || questionFeedFilterDeadlineFrom.value.trim()
    || questionFeedFilterDeadlineTo.value.trim()
    || questionFeedFilterStatus.value.trim()
    || questionFeedFilterLevel.value.trim(),
  ),
)
const filteredQuestionFeedItems = computed(() => {
  const keyword = questionFeedSearchKeyword.value.trim().toLowerCase()
  const eventDomain = questionFeedFilterEventDomain.value.trim().toLowerCase()
  const eventType = questionFeedFilterEventType.value.trim().toLowerCase()
  const createdFromMs = parseLocalDateTimeToMs(questionFeedFilterDeadlineFrom.value)
  const createdToMs = parseLocalDateTimeToMs(questionFeedFilterDeadlineTo.value)
  const status = questionFeedFilterStatus.value.trim()
  const level = questionFeedFilterLevel.value.trim()

  return questionFeedItems.value.filter((item) => {
    if (status && item.status !== status) {
      return false
    }

    if (level && item.level !== level) {
      return false
    }

    if (eventDomain && !item.eventDomain.toLowerCase().includes(eventDomain)) {
      return false
    }

    if (eventType && !item.eventType.toLowerCase().includes(eventType)) {
      return false
    }

    const createdMs = Date.parse(item.createdAt || item.deadline)
    if (createdFromMs !== null && Number.isFinite(createdMs) && createdMs < createdFromMs) {
      return false
    }
    if (createdToMs !== null && Number.isFinite(createdMs) && createdMs > createdToMs) {
      return false
    }

    if (!keyword) {
      return true
    }

    const linkedEventTitles = item.eventIds
      .map((id) => questionFeedEventTitleMap.value.get(id) ?? id)
      .join('\n')
    const haystack = `${item.title}\n${item.background}\n${item.answerSpace}\n${item.hypothesis}\n${item.groundTruth}\n${item.eventDomain}\n${item.eventType}\n${item.area}\n${item.inputType}\n${linkedEventTitles}`.toLowerCase()
    return haystack.includes(keyword)
  })
})
const activeQuestionPredictions = computed(() => {
  const questionId = manageDetailQuestion.value?.id
  if (!questionId) {
    return []
  }
  return questionPredictions.value[questionId] ?? []
})
const activeQuestionAgentPredictions = computed(() => {
  const questionId = manageDetailQuestion.value?.id
  if (!questionId) {
    return []
  }
  return questionAgentPredictions.value[questionId] ?? []
})
const activeQuestionComments = computed(() => {
  const questionId = manageDetailQuestion.value?.id
  if (!questionId) {
    return []
  }
  return questionComments.value[questionId] ?? []
})
const myCurrentPrediction = computed(() => {
  const userId = authUser.value?.id
  if (!userId) {
    return null
  }
  return activeQuestionPredictions.value.find((item) => item.userId === userId) ?? null
})
const canCurrentQuestionInteract = computed(() => canInteractWithQuestion(manageDetailQuestion.value))
const currentQuestionAnswerOptions = computed(() =>
  parseAnswerOptions(manageDetailQuestion.value?.answerSpace ?? ''),
)
const selectedAnswerOption = computed(() =>
  currentQuestionAnswerOptions.value.find((item) => item.id === predictionForm.selectedAnswerId) ?? null,
)

// 计算每个答案选项的投票分布
const answerOptionDistribution = computed(() => {
  const options = currentQuestionAnswerOptions.value
  const predictions = activeQuestionPredictions.value
  if (options.length === 0 || predictions.length === 0) {
    return new Map<string, number>()
  }

  const distribution = new Map<string, number>()

  // 统计每个选项的投票数
  for (const option of options) {
    const count = predictions.filter((p) =>
      p.predictionContent.trim() === option.label ||
      p.predictionContent.trim() === `${option.key}: ${option.label}` ||
      p.predictionContent.trim() === option.key
    ).length
    distribution.set(option.id, count)
  }

  return distribution
})

// 计算每个选项的百分比
const answerOptionPercentages = computed(() => {
  const distribution = answerOptionDistribution.value
  const total = activeQuestionPredictions.value.length

  if (total === 0) {
    return new Map<string, string>()
  }

  const percentages = new Map<string, string>()
  for (const [optionId, count] of distribution.entries()) {
    const percentage = Math.round((count / total) * 100)
    percentages.set(optionId, `${percentage}%`)
  }

  return percentages
})

// 当前用户选择的选项
const mySelectedAnswerOption = computed(() => {
  const userId = authUser.value?.id
  if (!userId) {
    return null
  }
  const myPrediction = activeQuestionPredictions.value.find((item) => item.userId === userId)
  if (!myPrediction) {
    return null
  }
  return currentQuestionAnswerOptions.value.find((option) =>
    myPrediction.predictionContent.trim() === option.label ||
    myPrediction.predictionContent.trim() === `${option.key}: ${option.label}` ||
    myPrediction.predictionContent.trim() === option.key
  ) ?? null
})

// 点击选项快速预测/取消预测/修改预测
async function handleAnswerOptionClick(optionId: string): Promise<void> {
  const question = manageDetailQuestion.value
  if (!question || !backendOnline.value || !isAuthenticated.value) {
    return
  }
  if (!canInteractWithQuestion(question)) {
    backendStatus.value = '仅已过期问题不可提交或修改预测'
    return
  }

  const myOptionId = mySelectedAnswerOption.value?.id ?? ''

  // 点击已选择的选项 = 取消预测
  if (myOptionId === optionId) {
    await cancelMyPrediction()
    return
  }

  // 点击其他选项 = 修改预测
  const selectedOption = currentQuestionAnswerOptions.value.find((item) => item.id === optionId)
  if (!selectedOption) {
    return
  }

  predictionForm.selectedAnswerId = optionId
  predictionForm.predictionContent = selectedOption.label
  predictionForm.confidence = ''
  predictionForm.reasoning = ''

  await submitMyPrediction()
}
const eventDetailQuestionPool = computed(() => {
  const merged = new Map<string, QuestionItem>()
  for (const item of questions.value) {
    merged.set(item.id, item)
  }
  for (const item of manageQuestions.value) {
    merged.set(item.id, item)
  }
  for (const item of questionFeedItems.value) {
    merged.set(item.id, item)
  }
  return Array.from(merged.values())
})

function relatedQuestionsForEvent(eventId: string): QuestionItem[] {
  return eventDetailQuestionPool.value.filter((item) => item.eventIds.includes(eventId)).slice(0, 6)
}

function canEditComment(comment: QuestionCommentItem): boolean {
  return authUser.value?.id === comment.userId
}

function canDeleteComment(comment: QuestionCommentItem): boolean {
  return authUser.value?.id === comment.userId || isAdmin.value
}

function beginCommentEdit(comment: QuestionCommentItem): void {
  if (!canEditComment(comment)) {
    backendStatus.value = '你只能编辑自己的评论'
    return
  }
  editingCommentId.value = comment.id
  editingCommentContent.value = comment.content
}

function cancelCommentEdit(): void {
  editingCommentId.value = ''
  editingCommentContent.value = ''
}
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
  if (backendOnline.value) {
    return questionEventOptions.value
  }
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
let taskDetailRefreshTimer: number | undefined
const skeletonRows = [1, 2, 3, 4]

const statusLabel: Record<QuestionItem['status'], string> = {
  draft: '收集中',
  pending_review: '待评审',
  published: '已发布',
  expired: '已过期',
  matched: '已匹配',
  closed: '已解析',
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
  if (status === 'matched') {
    return 'badge-info'
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

function statusTone(status: QuestionItem['status']): string {
  if (status === 'closed') {
    return 'badge-success'
  }
  if (status === 'expired') {
    return 'badge-error'
  }
  if (status === 'pending_review' || status === 'published' || status === 'matched') {
    return 'badge-info'
  }
  return 'badge-warning'
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

function openManageDetail(eventItem: EventItem): void {
  selectedEventId.value = eventItem.id
  manageDetailEvent.value = eventItem
  eventDetailDialogOpen.value = true
}

function openEventEdit(eventItem: EventItem): void {
  if (!isAdmin.value) {
    backendStatus.value = '当前账号无权限编辑事件'
    return
  }
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
  questionComposerMode.value = null
  predictionPanelCollapsed.value = false
  commentPanelCollapsed.value = false
  cancelCommentEdit()
  void ensureQuestionEventOptionsByIds(questionItem.eventIds)
  commentDraft.value = ''
  void loadQuestionInteractions(questionItem.id)
  questionDetailDialogOpen.value = true
}

function findKnownEventById(eventId: string): EventItem | null {
  return allKnownEvents.value.find((item) => item.id === eventId) ?? null
}

function linkedEventDisplayLabel(eventId: string): string {
  const matched = findKnownEventById(eventId)
  if (matched) {
    return `${matched.title} · ${matched.theater}`
  }
  return `事件 ${eventId}`
}

async function openQuestionLinkedEventDetail(eventId: string): Promise<void> {
  await ensureQuestionEventOptionsByIds([eventId])
  const matched = findKnownEventById(eventId)
  if (!matched) {
    backendStatus.value = `未找到关联事件详情：${eventId}`
    return
  }
  openManageDetail(matched)
}

function openQuestionEdit(questionItem: QuestionItem): void {
  if (!isAdmin.value) {
    backendStatus.value = '当前账号无权限编辑问题'
    return
  }
  selectedQuestionId.value = questionItem.id
  questionEditEventSearch.value = ''
  questionEditForm.id = questionItem.id
  questionEditForm.title = questionItem.title
  questionEditForm.level = questionItem.level
  questionEditForm.matchScore = questionItem.matchScore !== null ? String(questionItem.matchScore) : ''
  questionEditForm.eventDomain = questionItem.eventDomain
  questionEditForm.eventType = questionItem.eventType
  questionEditForm.area = questionItem.area
  questionEditForm.inputType = questionItem.inputType
  questionEditForm.background = questionItem.background
  questionEditForm.answerSpace = questionItem.answerSpace
  questionEditForm.eventIds = [...questionItem.eventIds]
  questionEditForm.deadline = toDateTimeLocalValue(questionItem.deadline)
  questionEditForm.status = questionItem.status
  questionEventSearchMode.value = 'edit'
  void ensureQuestionEventOptionsByIds(questionItem.eventIds)
  if (backendOnline.value) {
    void fetchQuestionEventOptions('', 'edit')
  }
  questionEditDialogOpen.value = true
}

function openCreateQuestionDialog(): void {
  questionEventSearch.value = ''
  selectedEventIdsForQuestion.value = selectedEventId.value ? [selectedEventId.value] : []
  createQuestionDialogOpen.value = true
  questionEventSearchMode.value = 'create'
  if (backendOnline.value) {
    void fetchQuestionEventOptions('', 'create')
  }
}

function closeCreateQuestionDialog(): void {
  if (questionEventSearchTimer !== undefined) {
    window.clearTimeout(questionEventSearchTimer)
    questionEventSearchTimer = undefined
  }
  resetQuestionEventSearchState()
  questionEventSearch.value = ''
  selectedEventIdsForQuestion.value = []
  draftQuestion.area = ''
  draftQuestion.inputType = ''
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
  closeQuestionDeleteReasonDialog()
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
    questionDeleteReasonDialogOpen.value ||
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
    void fetchQuestionEventOptions('', 'create')
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
  const hadInputBeforeSubmit = [draftEvent.title, draftEvent.theater, draftEvent.summary, draftEvent.url].some((value) => value.trim())
  await createEvent()
  if (!draftEvent.title && !draftEvent.theater && !draftEvent.summary && !draftEvent.url && hadInputBeforeSubmit) {
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
  if (allLoadedEventsSelected.value) {
    selectedManageEventIds.value = selectedManageEventIds.value.filter(
      (id) => !manageEvents.value.some((item) => item.id === id),
    )
    return
  }

  const pageIds = manageEvents.value.map((item) => item.id)
  selectedManageEventIds.value = Array.from(new Set([...selectedManageEventIds.value, ...pageIds]))
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

function toggleManageQuestionSelection(questionId: string): void {
  const target = manageQuestions.value.find((item) => item.id === questionId)
  if (target?.deletedAt) {
    return
  }
  if (selectedManageQuestionIds.value.includes(questionId)) {
    selectedManageQuestionIds.value = selectedManageQuestionIds.value.filter((id) => id !== questionId)
    return
  }
  selectedManageQuestionIds.value = [...selectedManageQuestionIds.value, questionId]
}

function toggleSelectAllQuestionsOnPage(): void {
  const selectablePageIds = manageQuestions.value
    .filter((item) => !item.deletedAt)
    .map((item) => item.id)
  if (allLoadedQuestionsSelected.value) {
    selectedManageQuestionIds.value = selectedManageQuestionIds.value.filter(
      (id) => !selectablePageIds.includes(id),
    )
    return
  }

  selectedManageQuestionIds.value = Array.from(new Set([...selectedManageQuestionIds.value, ...selectablePageIds]))
}

function resetQuestionManageFilters(): void {
  questionManageSearchKeyword.value = ''
  questionManageFilterEventDomain.value = ''
  questionManageFilterEventType.value = ''
  questionManageFilterDeadlineFrom.value = ''
  questionManageFilterDeadlineTo.value = ''
  questionManageFilterStatus.value = ''
  questionManageFilterLevel.value = ''
  questionManageDeletedMode.value = 'active_only'
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
  const pageIds = tasks.value.map((item) => item.id)
  if (allTasksOnPageSelected.value) {
    selectedManageTaskIds.value = selectedManageTaskIds.value.filter((id) => !pageIds.includes(id))
    return
  }
  selectedManageTaskIds.value = Array.from(new Set([...selectedManageTaskIds.value, ...pageIds]))
}

function setTaskManagePageSize(size: number): void {
  taskManagePageSize.value = size
  taskManagePage.value = 1
  taskManageJumpPage.value = '1'
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
  scheduleTaskDetailAutoRefresh()
}

async function refreshCurrentTaskDetail(): Promise<void> {
  const taskId = selectedTask.value?.id ?? selectedTaskDetail.value?.task_id
  if (!taskId) {
    return
  }
  taskDetailRefreshing.value = true
  try {
    await fetchTaskDetail(taskId)
  } finally {
    taskDetailRefreshing.value = false
  }
}

function stopTaskDetailAutoRefresh(): void {
  if (taskDetailRefreshTimer !== undefined) {
    window.clearTimeout(taskDetailRefreshTimer)
    taskDetailRefreshTimer = undefined
  }
}

function scheduleTaskDetailAutoRefresh(): void {
  stopTaskDetailAutoRefresh()
  const status = selectedTaskDetail.value?.status ?? ''
  if (!taskDetailDialogOpen.value || (status !== 'running' && status !== 'pending')) {
    return
  }
  taskDetailRefreshTimer = window.setTimeout(() => {
    void refreshCurrentTaskDetail().then(() => {
      scheduleTaskDetailAutoRefresh()
    })
  }, 2000)
}

function getTaskResultNumber(key: string): number | null {
  const value = selectedTaskDetail.value?.result?.[key]
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  return null
}

function getTaskBatchLogs(): Array<Record<string, unknown>> {
  const raw = selectedTaskDetail.value?.result?.batch_logs
  if (!Array.isArray(raw)) {
    return []
  }
  return raw.filter((item): item is Record<string, unknown> => typeof item === 'object' && item !== null)
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
    const ids = [...selectedManageTaskIds.value]
    await sendJson('/tasks', 'DELETE', { ids })
    await fetchTasks(taskManagePage.value)
    selectedManageTaskIds.value = selectedManageTaskIds.value.filter((id) => !ids.includes(id))
    backendStatus.value = `任务批量删除成功（${ids.length} 条）`
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

async function triggerTavilyIngestNow(): Promise<void> {
  if (!backendOnline.value) {
    backendStatus.value = '后端离线：无法触发 Tavily 专题采集'
    return
  }

  tavilyIngestProcessing.value = true
  try {
    const result = await sendJson<S1TaskResponse>('/s1/jobs/tavily-ingest-now', 'POST', {})
    backendStatus.value = `Tavily 专题采集已触发：${result.task_id}`
    await fetchTasks(1)
    const matched = tasks.value.find((item) => item.id === result.task_id)
    if (matched) {
      openTaskDetail(matched)
    }
  } catch {
    backendStatus.value = 'Tavily 专题采集触发失败：请检查后端接口或参数格式'
  } finally {
    tavilyIngestProcessing.value = false
  }
}

async function triggerAutoQuestionNow(): Promise<void> {
  if (!backendOnline.value) {
    backendStatus.value = '后端离线：无法触发自动提问'
    return
  }

  autoQuestionProcessing.value = true
  try {
    const result = await sendJson<S1TaskResponse>('/s1/jobs/auto-question-now', 'POST', {})
    backendStatus.value = `自动提问已触发：${result.task_id}`
    await fetchTasks(1)
    const matched = tasks.value.find((item) => item.id === result.task_id)
    if (matched) {
      openTaskDetail(matched)
    }
  } catch {
    backendStatus.value = '自动提问触发失败：请检查后端接口或参数格式'
  } finally {
    autoQuestionProcessing.value = false
  }
}

async function triggerLocationAnalysisNow(): Promise<void> {
  if (!backendOnline.value) {
    backendStatus.value = '后端离线：无法触发位置分析'
    return
  }

  locationAnalysisProcessing.value = true
  try {
    const result = await sendJson<S1TaskResponse>('/s1/jobs/question-location-analysis-now', 'POST', {})
    backendStatus.value = `位置分析已触发：${result.task_id}`
    await fetchTasks(1)
    const matched = tasks.value.find((item) => item.id === result.task_id)
    if (matched) {
      openTaskDetail(matched)
    }
  } catch {
    backendStatus.value = '位置分析触发失败：请检查后端接口或参数格式'
  } finally {
    locationAnalysisProcessing.value = false
  }
}

async function triggerExpiryCheckNow(): Promise<void> {
  if (!backendOnline.value) {
    backendStatus.value = '后端离线：无法触发问题过期检查'
    return
  }

  expiryProcessing.value = true
  try {
    const result = await sendJson<S1TaskResponse>('/s1/jobs/question-expiry-now', 'POST', {})
    backendStatus.value = `问题过期检查已触发：${result.task_id}`
    await fetchTasks(1)
    const matched = tasks.value.find((item) => item.id === result.task_id)
    if (matched) {
      openTaskDetail(matched)
    }
  } catch {
    backendStatus.value = '问题过期检查触发失败：请检查后端接口或参数格式'
  } finally {
    expiryProcessing.value = false
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
}

function copyToClipboard(text: string): void {
  window.navigator.clipboard.writeText(text)
  backendStatus.value = '已复制到剪贴板'
}

async function fetchApiKeys(page = 1): Promise<void> {
  const pageData = await fetchJson<{ page: number; page_size: number; total: number; items: ApiKeyItem[] }>(
    `/api-keys?page=${page}&page_size=${apiKeyManagePageSize.value}`,
  )
  apiKeyList.value = pageData.items
  apiKeyManageTotal.value = pageData.total
  apiKeyManagePage.value = pageData.page
  apiKeyManageJumpPage.value = String(pageData.page)
}

function openApiKeyCreateDialog(): void {
  apiKeyFormName.value = ''
  apiKeyFormUserType.value = 'agent'
  apiKeyFormPurpose.value = ''
  apiKeyCreateDialogOpen.value = true
}

async function createApiKey(): Promise<void> {
  if (!apiKeyFormName.value.trim()) {
    backendStatus.value = '请输入用户名称'
    return
  }
  try {
    const result = await sendJson<{ id: string; name: string; token: string; user_type: string; purpose: string | null }>(
      '/api-keys', 'POST',
      { name: apiKeyFormName.value.trim(), user_type: apiKeyFormUserType.value, purpose: apiKeyFormPurpose.value.trim() || null },
    )
    apiKeyCreatedToken.value = result.token
    apiKeyCreatedName.value = result.name
    apiKeyCreateDialogOpen.value = false
    backendStatus.value = `API Key 创建成功：${result.name}`
    await fetchApiKeys(1)
  } catch {
    backendStatus.value = 'API Key 创建失败'
  }
}

async function toggleApiKeyActive(item: ApiKeyItem): Promise<void> {
  try {
    await sendJson(`/api-keys/${item.id}`, 'PATCH', { is_active: !item.is_active })
    await fetchApiKeys(apiKeyManagePage.value)
    backendStatus.value = `${item.name} 已${item.is_active ? '禁用' : '启用'}`
  } catch {
    backendStatus.value = '操作失败'
  }
}

async function deleteApiKey(id: string): Promise<void> {
  try {
    await sendJson(`/api-keys/${id}`, 'DELETE', {})
    await fetchApiKeys(apiKeyManagePage.value)
    backendStatus.value = 'API Key 已删除'
  } catch {
    backendStatus.value = '删除失败'
  }
}

function openApiKeyEditDialog(item: ApiKeyItem): void {
  apiKeyEditId.value = item.id
  apiKeyEditName.value = item.name
  apiKeyEditUserType.value = item.user_type
  apiKeyEditPurpose.value = item.purpose ?? ''
  apiKeyEditDialogOpen.value = true
}

async function submitApiKeyEdit(): Promise<void> {
  if (!apiKeyEditName.value.trim()) {
    backendStatus.value = '请输入用户名称'
    return
  }
  try {
    await sendJson(`/api-keys/${apiKeyEditId.value}`, 'PATCH', {
      name: apiKeyEditName.value.trim(),
      user_type: apiKeyEditUserType.value,
      purpose: apiKeyEditPurpose.value.trim() || null,
    })
    apiKeyEditDialogOpen.value = false
    backendStatus.value = 'API Key 更新成功'
    await fetchApiKeys(apiKeyManagePage.value)
  } catch {
    backendStatus.value = 'API Key 更新失败'
  }
}

function setApiKeyManagePageSize(value: number): void {
  apiKeyManagePageSize.value = value
  fetchApiKeys(1)
}

function goApiKeyPage(delta: number): void {
  const next = apiKeyManagePage.value + delta
  if (next >= 1 && next <= Math.max(1, Math.ceil(apiKeyManageTotal.value / apiKeyManagePageSize.value))) {
    fetchApiKeys(next)
  }
}

function jumpToApiKeyPage(): void {
  const page = parseInt(apiKeyManageJumpPage.value, 10)
  if (!isNaN(page) && page >= 1) {
    fetchApiKeys(page)
  }
}

async function fetchModelEndpoints(page = 1): Promise<void> {
  const pageData = await fetchJson<{ page: number; page_size: number; total: number; items: ModelEndpointItem[] }>(
    `/model-endpoints?page=${page}&page_size=${modelEndpointManagePageSize.value}`,
  )
  modelEndpointList.value = pageData.items
  modelEndpointManageTotal.value = pageData.total
  modelEndpointManagePage.value = pageData.page
  modelEndpointManageJumpPage.value = String(pageData.page)
}

function openModelEndpointCreateDialog(): void {
  modelEndpointFormIsEdit.value = false
  modelEndpointFormId.value = ''
  meFormName.value = ''
  meFormIdentifier.value = ''
  meFormProvider.value = 'openai'
  meFormEndpointUrl.value = ''
  meFormApiKeyRef.value = ''
  meFormModelName.value = ''
  meFormModelVersion.value = 'v1.0'
  meFormMaxTokens.value = '4096'
  meFormTemperature.value = '0.7'
  meFormTimeoutSeconds.value = '120'
  meFormIsAvailable.value = true
  meFormStatus.value = 'active'
  meApiKeyVisible.value = false
  modelEndpointFormDialogOpen.value = true
}

function openModelEndpointEditDialog(item: ModelEndpointItem): void {
  modelEndpointFormIsEdit.value = true
  modelEndpointFormId.value = item.id
  meFormName.value = item.name
  meFormIdentifier.value = item.identifier
  meFormProvider.value = item.provider
  meFormEndpointUrl.value = item.endpoint_url
  meFormApiKeyRef.value = item.api_key_ref ?? ''
  meFormModelName.value = item.model_name
  meFormModelVersion.value = item.model_version
  meFormMaxTokens.value = String(item.max_tokens)
  meFormTemperature.value = String(item.temperature)
  meFormTimeoutSeconds.value = String(item.timeout_seconds)
  meFormIsAvailable.value = item.is_available
  meFormStatus.value = item.status
  meApiKeyVisible.value = false
  modelEndpointFormDialogOpen.value = true
}

async function submitModelEndpoint(): Promise<void> {
  if (!meFormName.value.trim() || !meFormIdentifier.value.trim() || !meFormEndpointUrl.value.trim() || !meFormModelName.value.trim()) {
    backendStatus.value = '请填写必填字段（名称、标识符、接口地址、模型名称）'
    return
  }
  const body: Record<string, unknown> = {
    name: meFormName.value.trim(),
    identifier: meFormIdentifier.value.trim(),
    provider: meFormProvider.value,
    endpoint_url: meFormEndpointUrl.value.trim(),
    api_key_ref: meFormApiKeyRef.value.trim() || null,
    model_name: meFormModelName.value.trim(),
    model_version: meFormModelVersion.value.trim(),
    max_tokens: parseInt(meFormMaxTokens.value, 10) || 4096,
    temperature: parseFloat(meFormTemperature.value) || 0.7,
    timeout_seconds: parseInt(meFormTimeoutSeconds.value, 10) || 120,
    is_available: meFormIsAvailable.value,
    status: meFormStatus.value,
  }
  try {
    if (modelEndpointFormIsEdit.value) {
      await sendJson(`/model-endpoints/${modelEndpointFormId.value}`, 'PATCH', body)
      backendStatus.value = '模型端点更新成功'
    } else {
      await sendJson('/model-endpoints', 'POST', body)
      backendStatus.value = '模型端点创建成功'
    }
    modelEndpointFormDialogOpen.value = false
    await fetchModelEndpoints(modelEndpointManagePage.value)
  } catch {
    backendStatus.value = '操作失败'
  }
}

async function deleteModelEndpoints(ids: string[]): Promise<void> {
  try {
    await sendJson('/model-endpoints', 'DELETE', { ids })
    backendStatus.value = `已删除 ${ids.length} 个模型端点`
    await fetchModelEndpoints(modelEndpointManagePage.value)
  } catch {
    backendStatus.value = '删除失败'
  }
}

function setModelEndpointPageSize(value: number): void {
  modelEndpointManagePageSize.value = value
  fetchModelEndpoints(1)
}

function goModelEndpointPage(delta: number): void {
  const next = modelEndpointManagePage.value + delta
  if (next >= 1 && next <= Math.max(1, Math.ceil(modelEndpointManageTotal.value / modelEndpointManagePageSize.value))) {
    fetchModelEndpoints(next)
  }
}

function jumpToModelEndpointPage(): void {
  const page = parseInt(modelEndpointManageJumpPage.value, 10)
  if (!isNaN(page) && page >= 1) {
    fetchModelEndpoints(page)
  }
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
  const pageIds = dataSources.value.map((item) => item.id)
  if (allDataSourcesOnPageSelected.value) {
    selectedManageDataSourceIds.value = selectedManageDataSourceIds.value.filter((id) => !pageIds.includes(id))
    return
  }
  selectedManageDataSourceIds.value = Array.from(new Set([...selectedManageDataSourceIds.value, ...pageIds]))
}

function setDataSourceManagePageSize(size: number): void {
  dataSourceManagePageSize.value = size
  dataSourceManagePage.value = 1
  dataSourceManageJumpPage.value = '1'
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
    const ids = [...selectedManageDataSourceIds.value]
    await sendJson('/data-sources', 'DELETE', { ids })
    await fetchDataSources(dataSourceManagePage.value)
    selectedManageDataSourceIds.value = selectedManageDataSourceIds.value.filter((id) => !ids.includes(id))
    backendStatus.value = `数据源批量删除成功（${ids.length} 条）`
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
  const pageIds = filterRules.value.map((item) => item.id)
  if (allFilterRulesOnPageSelected.value) {
    selectedManageFilterRuleIds.value = selectedManageFilterRuleIds.value.filter((id) => !pageIds.includes(id))
    return
  }
  selectedManageFilterRuleIds.value = Array.from(new Set([...selectedManageFilterRuleIds.value, ...pageIds]))
}

function setFilterRuleManagePageSize(size: number): void {
  filterRuleManagePageSize.value = size
  filterRuleManagePage.value = 1
  filterRuleManageJumpPage.value = '1'
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
    selectedManageFilterRuleIds.value = selectedManageFilterRuleIds.value.filter((id) => !ids.includes(id))
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
}

function openTemplateDetail(item: QuestionTemplateItem): void {
  selectedTemplate.value = item
  templateDetailDialogOpen.value = true
}

function openTemplateEdit(item: QuestionTemplateItem): void {
  selectedTemplate.value = item
  templateEditForm.id = item.id
  templateEditForm.templateIndex = item.templateIndex
  templateEditForm.questionTemplate = item.questionTemplate
  templateEditForm.difficultyLevel = item.difficultyLevel
  templateEditForm.candidateAnswerType = item.candidateAnswerType
  templateEditForm.eventDomain = item.eventDomain
  templateEditForm.eventType = item.eventType
  templateEditForm.eventTypeId = item.eventTypeId
  templateEditForm.operationLevel = item.operationLevel
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
  const pageIds = templates.value.map((item) => item.id)
  if (allTemplatesOnPageSelected.value) {
    selectedManageTemplateIds.value = selectedManageTemplateIds.value.filter((id) => !pageIds.includes(id))
    return
  }
  selectedManageTemplateIds.value = Array.from(new Set([...selectedManageTemplateIds.value, ...pageIds]))
}

function setTemplateManagePageSize(size: number): void {
  templateManagePageSize.value = size
  templateManagePage.value = 1
  templateManageJumpPage.value = '1'
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
    if (!Number.isFinite(createTemplateForm.templateIndex) || createTemplateForm.templateIndex <= 0) {
      backendStatus.value = '问题模板新增失败：序号必须是正整数'
      return
    }

    await sendJson('/question-templates', 'POST', {
      template_index: Math.trunc(createTemplateForm.templateIndex),
      question_template: createTemplateForm.questionTemplate.trim(),
      difficulty_level: createTemplateForm.difficultyLevel,
      candidate_answer_type: createTemplateForm.candidateAnswerType,
      event_domain: createTemplateForm.eventDomain.trim(),
      event_type: createTemplateForm.eventType.trim(),
      event_type_id: createTemplateForm.eventTypeId.trim(),
      operation_level: createTemplateForm.operationLevel.trim(),
      status: createTemplateForm.status,
      version: createTemplateForm.version.trim(),
    })
    await fetchTemplates(1)
    backendStatus.value = '问题模板新增成功'
    createTemplateDialogOpen.value = false
    createTemplateForm.templateIndex = 1
    createTemplateForm.questionTemplate = ''
    createTemplateForm.difficultyLevel = 'L2'
    createTemplateForm.candidateAnswerType = 'dynamic'
    createTemplateForm.eventDomain = ''
    createTemplateForm.eventType = ''
    createTemplateForm.eventTypeId = ''
    createTemplateForm.operationLevel = ''
    createTemplateForm.status = 'active'
    createTemplateForm.version = 'v1.0'
  } catch {
    backendStatus.value = '问题模板新增失败：请检查字段与后端接口'
  }
}

async function submitEditTemplate(): Promise<void> {
  try {
    if (!Number.isFinite(templateEditForm.templateIndex) || templateEditForm.templateIndex <= 0) {
      backendStatus.value = '问题模板更新失败：序号必须是正整数'
      return
    }

    await sendJson(`/question-templates/${templateEditForm.id}`, 'PATCH', {
      template_index: Math.trunc(templateEditForm.templateIndex),
      question_template: templateEditForm.questionTemplate.trim(),
      difficulty_level: templateEditForm.difficultyLevel,
      candidate_answer_type: templateEditForm.candidateAnswerType,
      event_domain: templateEditForm.eventDomain.trim(),
      event_type: templateEditForm.eventType.trim(),
      event_type_id: templateEditForm.eventTypeId.trim(),
      operation_level: templateEditForm.operationLevel.trim(),
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
    const ids = [...selectedManageTemplateIds.value]
    await sendJson('/question-templates', 'DELETE', { ids })
    await fetchTemplates(templateManagePage.value)
    selectedManageTemplateIds.value = selectedManageTemplateIds.value.filter((id) => !ids.includes(id))
    backendStatus.value = `问题模板批量删除成功（${ids.length} 条）`
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
      await fetchHomeEvents()
      requestManageEventsReload()
      backendStatus.value = `事件批量删除成功（${ids.length} 条）`
    }
    selectedManageEventIds.value = []
    if (!backendOnline.value && currentView.value === 'events') {
      requestManageEventsReload()
    }
  } catch {
    backendStatus.value = '事件批量删除失败：请检查后端接口或参数格式'
  }
}

async function reviewSelectedEvents(targetStatus: 'passed' | 'filtered'): Promise<void> {
  const ids = [...selectedManageEventIds.value]
  if (ids.length === 0) {
    backendStatus.value = '请先勾选要批量审核的事件'
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
      await fetchHomeEvents()
      requestManageEventsReload()
      backendStatus.value = `事件审核完成：${ids.length} 条 -> ${targetStatus}`
    }
    selectedManageEventIds.value = selectedManageEventIds.value.filter((id) => !ids.includes(id))
    if (!backendOnline.value && currentView.value === 'events') {
      requestManageEventsReload()
    }
  } catch {
    backendStatus.value = '事件审核失败：请检查后端接口或参数格式'
  } finally {
    eventReviewProcessing.value = false
  }
}

function openQuestionDeleteReasonDialog(ids: string[], closeQuestionEditAfterDelete: boolean): void {
  pendingDeleteQuestionIds.value = [...ids]
  pendingDeleteCloseQuestionEdit.value = closeQuestionEditAfterDelete
  questionDeleteReasonPreset.value = questionDeleteReasonOptions[0] ?? ''
  questionDeleteReasonCustom.value = ''
  questionDeleteReasonDialogOpen.value = true
}

function closeQuestionDeleteReasonDialog(): void {
  questionDeleteReasonDialogOpen.value = false
  questionDeleteReasonPreset.value = ''
  questionDeleteReasonCustom.value = ''
  pendingDeleteQuestionIds.value = []
  pendingDeleteCloseQuestionEdit.value = false
}

function resolvedQuestionDeleteReason(): string {
  if (questionDeleteReasonPreset.value === '__custom__') {
    return questionDeleteReasonCustom.value.trim()
  }
  return questionDeleteReasonPreset.value.trim()
}

async function deleteQuestionsByIds(ids: string[], deleteReason: string): Promise<void> {
  if (!backendOnline.value) {
    const deletedAt = new Date().toISOString()
    for (const item of questions.value) {
      if (!ids.includes(item.id) || item.deletedAt) {
        continue
      }
      item.deletedAt = deletedAt
      item.deleteReason = deleteReason
    }
    backendStatus.value = `后端离线：已删除 ${ids.length} 条模拟问题`
  } else {
    await sendJson('/questions', 'DELETE', { ids, delete_reason: deleteReason })
    await hydrateFromBackend()
    requestManageQuestionsReload()
    backendStatus.value = `问题删除成功（${ids.length} 条）`
  }
  if (ids.includes(selectedQuestionId.value)) {
    selectedQuestionId.value = questions.value[0]?.id ?? ''
  }
  selectedManageQuestionIds.value = selectedManageQuestionIds.value.filter((id) => !ids.includes(id))
  if (!backendOnline.value && currentView.value === 'questions') {
    requestManageQuestionsReload()
  }
}

async function confirmQuestionDeleteWithReason(): Promise<void> {
  const ids = [...pendingDeleteQuestionIds.value]
  if (ids.length === 0) {
    closeQuestionDeleteReasonDialog()
    return
  }
  const deleteReason = resolvedQuestionDeleteReason()
  if (!deleteReason) {
    backendStatus.value = '删除失败：请填写删除原因'
    return
  }
  const shouldCloseQuestionEdit = pendingDeleteCloseQuestionEdit.value
  try {
    await deleteQuestionsByIds(ids, deleteReason)
    closeQuestionDeleteReasonDialog()
    if (shouldCloseQuestionEdit) {
      questionEditDialogOpen.value = false
    }
  } catch {
    backendStatus.value = '问题删除失败：请检查后端接口或参数格式'
  }
}

async function deleteSelectedQuestionsBatch(): Promise<void> {
  if (selectedManageQuestionIds.value.length === 0) {
    backendStatus.value = '请先勾选要删除的问题'
    return
  }
  const deletableIds = selectedManageQuestionIds.value.filter((id) => {
    const matched = questions.value.find((item) => item.id === id)
    return Boolean(matched) && !matched?.deletedAt
  })
  if (deletableIds.length === 0) {
    backendStatus.value = '所选问题均已删除，无法重复删除'
    return
  }
  openQuestionDeleteReasonDialog(deletableIds, false)
}

async function submitQuestionEdit(): Promise<void> {
  if (!isAdmin.value) {
    backendStatus.value = '当前账号无权限编辑问题'
    questionEditDialogOpen.value = false
    return
  }
  if (!questionEditForm.id) {
    return
  }

  try {
    const title = questionEditForm.title.trim()
    const deadline = questionEditForm.deadline.trim()
    const eventIds = Array.from(new Set(questionEditForm.eventIds)).filter((value) => value.trim().length > 0)
    const answerSpace = questionEditForm.answerSpace.trim()
    const eventDomain = questionEditForm.eventDomain.trim()
    const eventType = questionEditForm.eventType.trim()
    const area = questionEditForm.area.trim()
    const inputType = questionEditForm.inputType.trim()
    const background = questionEditForm.background.trim()
    const matchScoreText = questionEditForm.matchScore.trim()
    const matchScore = matchScoreText ? Number(matchScoreText) : null
    if (!title || !deadline) {
      backendStatus.value = '问题更新失败：请填写标题与截止时间'
      return
    }
    if (matchScoreText && !Number.isFinite(matchScore)) {
      backendStatus.value = '问题更新失败：匹配分数格式无效'
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
        target.matchScore = matchScore
        target.eventDomain = eventDomain
        target.eventType = eventType
        target.area = area
        target.inputType = inputType
        target.background = background
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
      match_score: matchScore,
      event_domain: eventDomain || null,
      event_type: eventType || null,
      area: area || null,
      input_type: inputType || null,
      background: background || null,
      answer_space: answerSpace || null,
      event_ids: eventIds,
      deadline: normalizedDeadline,
      status: questionEditForm.status,
    })
    await hydrateFromBackend()
    requestManageQuestionsReload()
    backendStatus.value = '问题更新成功（后端）'
    questionEditDialogOpen.value = false
    questionEditEventSearch.value = ''
  } catch {
    backendStatus.value = '问题更新失败：请检查后端接口或参数格式'
  }
}

async function deleteQuestionInEditDialog(): Promise<void> {
  if (!isAdmin.value) {
    backendStatus.value = '当前账号无权限编辑问题'
    questionEditDialogOpen.value = false
    return
  }
  const currentId = questionEditForm.id || selectedQuestionId.value
  if (!currentId) {
    backendStatus.value = '删除失败：未找到问题 ID'
    return
  }
  const target = questions.value.find((item) => item.id === currentId)
  if (target?.deletedAt) {
    backendStatus.value = '已删除问题不允许再次删除'
    return
  }
  openQuestionDeleteReasonDialog([currentId], true)
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
      if (currentView.value === 'events') {
        requestManageEventsReload()
      }
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
    await fetchHomeEvents()
    requestManageEventsReload()
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

function parseLevelFilter(value: string): number | null {
  if (value === 'L1') {
    return 1
  }
  if (value === 'L2') {
    return 2
  }
  if (value === 'L3') {
    return 3
  }
  if (value === 'L4') {
    return 4
  }
  return null
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
    url: item.url,
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
  const normalizedStatus = normalizeQuestionStatus(item.status)
  return {
    id: item.id,
    eventIds,
    level: normalizeLevel(item.level),
    title: item.content,
    matchScore: typeof item.match_score === 'number' ? item.match_score : null,
    eventDomain: item.event_domain ?? '',
    eventType: item.event_type ?? '',
    area: item.area ?? '',
    inputType: item.input_type ?? '',
    background: item.background ?? '',
    answerSpace: item.answer_space ?? '',
    hypothesis: item.hypothesis?.trim() ?? '',
    deadline: item.deadline,
    status: normalizedStatus,
    groundTruth: normalizedStatus === 'closed'
      ? '后端状态显示已解析，请补充真实结果详情。'
      : '待真实结果回填。',
    deleteReason: item.delete_reason ?? '',
    deletedAt: item.deleted_at ?? '',
    createdAt: item.created_at ?? item.deadline,
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
    templateIndex: item.template_index,
    questionTemplate: item.question_template,
    difficultyLevel: item.difficulty_level,
    candidateAnswerType: item.candidate_answer_type,
    eventDomain: item.event_domain,
    eventType: item.event_type,
    eventTypeId: item.event_type_id,
    operationLevel: item.operation_level,
    status: item.status,
    version: item.version,
    usageCount: item.usage_count,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  }
}

function toCommunityPredictionItem(item: BackendCommunityPredictionItem): CommunityPredictionItem {
  return {
    id: item.id,
    questionId: item.question_id,
    userId: item.user_id,
    username: item.username,
    predictionContent: item.prediction_content,
    confidence: item.confidence,
    reasoning: item.reasoning,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  }
}

function toAgentPredictionItem(item: BackendAgentPredictionItem): AgentPredictionItem {
  return {
    id: item.id,
    questionId: item.question_id,
    apiKeyId: item.api_key_id,
    agentName: item.agent_name,
    userType: item.user_type,
    purpose: item.purpose,
    modelName: item.model_name,
    predictionContent: item.prediction_content,
    reasoning: item.reasoning,
    confidence: item.confidence,
    evidence: item.evidence,
    questionText: item.question_text,
    isCorrect: item.is_correct,
    score: item.score,
    status: item.status,
    createdAt: item.created_at,
  }
}

function toQuestionCommentItem(item: BackendQuestionCommentItem): QuestionCommentItem {
  return {
    id: item.id,
    questionId: item.question_id,
    userId: item.user_id,
    username: item.username,
    content: item.content,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  }
}

function normalizeQuestionStatus(value: string): QuestionStatus {
  const normalized = value.trim().toLowerCase()
  if (normalized === 'draft') {
    return 'draft'
  }
  if (normalized === 'pending_review') {
    return 'pending_review'
  }
  if (normalized === 'published') {
    return 'published'
  }
  if (normalized === 'expired') {
    return 'expired'
  }
  if (normalized === 'matched') {
    return 'matched'
  }
  if (normalized === 'closed') {
    return 'closed'
  }
  return 'draft'
}

function canInteractWithQuestion(question: QuestionItem | null): boolean {
  if (!question) {
    return false
  }
  return question.status !== 'expired'
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

function resetQuestionEventSearchState(): void {
  questionEventSearchSeq.value += 1
  questionEventOptions.value = []
  questionEventSearchTotal.value = 0
  questionEventSearchLoading.value = false
  questionEventSearchLoadingMore.value = false
  questionEventSearchPage.value = 0
  questionEventSearchHasMore.value = true
  questionEventSearchKeyword.value = ''
  questionEventSearchMode.value = null
}

function shouldLoadNextQuestionEventPage(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) {
    return false
  }
  const threshold = 56
  return target.scrollTop + target.clientHeight >= target.scrollHeight - threshold
}

async function loadMoreQuestionEventOptions(): Promise<void> {
  if (!backendOnline.value) {
    questionEventOptions.value = []
    questionEventSearchTotal.value = 0
    questionEventSearchLoading.value = false
    questionEventSearchLoadingMore.value = false
    questionEventSearchHasMore.value = false
    return
  }
  if (questionEventSearchLoading.value || questionEventSearchLoadingMore.value || !questionEventSearchHasMore.value) {
    return
  }

  const nextPage = questionEventSearchPage.value + 1
  const requestSeq = questionEventSearchSeq.value + 1
  questionEventSearchSeq.value = requestSeq
  if (nextPage === 1) {
    questionEventSearchLoading.value = true
  } else {
    questionEventSearchLoadingMore.value = true
  }

  try {
    const query = encodeURIComponent(questionEventSearchKeyword.value)
    const eventPage = await fetchJson<BackendPage<BackendEventItem>>(
      `/events/search?keyword=${query}&filter_status=passed&page=${nextPage}&page_size=50`,
    )
    if (requestSeq !== questionEventSearchSeq.value) {
      return
    }

    const mapped = sortByEventTimeDesc(eventPage.items.map(toEventItem))
    const merged = nextPage === 1 ? [] : [...questionEventOptions.value]
    for (const item of mapped) {
      if (!merged.some((target) => target.id === item.id)) {
        merged.push(item)
      }
    }
    questionEventOptions.value = merged
    questionEventSearchTotal.value = eventPage.total
    questionEventSearchPage.value = nextPage
    questionEventSearchHasMore.value = merged.length < eventPage.total && mapped.length > 0

    if (
      questionEventSearchMode.value === 'create' &&
      nextPage === 1 &&
      mapped.length > 0 &&
      !mapped.some((item) => item.id === selectedEventId.value)
    ) {
      selectedEventId.value = mapped[0]?.id ?? selectedEventId.value
    }
    if (questionEventSearchMode.value === 'create' && nextPage === 1 && selectedEventIdsForQuestion.value.length === 0) {
      selectedEventIdsForQuestion.value = selectedEventId.value ? [selectedEventId.value] : []
    }
  } catch {
    if (requestSeq !== questionEventSearchSeq.value) {
      return
    }
    if (nextPage === 1) {
      questionEventOptions.value = []
      questionEventSearchTotal.value = 0
      questionEventSearchHasMore.value = false
    }
    backendStatus.value = '事件搜索失败：请检查后端搜索接口'
  } finally {
    if (requestSeq === questionEventSearchSeq.value) {
      questionEventSearchLoading.value = false
      questionEventSearchLoadingMore.value = false
    }
  }
}

async function fetchQuestionEventOptions(keyword: string, mode: 'create' | 'edit'): Promise<void> {
  questionEventSearchMode.value = mode
  questionEventSearchKeyword.value = keyword.trim()
  questionEventSearchPage.value = 0
  questionEventSearchHasMore.value = true
  questionEventOptions.value = []
  questionEventSearchTotal.value = 0
  questionEventSearchLoading.value = false
  questionEventSearchLoadingMore.value = false
  await loadMoreQuestionEventOptions()
}

function handleQuestionEventSelectScroll(mode: 'create' | 'edit', event: Event): void {
  if (!backendOnline.value) {
    return
  }
  if (questionEventSearchMode.value !== mode) {
    return
  }
  if (!shouldLoadNextQuestionEventPage(event.target)) {
    return
  }
  void loadMoreQuestionEventOptions()
}

async function ensureQuestionEventOptionsByIds(eventIds: string[], requestSeq?: number): Promise<void> {
  if (requestSeq !== undefined && requestSeq !== questionFeedReloadSeq.value) {
    return
  }
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
  if (requestSeq !== undefined && requestSeq !== questionFeedReloadSeq.value) {
    return
  }
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

function applyPredictionFormFromMine(questionId: string): void {
  const mine = (questionPredictions.value[questionId] ?? []).find((item) => item.userId === authUser.value?.id)
  const options = currentQuestionAnswerOptions.value
  predictionForm.predictionContent = mine?.predictionContent ?? ''
  predictionForm.selectedAnswerId = mine ? matchPredictionToAnswerOptionId(mine.predictionContent, options) : ''
  predictionForm.confidence = mine?.confidence !== null && mine?.confidence !== undefined ? String(mine.confidence) : ''
  predictionForm.reasoning = mine?.reasoning ?? ''
}

async function loadQuestionInteractions(questionId: string): Promise<void> {
  if (!backendOnline.value || !isAuthenticated.value) {
    return
  }
  questionInteractionLoading.value = true
  try {
    const [predictionResult, commentResult, agentPredictionResult] = await Promise.all([
      fetchJson<{ items: BackendCommunityPredictionItem[] }>(
        `/community-predictions?question_id=${encodeURIComponent(questionId)}`,
      ),
      fetchJson<{ items: BackendQuestionCommentItem[] }>(`/question-comments?question_id=${encodeURIComponent(questionId)}`),
      fetchJson<BackendAgentPredictionItem[]>(`/agent-predictions/question/${encodeURIComponent(questionId)}`).catch((): BackendAgentPredictionItem[] => []),
    ])
    questionPredictions.value = {
      ...questionPredictions.value,
      [questionId]: predictionResult.items.map(toCommunityPredictionItem),
    }
    questionAgentPredictions.value = {
      ...questionAgentPredictions.value,
      [questionId]: agentPredictionResult.map(toAgentPredictionItem),
    }
    questionComments.value = {
      ...questionComments.value,
      [questionId]: commentResult.items.map(toQuestionCommentItem),
    }
    questionFeedInteractionCounts.value = {
      ...questionFeedInteractionCounts.value,
      [questionId]: {
        predictionCount: predictionResult.items.length,
        commentCount: commentResult.items.length,
      },
    }
    questionFeedParticipation.value = {
      ...questionFeedParticipation.value,
      [questionId]: {
        hasPrediction: predictionResult.items.some((item) => item.user_id === authUser.value?.id),
        myCommentCount: commentResult.items.filter((item) => item.user_id === authUser.value?.id).length,
      },
    }
    applyPredictionFormFromMine(questionId)
  } catch {
    backendStatus.value = '问题互动加载失败：请检查预测和评论接口'
  } finally {
    questionInteractionLoading.value = false
  }
}

function openQuestionComposer(mode: 'prediction' | 'comment'): void {
  const question = manageDetailQuestion.value
  if (!question) {
    return
  }
  if (!canInteractWithQuestion(question)) {
    backendStatus.value = '当前问题不可互动：仅已过期问题禁止预测和评论'
    return
  }
  questionComposerMode.value = mode
}

async function submitMyPrediction(): Promise<void> {
  const question = manageDetailQuestion.value
  if (!question || !backendOnline.value || !isAuthenticated.value) {
    return
  }
  if (!canInteractWithQuestion(question)) {
    backendStatus.value = '仅已过期问题不可提交或修改预测'
    return
  }
  const answerOptions = currentQuestionAnswerOptions.value
  let predictionContent = ''
  if (answerOptions.length > 0) {
    const selected = answerOptions.find((item) => item.id === predictionForm.selectedAnswerId)
    if (!selected) {
      backendStatus.value = '请先选择一个预测答案'
      return
    }
    predictionContent = selected.label
  } else {
    predictionContent = predictionForm.predictionContent.trim()
    if (!predictionContent) {
      backendStatus.value = '预测内容不能为空'
      return
    }
  }
  let parsedConfidence: number | null = null
  const confidenceRaw = predictionForm.confidence == null ? '' : String(predictionForm.confidence).trim()
  if (confidenceRaw) {
    const numeric = Number(confidenceRaw)
    if (!Number.isFinite(numeric) || numeric < 0 || numeric > 100) {
      backendStatus.value = '置信度必须在 0-100 之间'
      return
    }
    parsedConfidence = Number(numeric.toFixed(2))
  }

  predictionSubmitting.value = true
  try {
    await sendJson<BackendCommunityPredictionItem>('/community-predictions', 'POST', {
      question_id: question.id,
      prediction_content: predictionContent,
      confidence: parsedConfidence,
      reasoning: String(predictionForm.reasoning ?? '').trim() || null,
    })
    await loadQuestionInteractions(question.id)
    questionComposerMode.value = null
    pushToast('预测已保存', 'success')
  } catch {
    backendStatus.value = '预测提交失败：请确认问题状态、截止时间与权限'
  } finally {
    predictionSubmitting.value = false
  }
}

async function submitQuestionComment(): Promise<void> {
  const question = manageDetailQuestion.value
  if (!question || !backendOnline.value || !isAuthenticated.value) {
    return
  }
  if (!canInteractWithQuestion(question)) {
    backendStatus.value = '仅已过期问题不可发表评论'
    return
  }
  const content = commentDraft.value.trim()
  if (!content) {
    backendStatus.value = '评论内容不能为空'
    return
  }

  commentSubmitting.value = true
  try {
    await sendJson<BackendQuestionCommentItem>('/question-comments', 'POST', {
      question_id: question.id,
      content,
    })
    commentDraft.value = ''
    await loadQuestionInteractions(question.id)
    questionComposerMode.value = null
    pushToast('评论已发布', 'success')
  } catch {
    backendStatus.value = '评论发布失败：请确认问题状态、截止时间与权限'
  } finally {
    commentSubmitting.value = false
  }
}

async function saveEditedComment(): Promise<void> {
  const question = manageDetailQuestion.value
  if (!question || !backendOnline.value || !isAuthenticated.value || !editingCommentId.value) {
    return
  }

  const content = editingCommentContent.value.trim()
  if (!content) {
    backendStatus.value = '评论内容不能为空'
    return
  }

  commentActionLoading.value = true
  try {
    await sendJson<BackendQuestionCommentItem>(`/question-comments/${editingCommentId.value}`, 'PATCH', { content })
    await loadQuestionInteractions(question.id)
    cancelCommentEdit()
    pushToast('评论已更新', 'success')
  } catch {
    backendStatus.value = '评论更新失败：你只能编辑自己的评论'
  } finally {
    commentActionLoading.value = false
  }
}

async function deleteComment(comment: QuestionCommentItem): Promise<void> {
  const question = manageDetailQuestion.value
  if (!question || !backendOnline.value || !isAuthenticated.value) {
    return
  }
  if (!canDeleteComment(comment)) {
    backendStatus.value = '你无权删除该评论'
    return
  }

  commentActionLoading.value = true
  try {
    await sendJson(`/question-comments/${comment.id}`, 'DELETE', {})
    await loadQuestionInteractions(question.id)
    if (editingCommentId.value === comment.id) {
      cancelCommentEdit()
    }
    pushToast('评论已删除', 'success')
  } catch {
    backendStatus.value = '评论删除失败：仅本人或管理员可删除'
  } finally {
    commentActionLoading.value = false
  }
}

async function cancelMyPrediction(): Promise<void> {
  const question = manageDetailQuestion.value
  const myPrediction = myCurrentPrediction.value
  if (!question || !backendOnline.value || !isAuthenticated.value) {
    return
  }
  if (!myPrediction) {
    return
  }
  if (myPrediction.userId !== authUser.value?.id && !isAdmin.value) {
    backendStatus.value = '你无权取消此预测'
    return
  }

  predictionSubmitting.value = true
  try {
    await sendJson(`/community-predictions/${myPrediction.id}`, 'DELETE', {})
    await loadQuestionInteractions(question.id)
    predictionForm.selectedAnswerId = ''
    predictionForm.predictionContent = ''
    predictionForm.confidence = ''
    predictionForm.reasoning = ''
    questionComposerMode.value = null
    pushToast('预测已取消', 'success')
  } catch {
    backendStatus.value = '预测取消失败：仅本人或管理员可取消'
  } finally {
    predictionSubmitting.value = false
  }
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

function resetManageEventsFeed(): void {
  eventManageReloadSeq.value += 1
  manageEvents.value = []
  manageEventTotal.value = backendOnline.value ? 0 : localFilteredManageEvents.value.length
  eventManagePage.value = 0
  eventManageHasMore.value = true
  selectedManageEventIds.value = []
}

function requestManageEventsReload(): void {
  eventManageReloadPending = false
  resetManageEventsFeed()
  if (eventManageSearchLoading.value) {
    eventManageReloadPending = true
    return
  }
  void loadManageEventsNextPage()
}

async function loadManageEventsNextPage(): Promise<void> {
  if (eventManageSearchLoading.value || !eventManageHasMore.value) {
    return
  }

  const requestSeq = eventManageReloadSeq.value
  eventManageSearchLoading.value = true
  try {
    const nextPage = eventManagePage.value + 1
    if (!backendOnline.value) {
      const start = manageEvents.value.length
      const batch = localFilteredManageEvents.value.slice(start, start + eventManagePageSize.value)
      if (requestSeq !== eventManageReloadSeq.value) {
        return
      }
      manageEvents.value = [...manageEvents.value, ...batch]
      manageEventTotal.value = localFilteredManageEvents.value.length
      eventManagePage.value = nextPage
      eventManageHasMore.value = manageEvents.value.length < localFilteredManageEvents.value.length && batch.length > 0
      return
    }

    const query = new URLSearchParams()
    query.set('keyword', eventManageSearchKeyword.value.trim())
    const sourceSystem = eventManageSourceSystem.value.trim()
    const status = eventManageFilterStatus.value.trim()
    const fromIso = toIsoFromLocalDateTime(eventManageTimeFrom.value)
    const toIso = toIsoFromLocalDateTime(eventManageTimeTo.value)
    if (sourceSystem) {
      query.set('source_system', sourceSystem)
    }
    if (status) {
      query.set('filter_status', status)
    }
    if (fromIso) {
      query.set('event_time_from', fromIso)
    }
    if (toIso) {
      query.set('event_time_to', toIso)
    }
    query.set('page', String(nextPage))
    query.set('page_size', String(eventManagePageSize.value))
    const eventPage = await fetchJson<BackendPage<BackendEventItem>>(`/events/search?${query.toString()}`)
    if (requestSeq !== eventManageReloadSeq.value) {
      return
    }

    const batch = sortByEventTimeDesc(eventPage.items.map(toEventItem))
    manageEvents.value = [...manageEvents.value, ...batch]
    manageEventTotal.value = eventPage.total
    eventManagePage.value = nextPage
    eventManageHasMore.value = manageEvents.value.length < eventPage.total && batch.length > 0
  } catch {
    if (requestSeq === eventManageReloadSeq.value) {
      backendStatus.value = '事件管理加载失败：请检查后端事件搜索接口'
      eventManageHasMore.value = false
    }
  } finally {
    eventManageSearchLoading.value = false
    if (eventManageReloadPending) {
      eventManageReloadPending = false
      void loadManageEventsNextPage()
    }
  }
}

function resetManageQuestionsFeed(): void {
  questionManageReloadSeq.value += 1
  manageQuestions.value = []
  questionManageTotal.value = backendOnline.value ? 0 : localFilteredManageQuestions.value.length
  questionManagePage.value = 0
  questionManageHasMore.value = true
  selectedManageQuestionIds.value = []
}

function requestManageQuestionsReload(): void {
  questionManageReloadPending = false
  resetManageQuestionsFeed()
  if (questionManageSearchLoading.value) {
    questionManageReloadPending = true
    return
  }
  void loadManageQuestionsNextPage()
}

async function loadManageQuestionsNextPage(): Promise<void> {
  if (questionManageSearchLoading.value || !questionManageHasMore.value) {
    return
  }

  const requestSeq = questionManageReloadSeq.value
  questionManageSearchLoading.value = true
  try {
    const nextPage = questionManagePage.value + 1
    if (!backendOnline.value) {
      const start = manageQuestions.value.length
      const batch = localFilteredManageQuestions.value.slice(start, start + questionManagePageSize.value)
      if (requestSeq !== questionManageReloadSeq.value) {
        return
      }
      manageQuestions.value = [...manageQuestions.value, ...batch]
      questionManageTotal.value = localFilteredManageQuestions.value.length
      questionManagePage.value = nextPage
      questionManageHasMore.value = manageQuestions.value.length < localFilteredManageQuestions.value.length && batch.length > 0
      return
    }

    const query = new URLSearchParams()
    query.set('keyword', questionManageSearchKeyword.value.trim())
    const eventDomain = questionManageFilterEventDomain.value.trim()
    const eventType = questionManageFilterEventType.value.trim()
    const status = questionManageFilterStatus.value.trim()
    const level = parseLevelFilter(questionManageFilterLevel.value.trim())
    const createdFrom = toIsoFromLocalDateTime(questionManageFilterDeadlineFrom.value)
    const createdTo = toIsoFromLocalDateTime(questionManageFilterDeadlineTo.value)
    if (eventDomain) {
      query.set('event_domain', eventDomain)
    }
    if (eventType) {
      query.set('event_type', eventType)
    }
    if (status) {
      query.set('status', status)
    }
    if (level !== null) {
      query.set('level', String(level))
    }
    if (createdFrom) {
      query.set('created_from', createdFrom)
    }
    if (createdTo) {
      query.set('created_to', createdTo)
    }
    query.set('deleted_mode', questionManageDeletedMode.value)
    query.set('page', String(nextPage))
    query.set('page_size', String(questionManagePageSize.value))
    const questionPage = await fetchJson<BackendPage<BackendQuestionItem>>(`/questions/search?${query.toString()}`)
    if (requestSeq !== questionManageReloadSeq.value) {
      return
    }

    const batch = questionPage.items.map(toQuestionItem)
    const batchEventIds = Array.from(new Set(batch.flatMap((item) => item.eventIds)))
    await ensureQuestionEventOptionsByIds(batchEventIds, requestSeq)
    if (requestSeq !== questionManageReloadSeq.value) {
      return
    }
    manageQuestions.value = [...manageQuestions.value, ...batch]
    questionManageTotal.value = questionPage.total
    questionManagePage.value = nextPage
    questionManageHasMore.value = manageQuestions.value.length < questionPage.total && batch.length > 0
  } catch {
    if (requestSeq === questionManageReloadSeq.value) {
      backendStatus.value = '问题管理加载失败：请检查后端问题搜索接口'
      questionManageHasMore.value = false
    }
  } finally {
    questionManageSearchLoading.value = false
    if (questionManageReloadPending) {
      questionManageReloadPending = false
      void loadManageQuestionsNextPage()
    }
  }
}

function resetQuestionFeed(): void {
  questionFeedReloadSeq.value += 1
  questionFeedItems.value = []
  questionFeedPage.value = 0
  questionFeedTotal.value = 0
  questionFeedHasMore.value = true
  questionFeedInteractionCounts.value = {}
  questionFeedParticipation.value = {}
}

function requestQuestionFeedReload(): void {
  questionFeedReloadPending = false
  resetQuestionFeed()
  if (questionFeedLoading.value) {
    questionFeedReloadPending = true
    return
  }
  void loadQuestionFeedNextPage()
}

function resetQuestionFeedFilters(): void {
  questionFeedFilterResetting = true
  if (questionFeedSearchTimer !== undefined) {
    window.clearTimeout(questionFeedSearchTimer)
    questionFeedSearchTimer = undefined
  }
  questionFeedSearchKeyword.value = ''
  questionFeedFilterEventDomain.value = ''
  questionFeedFilterEventType.value = ''
  questionFeedFilterDeadlineFrom.value = ''
  questionFeedFilterDeadlineTo.value = ''
  questionFeedFilterStatus.value = ''
  questionFeedFilterLevel.value = ''
  questionFeedFilterResetting = false
  if (backendOnline.value && currentView.value === 'questionStream') {
    requestQuestionFeedReload()
  }
}

function ensureQuestionFeedCounts(questionIds: string[]): void {
  const next = { ...questionFeedInteractionCounts.value }
  const participationNext = { ...questionFeedParticipation.value }
  for (const questionId of questionIds) {
    if (!next[questionId]) {
      next[questionId] = { predictionCount: 0, commentCount: 0 }
    }
    if (!participationNext[questionId]) {
      participationNext[questionId] = { hasPrediction: false, myCommentCount: 0 }
    }
  }
  questionFeedInteractionCounts.value = next
  questionFeedParticipation.value = participationNext
}

async function hydrateQuestionFeedCounts(questionIds: string[], requestSeq?: number): Promise<void> {
  if (requestSeq !== undefined && requestSeq !== questionFeedReloadSeq.value) {
    return
  }
  if (!backendOnline.value || !isAuthenticated.value || questionIds.length === 0) {
    if (requestSeq === undefined || requestSeq === questionFeedReloadSeq.value) {
      ensureQuestionFeedCounts(questionIds)
    }
    return
  }

  const uniqueIds = Array.from(new Set(questionIds)).filter((questionId) => !questionFeedInteractionCounts.value[questionId])
  if (uniqueIds.length === 0) {
    return
  }

  try {
    const query = new URLSearchParams()
    for (const questionId of uniqueIds) {
      query.append('question_ids', questionId)
    }
    const statsResult = await fetchJson<BackendQuestionCommunityStatsResponse>(
      `/questions/community-stats?${query.toString()}`,
    )
    if (requestSeq !== undefined && requestSeq !== questionFeedReloadSeq.value) {
      return
    }

    const next = { ...questionFeedInteractionCounts.value }
    const participationNext = { ...questionFeedParticipation.value }
    for (const row of statsResult.items) {
      next[row.question_id] = {
        predictionCount: row.prediction_count,
        commentCount: row.comment_count,
      }
      participationNext[row.question_id] = {
        hasPrediction: row.has_prediction,
        myCommentCount: row.my_comment_count,
      }
    }
    questionFeedInteractionCounts.value = next
    questionFeedParticipation.value = participationNext
  } catch {
    if (requestSeq === undefined || requestSeq === questionFeedReloadSeq.value) {
      ensureQuestionFeedCounts(uniqueIds)
    }
  }
}

async function loadQuestionFeedNextPage(): Promise<void> {
  if (questionFeedLoading.value || !questionFeedHasMore.value) {
    return
  }

  const requestSeq = questionFeedReloadSeq.value
  questionFeedLoading.value = true
  try {
    const nextPage = questionFeedPage.value + 1
    if (!backendOnline.value) {
      const source = [...questions.value].sort(
        (a, b) => new Date(b.deadline).getTime() - new Date(a.deadline).getTime(),
      )
      const start = (nextPage - 1) * 10
      const batch = source.slice(start, start + 10)
      if (requestSeq !== questionFeedReloadSeq.value) {
        return
      }
      questionFeedItems.value = [...questionFeedItems.value, ...batch]
      questionFeedPage.value = nextPage
      questionFeedTotal.value = source.length
      questionFeedHasMore.value = questionFeedItems.value.length < source.length && batch.length > 0
      ensureQuestionFeedCounts(batch.map((item) => item.id))
      return
    }

    const query = new URLSearchParams()
    query.set('keyword', questionFeedSearchKeyword.value.trim())
    const eventDomain = questionFeedFilterEventDomain.value.trim()
    const eventType = questionFeedFilterEventType.value.trim()
    const status = questionFeedFilterStatus.value.trim()
    const level = parseLevelFilter(questionFeedFilterLevel.value.trim())
    const createdFrom = toIsoFromLocalDateTime(questionFeedFilterDeadlineFrom.value)
    const createdTo = toIsoFromLocalDateTime(questionFeedFilterDeadlineTo.value)
    if (eventDomain) {
      query.set('event_domain', eventDomain)
    }
    if (eventType) {
      query.set('event_type', eventType)
    }
    if (status) {
      query.set('status', status)
    }
    if (level !== null) {
      query.set('level', String(level))
    }
    if (createdFrom) {
      query.set('created_from', createdFrom)
    }
    if (createdTo) {
      query.set('created_to', createdTo)
    }
    query.set('page', String(nextPage))
    query.set('page_size', '10')
    const pageData = await fetchJson<BackendPage<BackendQuestionItem>>(`/questions/search?${query.toString()}`)
    if (requestSeq !== questionFeedReloadSeq.value) {
      return
    }
    const batch = pageData.items.map(toQuestionItem)
    const batchEventIds = Array.from(new Set(batch.flatMap((item) => item.eventIds)))
    await ensureQuestionEventOptionsByIds(batchEventIds, requestSeq)
    if (requestSeq !== questionFeedReloadSeq.value) {
      return
    }
    questionFeedItems.value = [...questionFeedItems.value, ...batch]
    questionFeedPage.value = nextPage
    questionFeedTotal.value = pageData.total
    questionFeedHasMore.value = questionFeedItems.value.length < pageData.total && batch.length > 0
    await hydrateQuestionFeedCounts(batch.map((item) => item.id), requestSeq)
  } catch {
    if (requestSeq === questionFeedReloadSeq.value) {
      backendStatus.value = '问题社区加载失败：请检查后端问题搜索接口'
      questionFeedHasMore.value = false
    }
  } finally {
    questionFeedLoading.value = false
    if (questionFeedReloadPending) {
      questionFeedReloadPending = false
      void loadQuestionFeedNextPage()
    }
  }
}

async function createEvent(): Promise<void> {
  try {
    const title = draftEvent.title.trim()
    const theater = draftEvent.theater.trim()
    const summary = draftEvent.summary.trim()
    const url = draftEvent.url.trim()
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
        url: url || null,
        theater,
        summary,
        tags: [],
        severity: draftEvent.severity,
        filterStatus: 'mock_new',
        timestamp: new Date().toISOString(),
      }
      homeEvents.value.unshift(newItem)
      if (currentView.value === 'events') {
        requestManageEventsReload()
      }
      selectedEventId.value = localId
      homeEventTotal.value += 1
      backendStatus.value = '后端离线：已在模拟数据中新增事件'
    } else {
      await sendJson<{ id: string }>('/events', 'POST', {
        event_key: codename,
        title,
        content: summary,
        url: url || null,
        source_system: theater,
        credibility_level: credibilityFromSeverity(draftEvent.severity),
        event_time: new Date().toISOString(),
        trace_id: makeTraceId(),
      })
      await fetchHomeEvents()
      requestManageEventsReload()
      backendStatus.value = '事件新增成功（后端）'
    }

    draftEvent.title = ''
    draftEvent.theater = ''
    draftEvent.summary = ''
    draftEvent.url = ''
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
      if (currentView.value === 'events') {
        requestManageEventsReload()
      }
      return
    }

    await sendJson('/events', 'DELETE', { ids: [currentId] })
    await fetchHomeEvents()
    requestManageEventsReload()
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
    const eventDomain = draftQuestion.eventDomain.trim()
    const eventType = draftQuestion.eventType.trim()
    const area = draftQuestion.area.trim()
    const inputType = draftQuestion.inputType.trim()
    const background = draftQuestion.background.trim()
    const matchScoreText = draftQuestion.matchScore.trim()
    const matchScore = matchScoreText ? Number(matchScoreText) : null
    if (!title || !deadline) {
      backendStatus.value = '问题新增失败：请填写标题与截止时间'
      return
    }
    if (matchScoreText && !Number.isFinite(matchScore)) {
      backendStatus.value = '问题新增失败：匹配分数格式无效'
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
        matchScore,
        eventDomain,
        eventType,
        area,
        inputType,
        background,
        answerSpace,
        hypothesis: '由人工创建，待补充假设。',
        deadline: normalizedDeadline,
        status: draftQuestion.status,
        groundTruth: '待真实结果回填。',
        deleteReason: '',
        deletedAt: '',
      })
      selectedQuestionId.value = localId
      backendStatus.value = '后端离线：已在模拟数据中新增问题'
      if (currentView.value === 'questions') {
        requestManageQuestionsReload()
      }
      draftQuestion.title = ''
      draftQuestion.matchScore = ''
      draftQuestion.eventDomain = ''
      draftQuestion.eventType = ''
      draftQuestion.area = ''
      draftQuestion.inputType = ''
      draftQuestion.background = ''
      draftQuestion.answerSpace = ''
      return
    }

    await sendJson<{ id: string }>('/questions', 'POST', {
      event_ids: eventIds,
      level: levelToNumber(draftQuestion.level),
      content: title,
      match_score: matchScore,
      event_domain: eventDomain || null,
      event_type: eventType || null,
      area: area || null,
      input_type: inputType || null,
      background: background || null,
      answer_space: answerSpace || null,
      deadline: normalizedDeadline,
      trace_id: makeTraceId(),
    })
    await hydrateFromBackend()
    requestManageQuestionsReload()
    backendStatus.value = '问题新增成功（后端）'
    draftQuestion.title = ''
    draftQuestion.matchScore = ''
    draftQuestion.eventDomain = ''
    draftQuestion.eventType = ''
    draftQuestion.area = ''
    draftQuestion.inputType = ''
    draftQuestion.background = ''
    draftQuestion.answerSpace = ''
  } catch {
    backendStatus.value = '问题新增失败：请检查后端接口或参数格式'
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

function loadViewData(view: AppView): void {
  if (view === 'events') {
    requestManageEventsReload()
  }
  if (view === 'questions') {
    requestManageQuestionsReload()
  }
  if (view === 'questionStream') {
    requestQuestionFeedReload()
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
  if (view === 'apiKeys') {
    if (backendOnline.value) {
      void fetchApiKeys(1)
    } else {
      apiKeyList.value = []
      apiKeyManageTotal.value = 0
      apiKeyManagePage.value = 1
      apiKeyManageJumpPage.value = '1'
    }
  }
  if (view === 'modelEndpoints') {
    if (backendOnline.value) {
      void fetchModelEndpoints(1)
    } else {
      modelEndpointList.value = []
      modelEndpointManageTotal.value = 0
      modelEndpointManagePage.value = 1
      modelEndpointManageJumpPage.value = '1'
    }
  }
}

watch(
  () => manageDetailQuestion.value?.id,
  (questionId) => {
    if (!questionId) {
      predictionForm.predictionContent = ''
      predictionForm.selectedAnswerId = ''
      predictionForm.confidence = ''
      predictionForm.reasoning = ''
      commentDraft.value = ''
      return
    }
    applyPredictionFormFromMine(questionId)
  },
)

watch(myCurrentPrediction, (mine) => {
  const options = currentQuestionAnswerOptions.value
  if (!mine) {
    predictionForm.selectedAnswerId = ''
    return
  }
  predictionForm.predictionContent = mine.predictionContent
  predictionForm.selectedAnswerId = matchPredictionToAnswerOptionId(mine.predictionContent, options)
  predictionForm.confidence = mine.confidence !== null && mine.confidence !== undefined ? String(mine.confidence) : ''
  predictionForm.reasoning = mine.reasoning ?? ''
})

watch(currentQuestionAnswerOptions, (options) => {
  if (options.length === 0) {
    predictionForm.selectedAnswerId = ''
    return
  }
  if (options.some((item) => item.id === predictionForm.selectedAnswerId)) {
    return
  }
  predictionForm.selectedAnswerId = matchPredictionToAnswerOptionId(predictionForm.predictionContent, options)
})

watch(questionDetailDialogOpen, (open) => {
  if (open) {
    return
  }
  questionComposerMode.value = null
  predictionPanelCollapsed.value = false
  commentPanelCollapsed.value = false
  cancelCommentEdit()
})

watch(activeTheme, (theme) => {
  applyTheme(theme)
})

onMounted(() => {
  const savedTheme = localStorage.getItem('moppa_theme') ?? ''
  if (isThemeId(savedTheme)) {
    activeTheme.value = savedTheme
  }
  applyTheme(activeTheme.value)
  void (async () => {
    await bootstrapAuthSession()
    if (isAuthenticated.value) {
      await hydrateFromBackend()
      await fetchSourceSystemOptions()
      if (!isAdmin.value && currentView.value !== 'home' && currentView.value !== 'questionStream') {
        currentView.value = 'home'
      } else {
        loadViewData(currentView.value)
      }
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
  stopTaskDetailAutoRefresh()
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

  localStorage.setItem(APP_VIEW_STORAGE_KEY, view)
  loadViewData(view)
})

watch(taskDetailDialogOpen, (open) => {
  if (!open) {
    stopTaskDetailAutoRefresh()
    return
  }
  scheduleTaskDetailAutoRefresh()
})

watch(
  () => selectedTaskDetail.value?.status,
  () => {
    scheduleTaskDetailAutoRefresh()
  },
)

watch(eventManageSearchKeyword, () => {
  selectedManageEventIds.value = []
  if (currentView.value !== 'events') {
    return
  }
  if (eventManageSearchTimer !== undefined) {
    window.clearTimeout(eventManageSearchTimer)
  }
  eventManageSearchTimer = window.setTimeout(() => {
    requestManageEventsReload()
  }, 250)
})

watch(eventManageFilterStatus, () => {
  selectedManageEventIds.value = []
  if (currentView.value !== 'events') {
    return
  }
  requestManageEventsReload()
})

watch(eventManageSourceSystem, () => {
  selectedManageEventIds.value = []
  if (currentView.value !== 'events') {
    return
  }
  requestManageEventsReload()
})

watch([eventManageTimeFrom, eventManageTimeTo], () => {
  selectedManageEventIds.value = []
  if (currentView.value !== 'events') {
    return
  }
  requestManageEventsReload()
})

watch(questionManageSearchKeyword, () => {
  selectedManageQuestionIds.value = []
  if (currentView.value !== 'questions') {
    return
  }
  if (questionManageSearchTimer !== undefined) {
    window.clearTimeout(questionManageSearchTimer)
  }
  questionManageSearchTimer = window.setTimeout(() => {
    requestManageQuestionsReload()
  }, 250)
})

watch(
  [
    questionManageFilterEventDomain,
    questionManageFilterEventType,
    questionManageFilterDeadlineFrom,
    questionManageFilterDeadlineTo,
    questionManageFilterStatus,
    questionManageFilterLevel,
    questionManageDeletedMode,
  ],
  () => {
    selectedManageQuestionIds.value = []
    if (currentView.value !== 'questions') {
      return
    }
    requestManageQuestionsReload()
  },
)

watch(questionFeedSearchKeyword, () => {
  if (questionFeedFilterResetting) {
    return
  }
  if (!backendOnline.value || currentView.value !== 'questionStream') {
    return
  }
  if (questionFeedSearchTimer !== undefined) {
    window.clearTimeout(questionFeedSearchTimer)
  }
  questionFeedSearchTimer = window.setTimeout(() => {
    requestQuestionFeedReload()
  }, 250)
})

watch(
  [
    questionFeedFilterEventDomain,
    questionFeedFilterEventType,
    questionFeedFilterDeadlineFrom,
    questionFeedFilterDeadlineTo,
    questionFeedFilterStatus,
    questionFeedFilterLevel,
  ],
  () => {
    if (questionFeedFilterResetting) {
      return
    }
    if (!backendOnline.value || currentView.value !== 'questionStream') {
      return
    }
    requestQuestionFeedReload()
  },
)

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
    void fetchQuestionEventOptions(keyword, 'create')
  }, 250)
})

watch(questionEditEventSearch, (keyword) => {
  if (!questionEditDialogOpen.value || !backendOnline.value) {
    return
  }
  if (questionEventSearchTimer !== undefined) {
    window.clearTimeout(questionEventSearchTimer)
  }
  questionEventSearchTimer = window.setTimeout(() => {
    void fetchQuestionEventOptions(keyword, 'edit')
  }, 250)
})

watch(questionEditDialogOpen, (open) => {
  if (open) {
    return
  }
  if (questionEventSearchTimer !== undefined) {
    window.clearTimeout(questionEventSearchTimer)
    questionEventSearchTimer = undefined
  }
  questionEditEventSearch.value = ''
  if (!createQuestionDialogOpen.value) {
    resetQuestionEventSearchState()
  }
})

watch(backendOnline, (online) => {
  scheduleTopMetricRefresh(0)
  if (!isAuthenticated.value) {
    return
  }
  if (currentView.value === 'events') {
    requestManageEventsReload()
  }
  if (currentView.value === 'questions') {
    requestManageQuestionsReload()
  }
  if (currentView.value === 'questionStream') {
    requestQuestionFeedReload()
  }
  if (online && currentView.value === 'templates') {
    void fetchTemplates(1)
  }
  if (online && createQuestionDialogOpen.value) {
    void fetchQuestionEventOptions(questionEventSearch.value, 'create')
  }
  if (online && questionEditDialogOpen.value) {
    void fetchQuestionEventOptions(questionEditEventSearch.value, 'edit')
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
      :active-theme="activeTheme"
      :theme-options="themeOptions"
      @open-auth="authDialogOpen = true"
      @logout="logout"
      @update-theme="updateTheme"
    />

    <div class="workspace-shell">
      <SidebarNav :current-view="currentView" :is-admin="isAdmin" @update:view="currentView = $event" />

      <div class="workspace-main">
        <main v-if="currentView === 'home'" class="home-stack">
          <HomeOverviewMap :backend-online="backendOnline" />

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
      :items="manageEvents"
      :all-loaded-events-selected="allLoadedEventsSelected"
      :event-review-processing="eventReviewProcessing"
      :event-manage-search-keyword="eventManageSearchKeyword"
      :event-manage-source-system="eventManageSourceSystem"
      :event-manage-filter-status="eventManageFilterStatus"
      :event-manage-time-from="eventManageTimeFrom"
      :event-manage-time-to="eventManageTimeTo"
      :loading="eventManageSearchLoading"
      :backend-online="backendOnline"
      :matching-total="manageEventMatchingTotal"
      :loaded-count="manageEvents.length"
      :has-more="eventManageHasMore"
      :skeleton-rows="skeletonRows"
      :selected-event-id="selectedEventId"
      :selected-manage-event-ids="selectedManageEventIds"
      :source-system-options="sourceSystemOptions"
      @open-create-event="createEventDialogOpen = true; void fetchSourceSystemOptions()"
      @toggle-select-all="toggleSelectAllEventsOnPage"
      @review-events="reviewSelectedEvents"
      @delete-selected-batch="deleteSelectedEventsBatch"
      @update:search-keyword="eventManageSearchKeyword = $event"
      @update:source-system="eventManageSourceSystem = $event"
      @update:filter-status="eventManageFilterStatus = $event"
      @update:time-from="eventManageTimeFrom = $event"
      @update:time-to="eventManageTimeTo = $event"
      @select-event="selectEvent"
      @open-manage-detail="openManageDetail"
      @toggle-selection="toggleManageEventSelection"
      @open-edit="openEventEdit"
      @load-more="loadManageEventsNextPage"
    />

    <ManageQuestionsPanel
      v-if="currentView === 'questions'"
      :all-loaded-manage-questions-selected="allLoadedQuestionsSelected"
      :question-manage-search-keyword="questionManageSearchKeyword"
      :question-manage-filter-event-domain="questionManageFilterEventDomain"
      :question-manage-filter-event-type="questionManageFilterEventType"
      :question-manage-filter-deadline-from="questionManageFilterDeadlineFrom"
      :question-manage-filter-deadline-to="questionManageFilterDeadlineTo"
      :question-manage-filter-status="questionManageFilterStatus"
      :question-manage-filter-level="questionManageFilterLevel"
      :question-manage-deleted-mode="questionManageDeletedMode"
      :question-manage-filters-applied="questionManageFiltersApplied"
      :question-manage-loading="questionManageSearchLoading"
      :backend-online="backendOnline"
      :question-manage-total="questionManageTotal"
      :skeleton-rows="skeletonRows"
      :loaded-manage-questions="manageQuestions"
      :selected-question-id="selectedQuestionId"
      :selected-manage-question-ids="selectedManageQuestionIds"
      :question-manage-has-more="questionManageHasMore"
      :all-known-events="allKnownEvents"
      @open-create-question="openCreateQuestionDialog"
      @toggle-select-all="toggleSelectAllQuestionsOnPage"
      @delete-selected-batch="deleteSelectedQuestionsBatch"
      @update:search-keyword="questionManageSearchKeyword = $event"
      @update:filter-event-domain="questionManageFilterEventDomain = $event"
      @update:filter-event-type="questionManageFilterEventType = $event"
      @update:filter-deadline-from="questionManageFilterDeadlineFrom = $event"
      @update:filter-deadline-to="questionManageFilterDeadlineTo = $event"
      @update:filter-status="questionManageFilterStatus = $event"
      @update:filter-level="questionManageFilterLevel = $event"
      @update:deleted-mode="questionManageDeletedMode = $event"
      @clear-filters="resetQuestionManageFilters"
      @select-question="selectedQuestionId = $event"
      @open-manage-detail="openManageQuestionDetail"
      @toggle-selection="toggleManageQuestionSelection"
      @open-edit="openQuestionEdit"
      @load-more="loadManageQuestionsNextPage"
    />

    <QuestionFeedPanel
      v-if="currentView === 'questionStream'"
      :items="filteredQuestionFeedItems"
      :interaction-counts="questionFeedInteractionCounts"
      :participation="questionFeedParticipation"
      :loading="questionFeedLoading"
      :has-more="questionFeedHasMore"
      :backend-online="backendOnline"
      :all-known-events="allKnownEvents"
      :search-keyword="questionFeedSearchKeyword"
      :filter-event-domain="questionFeedFilterEventDomain"
      :filter-event-type="questionFeedFilterEventType"
      :filter-deadline-from="questionFeedFilterDeadlineFrom"
      :filter-deadline-to="questionFeedFilterDeadlineTo"
      :filter-status="questionFeedFilterStatus"
      :filter-level="questionFeedFilterLevel"
      :loaded-count="questionFeedItems.length"
      :filtered-count="filteredQuestionFeedItems.length"
      :filters-applied="questionFeedFiltersApplied"
      @load-more="loadQuestionFeedNextPage"
      @open-question="openManageQuestionDetail"
      @update:search-keyword="questionFeedSearchKeyword = $event"
      @update:filter-event-domain="questionFeedFilterEventDomain = $event"
      @update:filter-event-type="questionFeedFilterEventType = $event"
      @update:filter-deadline-from="questionFeedFilterDeadlineFrom = $event"
      @update:filter-deadline-to="questionFeedFilterDeadlineTo = $event"
      @update:filter-status="questionFeedFilterStatus = $event"
      @update:filter-level="questionFeedFilterLevel = $event"
      @clear-filters="resetQuestionFeedFilters"
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
      :template-manage-page-size-options="eventManagePageSizeOptions"
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
      :tavily-ingest-processing="tavilyIngestProcessing"
      :auto-review-processing="autoReviewProcessing"
      :auto-question-processing="autoQuestionProcessing"
      :location-analysis-processing="locationAnalysisProcessing"
      :expiry-processing="expiryProcessing"
      :all-tasks-on-page-selected="allTasksOnPageSelected"
      :has-tasks="hasTasks"
      :tasks="tasks"
      :selected-task-id="selectedTask?.id ?? ''"
      :selected-manage-task-ids="selectedManageTaskIds"
      :task-manage-page-size="taskManagePageSize"
      :task-manage-page-size-options="eventManagePageSizeOptions"
      :task-manage-jump-page="taskManageJumpPage"
      @open-trigger-pull="triggerPullDialogOpen = true; void fetchSourceSystemOptions()"
      @trigger-tavily-ingest="triggerTavilyIngestNow"
      @trigger-auto-review="triggerAutoReviewNow"
      @trigger-auto-question="triggerAutoQuestionNow"
      @trigger-location-analysis="triggerLocationAnalysisNow"
      @trigger-expiry-check="triggerExpiryCheckNow"
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

    <main v-if="currentView === 'apiKeys'" class="manage-grid">
      <article class="panel list-panel">
        <div class="panel-head">
          <h2>身份认证 - API Key 管理</h2>
        </div>
        <div class="action-row manage-toolbar">
          <button class="action-btn" @click="openApiKeyCreateDialog">新增 API Key</button>
        </div>
        <div v-if="apiKeyList.length === 0" class="empty-state">暂无 API Key</div>
        <ul v-else class="event-list">
          <li v-for="item in apiKeyList" :key="item.id" class="question-card">
            <div class="row-between">
              <strong>{{ item.name }}</strong>
              <div class="tag-group">
                <span class="badge">{{ item.user_type }}</span>
                <span v-if="item.purpose" class="badge">{{ item.purpose }}</span>
                <span :class="['badge', item.is_active ? 'badge-success' : 'badge-error']">{{ item.is_active ? '启用' : '禁用' }}</span>
              </div>
            </div>
            <p class="item-meta" style="word-break:break-all"><strong>Token：</strong>{{ item.token }}</p>
            <small class="item-subtle">
              创建时间：{{ item.created_at }} | 最后使用：{{ item.last_used_at ?? '从未使用' }}
            </small>
            <div class="action-row" style="margin-top:0.5rem">
              <button class="action-btn" @click="openApiKeyEditDialog(item)">编辑</button>
              <button class="action-btn" @click="toggleApiKeyActive(item)">{{ item.is_active ? '禁用' : '启用' }}</button>
              <button class="action-btn danger" @click="deleteApiKey(item.id)">删除</button>
            </div>
          </li>
        </ul>
        <div class="action-row pagination-row pagination-center">
          <span>每页</span>
          <select :value="apiKeyManagePageSize" @change="setApiKeyManagePageSize(Number(($event.target as HTMLSelectElement).value))">
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
          </select>
          <button class="action-btn" @click="goApiKeyPage(-1)">上一页</button>
          <input :value="apiKeyManageJumpPage" class="jump-input" placeholder="页码" @input="apiKeyManageJumpPage = ($event.target as HTMLInputElement).value" />
          <button class="action-btn" @click="jumpToApiKeyPage">跳转</button>
          <button class="action-btn" @click="goApiKeyPage(1)">下一页</button>
        </div>
      </article>
    </main>

    <main v-if="currentView === 'modelEndpoints'" class="manage-grid">
      <article class="panel list-panel">
        <div class="panel-head">
          <h2>模型配置</h2>
        </div>
        <div class="action-row manage-toolbar">
          <button class="action-btn" @click="openModelEndpointCreateDialog()">新增模型端点</button>
        </div>
        <div v-if="modelEndpointList.length === 0" class="empty-state">暂无模型端点</div>
        <ul v-else class="event-list">
          <li v-for="item in modelEndpointList" :key="item.id" class="question-card">
            <div class="row-between">
              <strong>{{ item.name }}</strong>
              <div class="tag-group">
                <span class="badge">{{ item.provider }}</span>
                <span :class="['badge', item.is_available ? 'badge-success' : 'badge-error']">{{ item.is_available ? '可用' : '不可用' }}</span>
                <span :class="['badge', item.status === 'active' ? 'badge-success' : item.status === 'inactive' ? 'badge-warning' : 'badge-muted']">{{ item.status }}</span>
              </div>
            </div>
            <p class="item-meta">标识符：{{ item.identifier }}</p>
            <p class="item-meta">模型：{{ item.model_name }} ({{ item.model_version }})</p>
            <p class="item-subtle">地址：{{ item.endpoint_url }}</p>
            <small class="item-subtle">max_tokens={{ item.max_tokens }} | temperature={{ item.temperature }} | timeout={{ item.timeout_seconds }}s</small>
            <div class="action-row" style="margin-top:0.5rem">
              <button class="action-btn" @click="openModelEndpointEditDialog(item)">编辑</button>
              <button class="action-btn danger" @click="deleteModelEndpoints([item.id])">删除</button>
            </div>
          </li>
        </ul>
        <div class="action-row pagination-row pagination-center">
          <span>每页</span>
          <select :value="modelEndpointManagePageSize" @change="setModelEndpointPageSize(Number(($event.target as HTMLSelectElement).value))">
            <option value="10">10</option>
            <option value="20">20</option>
            <option value="50">50</option>
          </select>
          <button class="action-btn" @click="goModelEndpointPage(-1)">上一页</button>
          <input :value="modelEndpointManageJumpPage" class="jump-input" placeholder="页码" @input="modelEndpointManageJumpPage = ($event.target as HTMLInputElement).value" />
          <button class="action-btn" @click="jumpToModelEndpointPage">跳转</button>
          <button class="action-btn" @click="goModelEndpointPage(1)">下一页</button>
        </div>
      </article>
    </main>
      </div>

    </div>

    <div v-if="taskDetailDialogOpen && selectedTaskDetail" class="dialog-backdrop" @click.self="taskDetailDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>任务执行详情</h2>
          <div class="action-row">
            <button class="action-btn" :disabled="taskDetailRefreshing" @click="refreshCurrentTaskDetail">
              {{ taskDetailRefreshing ? '刷新中...' : '刷新详情' }}
            </button>
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
          <p><strong>已处理批次：</strong>{{ getTaskResultNumber('processed_batches') ?? '-' }}</p>
          <p><strong>已处理事件：</strong>{{ getTaskResultNumber('processed_events') ?? '-' }}</p>
          <p><strong>已生成问题：</strong>{{ getTaskResultNumber('generated_questions') ?? '-' }}</p>
          <p><strong>已保存问题：</strong>{{ getTaskResultNumber('saved_questions') ?? '-' }}</p>
          <p><strong>结果：</strong>{{ JSON.stringify(selectedTaskDetail.result) }}</p>
          <p><strong>指标：</strong>{{ JSON.stringify(selectedTaskDetail.metrics) }}</p>
          <p><strong>批次日志：</strong>{{ JSON.stringify(getTaskBatchLogs()) }}</p>
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
      <section class="dialog-panel event-detail-dialog">
        <div class="panel-head panel-head-split">
          <h2>事件详情</h2>
          <button class="action-btn" @click="homeDetailDialogOpen = false">关闭</button>
        </div>
        <article class="detail-block event-story-card">
          <p class="event-story-kicker">{{ homeDetailEvent.theater }}</p>
          <h3>{{ homeDetailEvent.title }}</h3>
          <p>{{ homeDetailEvent.summary }}</p>
          <div class="action-row event-story-metrics">
            <span :class="['badge', 'badge-core', severityBadgeTone(homeDetailEvent.severity)]">可信等级：{{ severityLabel[homeDetailEvent.severity] }}</span>
            <span :class="['badge', 'badge-core', eventFilterBadgeTone(homeDetailEvent.filterStatus)]">{{ homeDetailEvent.filterStatus }}</span>
            <span class="badge badge-normal">事件时间：{{ formatDate(homeDetailEvent.timestamp) }}</span>
            <span class="badge badge-subtle">ID：{{ homeDetailEvent.id }}</span>
            <span class="badge badge-subtle">event_key：{{ homeDetailEvent.codename }}</span>
          </div>
          <a v-if="homeDetailEvent.url" class="event-story-link" :href="homeDetailEvent.url" target="_blank" rel="noopener noreferrer">
            查看原始链接
          </a>
        </article>
        <section class="detail-block detail-summary-block">
          <h3>话题标签</h3>
          <div class="tag-group detail-tags">
            <span v-if="homeDetailEvent.tags.length === 0" class="badge badge-muted">无 tags</span>
            <span v-for="tag in homeDetailEvent.tags" :key="`event-home-tag-${homeDetailEvent.id}-${tag}`" class="badge">{{ tag }}</span>
          </div>
        </section>
        <section class="detail-block detail-related-block">
          <h3>关联社区问题</h3>
          <div v-if="relatedQuestionsForEvent(homeDetailEvent.id).length > 0" class="event-related-question-list">
            <button
              v-for="item in relatedQuestionsForEvent(homeDetailEvent.id)"
              :key="`event-home-question-${homeDetailEvent.id}-${item.id}`"
              class="event-related-question-card"
              type="button"
              @click="homeDetailDialogOpen = false; openManageQuestionDetail(item)"
            >
              <strong>{{ item.title }}</strong>
              <span class="item-subtle">{{ item.level }} · {{ statusLabel[item.status] }} · 截止 {{ formatDate(item.deadline) }}</span>
            </button>
          </div>
          <p v-else class="item-subtle">暂无与此事件关联的问题</p>
        </section>
      </section>
    </div>

    <div
      v-if="eventDetailDialogOpen && manageDetailEvent"
      class="dialog-backdrop dialog-backdrop-stacked"
      @click.self="eventDetailDialogOpen = false"
    >
      <section class="dialog-panel event-detail-dialog">
        <div class="panel-head panel-head-split">
          <h2>事件详情</h2>
          <div class="action-row">
            <button v-if="isAdmin" class="action-btn" @click="openEventEdit(manageDetailEvent)">编辑</button>
            <button class="action-btn" @click="eventDetailDialogOpen = false">关闭</button>
          </div>
        </div>
        <article class="detail-block event-story-card">
          <p class="event-story-kicker">{{ manageDetailEvent.theater }}</p>
          <h3>{{ manageDetailEvent.title }}</h3>
          <p>{{ manageDetailEvent.summary }}</p>
          <div class="action-row event-story-metrics">
            <span :class="['badge', 'badge-core', severityBadgeTone(manageDetailEvent.severity)]">可信等级：{{ severityLabel[manageDetailEvent.severity] }}</span>
            <span :class="['badge', 'badge-core', eventFilterBadgeTone(manageDetailEvent.filterStatus)]">{{ manageDetailEvent.filterStatus }}</span>
            <span class="badge badge-normal">事件时间：{{ formatDate(manageDetailEvent.timestamp) }}</span>
            <span class="badge badge-subtle">ID：{{ manageDetailEvent.id }}</span>
            <span class="badge badge-subtle">event_key：{{ manageDetailEvent.codename }}</span>
          </div>
          <a v-if="manageDetailEvent.url" class="event-story-link" :href="manageDetailEvent.url" target="_blank" rel="noopener noreferrer">
            查看原始链接
          </a>
        </article>
        <section class="detail-block detail-summary-block">
          <h3>话题标签</h3>
          <div class="tag-group detail-tags">
            <span v-if="manageDetailEvent.tags.length === 0" class="badge badge-muted">无 tags</span>
            <span v-for="tag in manageDetailEvent.tags" :key="`event-manage-tag-${manageDetailEvent.id}-${tag}`" class="badge">{{ tag }}</span>
          </div>
        </section>
        <section class="detail-block detail-related-block">
          <h3>关联社区问题</h3>
          <div v-if="relatedQuestionsForEvent(manageDetailEvent.id).length > 0" class="event-related-question-list">
            <button
              v-for="item in relatedQuestionsForEvent(manageDetailEvent.id)"
              :key="`event-manage-question-${manageDetailEvent.id}-${item.id}`"
              class="event-related-question-card"
              type="button"
              @click="eventDetailDialogOpen = false; openManageQuestionDetail(item)"
            >
              <strong>{{ item.title }}</strong>
              <span class="item-subtle">{{ item.level }} · {{ statusLabel[item.status] }} · 截止 {{ formatDate(item.deadline) }}</span>
            </button>
          </div>
          <p v-else class="item-subtle">暂无与此事件关联的问题</p>
        </section>
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
              v-if="eventEditForm.filterStatus && !['pending', 'passed', 'matched', 'filtered'].includes(eventEditForm.filterStatus)"
              :value="eventEditForm.filterStatus"
            >
              {{ eventEditForm.filterStatus }}
            </option>
            <option value="pending">pending</option>
            <option value="passed">passed</option>
            <option value="matched">matched</option>
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
      <section class="dialog-panel question-detail-dialog">
        <div class="panel-head panel-head-split">
          <h2>问题社区 · 详情</h2>
          <div class="action-row">
            <button
              v-if="isAdmin"
              class="action-btn"
              @click="openQuestionEdit(manageDetailQuestion!)"
            >
              编辑
            </button>
            <button class="action-btn" @click="questionDetailDialogOpen = false">关闭</button>
          </div>
        </div>
        <article class="detail-block question-story-card">
          <div class="stream-head question-story-head">
            <div class="stream-avatar">Q</div>
            <div>
              <strong>MOPPA Question Desk</strong>
              <p class="item-subtle">发布于 {{ manageDetailQuestion.createdAt ? formatDate(manageDetailQuestion.createdAt) : '-' }}</p>
            </div>
          </div>
          <h3>{{ manageDetailQuestion.title }}</h3>
          <p v-if="manageDetailQuestion.background" class="question-story-summary">{{ manageDetailQuestion.background }}</p>
          <div class="action-row question-story-tags">
            <span class="badge badge-core">{{ manageDetailQuestion.level }}</span>
            <span :class="['badge', 'badge-core', statusTone(manageDetailQuestion.status)]">{{ statusLabel[manageDetailQuestion.status] }}</span>
            <span class="badge badge-core">截止：{{ formatDate(manageDetailQuestion.deadline) }}</span>
            <span v-if="manageDetailQuestion.eventDomain" class="badge badge-normal">事件域：{{ manageDetailQuestion.eventDomain }}</span>
            <span v-if="manageDetailQuestion.eventType" class="badge badge-normal">事件类型：{{ manageDetailQuestion.eventType }}</span>
            <span v-if="manageDetailQuestion.area" class="badge badge-normal">区域：{{ manageDetailQuestion.area }}</span>
            <span v-if="manageDetailQuestion.inputType" class="badge badge-normal">输入类型：{{ manageDetailQuestion.inputType }}</span>
            <span class="badge badge-subtle">ID：{{ manageDetailQuestion.id }}</span>
            <span v-if="manageDetailQuestion.matchScore !== null" class="badge badge-subtle">匹配分：{{ manageDetailQuestion.matchScore }}</span>
            <span v-if="manageDetailQuestion.deletedAt" class="badge badge-subtle">删除时间：{{ formatDate(manageDetailQuestion.deletedAt) }}</span>
          </div>
          <div v-if="manageDetailQuestion.eventIds.length > 0" class="question-story-events">
            <div class="tag-group">
              <button
                v-for="eventId in manageDetailQuestion.eventIds"
                :key="`detail-event-${manageDetailQuestion.id}-${eventId}`"
                type="button"
                class="action-btn mini-btn linked-event-chip"
                @click="void openQuestionLinkedEventDetail(eventId)"
              >
                {{ linkedEventDisplayLabel(eventId) }}
              </button>
            </div>
          </div>
        </article>
        <section class="detail-block question-answer-block">
          <h3>候选答案（投票项）</h3>
          <p v-if="currentQuestionAnswerOptions.length === 0" class="item-subtle">未解析到结构化选项，当前问题允许自由文本预测。</p>
          <div v-else class="question-answer-list">
            <button
              v-for="option in currentQuestionAnswerOptions"
              :key="`question-answer-${manageDetailQuestion.id}-${option.id}`"
              :class="['question-answer-item', { 'my-prediction': mySelectedAnswerOption?.id === option.id }]"
              type="button"
              :disabled="!canCurrentQuestionInteract || predictionSubmitting"
              @click="void handleAnswerOptionClick(option.id)"
            >
              <span class="question-answer-key">{{ option.key }}</span>
              <span class="question-answer-label">{{ option.label }}</span>
              <span v-if="answerOptionPercentages.has(option.id)" class="question-answer-percentage">
                {{ answerOptionPercentages.get(option.id) }}
              </span>
              <span v-if="mySelectedAnswerOption?.id === option.id" class="question-answer-badge">
                我的预测
              </span>
            </button>
          </div>
        </section>
        <section class="detail-block detail-summary-block" v-if="manageDetailQuestion.hypothesis">
          <h3>假设</h3>
          <p>{{ manageDetailQuestion.hypothesis }}</p>
        </section>
        <section class="detail-block detail-summary-block" v-if="manageDetailQuestion.groundTruth">
          <h3>真实结果</h3>
          <p>{{ manageDetailQuestion.groundTruth }}</p>
        </section>
        <section class="detail-block detail-summary-block" v-if="manageDetailQuestion.deleteReason">
          <h3>删除原因</h3>
          <p>{{ manageDetailQuestion.deleteReason }}</p>
        </section>

        <div class="field-block">
          <label>社区互动</label>
          <small>
            {{ canCurrentQuestionInteract ? '当前可互动：问题收集中且未到截止时间' : '当前不可互动：仅收集中且截止前允许预测和评论' }}
          </small>
          <div class="action-row question-actions-strip">
            <span class="chip">预测 {{ activeQuestionPredictions.length }}</span>
            <span class="chip">评论 {{ activeQuestionComments.length }}</span>
            <button
              class="action-btn"
              :disabled="!canCurrentQuestionInteract || questionInteractionLoading"
              @click="openQuestionComposer('prediction')"
            >
              {{ myCurrentPrediction ? '编辑我的预测' : '发布预测' }}
            </button>
            <button
              class="action-btn"
              :disabled="!canCurrentQuestionInteract || questionInteractionLoading"
              @click="openQuestionComposer('comment')"
            >
              写评论
            </button>
          </div>
          <div v-if="questionInteractionLoading" class="item-subtle">互动数据加载中...</div>
        </div>

        <div v-if="questionComposerMode === 'prediction'" class="detail-block composer-drawer">
          <h3>发布预测</h3>
          <div v-if="currentQuestionAnswerOptions.length > 0" class="field-block">
            <label>从候选答案中选择一个结果</label>
            <div class="prediction-option-list">
              <label
                v-for="option in currentQuestionAnswerOptions"
                :key="`prediction-option-${manageDetailQuestion.id}-${option.id}`"
                class="prediction-option"
              >
                <input
                  v-model="predictionForm.selectedAnswerId"
                  type="radio"
                  name="prediction-option"
                  :value="option.id"
                  :disabled="!canCurrentQuestionInteract || predictionSubmitting"
                />
                <span class="prediction-option-key">{{ option.key }}</span>
                <span>{{ option.label }}</span>
              </label>
            </div>
            <small v-if="selectedAnswerOption" class="item-subtle">当前选择：{{ selectedAnswerOption.label }}</small>
          </div>
          <div v-else class="field-block">
            <label>我的预测内容</label>
            <textarea
              v-model="predictionForm.predictionContent"
              rows="3"
              :disabled="!canCurrentQuestionInteract || predictionSubmitting"
              placeholder="输入你对该问题的预测"
            ></textarea>
          </div>
          <div class="dialog-inline-grid">
            <div class="field-block">
              <label>置信度（0-100，可空）</label>
              <input
                v-model="predictionForm.confidence"
                type="number"
                min="0"
                max="100"
                step="0.01"
                :disabled="!canCurrentQuestionInteract || predictionSubmitting"
              />
            </div>
            <div class="field-block">
              <label>预测依据（可空）</label>
              <input
                v-model="predictionForm.reasoning"
                :disabled="!canCurrentQuestionInteract || predictionSubmitting"
                placeholder="可填写简短理由"
              />
            </div>
          </div>
          <div class="action-row action-right">
            <button class="action-btn" @click="questionComposerMode = null">取消</button>
            <button
              class="action-btn"
              :disabled="!canCurrentQuestionInteract || predictionSubmitting"
              @click="submitMyPrediction"
            >
              {{ predictionSubmitting ? '提交中...' : '保存我的预测' }}
            </button>
          </div>
        </div>

        <div v-if="questionComposerMode === 'comment'" class="detail-block composer-drawer">
          <h3>发布评论</h3>
          <textarea
            v-model="commentDraft"
            rows="2"
            :disabled="!canCurrentQuestionInteract || commentSubmitting"
            placeholder="输入评论内容"
          ></textarea>
          <div class="action-row action-right">
            <button class="action-btn" @click="questionComposerMode = null">取消</button>
            <button
              class="action-btn"
              :disabled="!canCurrentQuestionInteract || commentSubmitting"
              @click="submitQuestionComment"
            >
              {{ commentSubmitting ? '发布中...' : '发布评论' }}
            </button>
          </div>
        </div>

        <div class="discussion-stack">
          <section class="subpanel">
            <div class="discussion-panel-head">
              <h3>社区预测</h3>
              <button class="action-btn mini-btn" @click="predictionPanelCollapsed = !predictionPanelCollapsed">
                {{ predictionPanelCollapsed ? '展开' : '折叠' }}
              </button>
            </div>
            <p v-if="predictionPanelCollapsed" class="item-subtle">预测区已折叠</p>
            <p v-else-if="activeQuestionPredictions.length === 0" class="item-subtle">暂无社区预测</p>
            <div v-else class="community-card-list">
              <article v-for="item in activeQuestionPredictions" :key="`prediction-${item.id}`" class="community-item-card">
                <div class="community-item-head">
                  <strong>{{ item.username }}</strong>
                  <span class="item-subtle">{{ formatDate(item.createdAt) }}</span>
                </div>
                <p>
                  {{ item.predictionContent }}
                  <span v-if="item.userId === authUser?.id" class="badge badge-info">我的预测</span>
                </p>
                <div class="action-row">
                  <span v-if="item.confidence !== null" class="chip">置信度 {{ item.confidence }}</span>
                  <span v-if="item.reasoning" class="item-subtle">依据：{{ item.reasoning }}</span>
                </div>
              </article>
            </div>
          </section>
          <section class="subpanel">
            <div class="discussion-panel-head">
              <h3>模型预测</h3>
              <button class="action-btn mini-btn" @click="agentPredictionPanelCollapsed = !agentPredictionPanelCollapsed">
                {{ agentPredictionPanelCollapsed ? '展开' : '折叠' }}
              </button>
            </div>
            <p v-if="agentPredictionPanelCollapsed" class="item-subtle">模型预测区已折叠</p>
            <p v-else-if="activeQuestionAgentPredictions.length === 0" class="item-subtle">暂无模型预测</p>
            <div v-else class="community-card-list">
              <article v-for="item in activeQuestionAgentPredictions" :key="`agent-prediction-${item.id}`" class="community-item-card">
                <div class="community-item-head">
                  <strong>{{ item.agentName }}</strong>
                  <div class="tag-group">
                    <span class="badge">{{ item.modelName }}</span>
                    <span v-if="item.userType === 'agent'" class="badge badge-info">Agent</span>
                    <span v-else-if="item.userType === 'user'" class="badge">User</span>
                    <span v-else class="badge badge-muted">Other</span>
                    <span v-if="item.purpose" class="badge">{{ item.purpose }}</span>
                  </div>
                </div>
                <p>{{ item.predictionContent }}</p>
                <div class="action-row">
                  <span v-if="item.confidence !== null" class="chip">置信度 {{ item.confidence }}</span>
                  <span v-if="item.isCorrect === true" class="chip badge-success">✓ 正确</span>
                  <span v-else-if="item.isCorrect === false" class="chip badge-error">✗ 错误</span>
                  <span v-if="item.score !== null" class="chip">得分 {{ item.score }}</span>
                </div>
                <p v-if="item.reasoning" class="item-subtle">依据：{{ item.reasoning }}</p>
                <div v-if="item.evidence && item.evidence.length > 0" class="evidence-list">
                  <p class="item-subtle" style="margin-bottom:0.25rem">证据：</p>
                  <a v-for="(ev, idx) in item.evidence" :key="`ev-${idx}`" :href="ev.url" target="_blank" rel="noopener" class="evidence-link">
                    {{ ev.content || ev.url }}
                  </a>
                </div>
                <small class="item-subtle">{{ formatDate(item.createdAt) }}</small>
              </article>
            </div>
          </section>
          <section class="subpanel">
            <div class="discussion-panel-head">
              <h3>评论</h3>
              <button class="action-btn mini-btn" @click="commentPanelCollapsed = !commentPanelCollapsed">
                {{ commentPanelCollapsed ? '展开' : '折叠' }}
              </button>
            </div>
            <p v-if="commentPanelCollapsed" class="item-subtle">评论区已折叠</p>
            <p v-else-if="activeQuestionComments.length === 0" class="item-subtle">暂无评论</p>
            <div v-else class="community-card-list">
              <div v-for="comment in activeQuestionComments" :key="`comment-${comment.id}`" class="comment-item-row">
                <template v-if="editingCommentId === comment.id">
                  <textarea
                    v-model="editingCommentContent"
                    rows="2"
                    :disabled="commentActionLoading"
                    placeholder="修改评论内容"
                  ></textarea>
                  <div class="action-row action-right">
                    <button class="action-btn mini-btn" :disabled="commentActionLoading" @click="cancelCommentEdit">取消</button>
                    <button class="action-btn mini-btn" :disabled="commentActionLoading" @click="saveEditedComment">
                      {{ commentActionLoading ? '保存中...' : '保存' }}
                    </button>
                  </div>
                </template>
                <template v-else>
                  <div class="community-item-head">
                    <strong>{{ comment.username }}</strong>
                    <span class="item-subtle">{{ formatDate(comment.createdAt) }}</span>
                  </div>
                  <p>{{ comment.content }}</p>
                  <div class="action-row action-right">
                    <button
                      v-if="canEditComment(comment)"
                      class="action-btn mini-btn"
                      :disabled="commentActionLoading"
                      @click="beginCommentEdit(comment)"
                    >
                      编辑
                    </button>
                    <button
                      v-if="canDeleteComment(comment)"
                      class="action-btn mini-btn danger"
                      :disabled="commentActionLoading"
                      @click="deleteComment(comment)"
                    >
                      删除
                    </button>
                  </div>
                </template>
              </div>
            </div>
          </section>
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
          <div class="question-event-multi-select" @scroll.passive="handleQuestionEventSelectScroll('edit', $event)">
            <label v-for="eventItem in filteredKnownEventsForQuestionEdit" :key="`question-edit-target-${eventItem.id}`" class="select-row question-event-option">
              <input
                type="checkbox"
                :checked="questionEditForm.eventIds.includes(eventItem.id)"
                @change="toggleQuestionEditEventSelection(eventItem.id)"
              />
              <span>{{ eventItem.title }}（{{ eventItem.theater }}）</span>
            </label>
            <p v-if="questionEventSearchLoading" class="item-subtle">搜索中...</p>
            <p v-else-if="filteredKnownEventsForQuestionEdit.length === 0" class="item-subtle">无匹配事件</p>
            <p v-if="questionEventSearchLoadingMore" class="item-subtle">正在加载更多...</p>
            <p
              v-else-if="backendOnline && questionEventSearchMode === 'edit' && !questionEventSearchHasMore && filteredKnownEventsForQuestionEdit.length > 0"
              class="item-subtle"
            >
              已加载全部匹配事件
            </p>
          </div>
        </div>
        <div class="field-block">
          <label>问题等级</label>
          <select v-model="questionEditForm.level">
            <option v-for="level in levels" :key="`edit-question-${level}`" :value="level">{{ level }}</option>
          </select>
        </div>
        <div class="field-block">
          <label>匹配分数（可选）</label>
          <input v-model="questionEditForm.matchScore" type="number" step="0.0001" min="0" placeholder="例如 0.7074" />
        </div>
        <div class="field-block">
          <label>事件域（可选）</label>
          <input v-model="questionEditForm.eventDomain" placeholder="例如 外交" />
        </div>
        <div class="field-block">
          <label>事件类型（可选）</label>
          <input v-model="questionEditForm.eventType" placeholder="例如 外交对话" />
        </div>
        <div class="field-block">
          <label>区域（可选）</label>
          <input v-model="questionEditForm.area" placeholder="例如 伊朗 - 以色列" />
        </div>
        <div class="field-block">
          <label>输入类型（可选）</label>
          <input v-model="questionEditForm.inputType" placeholder="例如 news" />
        </div>
        <div class="field-block">
          <label>背景（可选）</label>
          <textarea v-model="questionEditForm.background" rows="3" placeholder="问题背景描述"></textarea>
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
            <option value="draft">收集中</option>
            <option value="pending_review">待评审</option>
            <option value="published">已发布</option>
            <option value="expired">已过期</option>
            <option value="matched">已匹配</option>
            <option value="closed">已解析</option>
          </select>
        </div>
        <div class="action-row">
          <button class="action-btn" @click="submitQuestionEdit">保存修改</button>
          <button
            class="action-btn danger"
            :disabled="Boolean(questions.find((item) => item.id === questionEditForm.id)?.deletedAt)"
            @click="deleteQuestionInEditDialog"
          >
            删除该问题
          </button>
        </div>
      </section>
    </div>

    <div
      v-if="questionDeleteReasonDialogOpen"
      class="dialog-backdrop dialog-backdrop-stacked"
      @click.self="closeQuestionDeleteReasonDialog"
    >
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>填写删除原因</h2>
          <button class="action-btn" @click="closeQuestionDeleteReasonDialog">关闭</button>
        </div>
        <div class="field-block">
          <label>删除原因</label>
          <select v-model="questionDeleteReasonPreset">
            <option value="" disabled>请选择删除原因</option>
            <option v-for="reason in questionDeleteReasonOptions" :key="`question-delete-reason-${reason}`" :value="reason">
              {{ reason }}
            </option>
            <option value="__custom__">其他（手动填写）</option>
          </select>
        </div>
        <div v-if="questionDeleteReasonPreset === '__custom__'" class="field-block">
          <label>自定义原因</label>
          <textarea v-model="questionDeleteReasonCustom" rows="3" placeholder="请填写删除原因"></textarea>
        </div>
        <small>将删除 {{ pendingDeleteQuestionIds.length }} 条问题记录</small>
        <div class="action-row action-right">
          <button class="action-btn" @click="closeQuestionDeleteReasonDialog">取消</button>
          <button class="action-btn danger" :disabled="!resolvedQuestionDeleteReason()" @click="void confirmQuestionDeleteWithReason()">
            确认删除
          </button>
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
          <p><strong>序号：</strong>{{ selectedTemplateDetail.templateIndex }}</p>
          <p><strong>问题模板：</strong>{{ selectedTemplateDetail.questionTemplate }}</p>
          <p><strong>难度等级：</strong>{{ selectedTemplateDetail.difficultyLevel }}</p>
          <p><strong>候选答案类型：</strong>{{ selectedTemplateDetail.candidateAnswerType }}</p>
          <p><strong>事件域：</strong>{{ selectedTemplateDetail.eventDomain }}</p>
          <p><strong>事件类型：</strong>{{ selectedTemplateDetail.eventType }}</p>
          <p><strong>事件类型ID：</strong>{{ selectedTemplateDetail.eventTypeId }}</p>
          <p><strong>作战层级：</strong>{{ selectedTemplateDetail.operationLevel }}</p>
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
          <label>序号</label>
          <input v-model.number="templateEditForm.templateIndex" type="number" min="1" step="1" />
        </div>
        <div class="field-block">
          <label>问题模板</label>
          <textarea v-model="templateEditForm.questionTemplate" rows="3"></textarea>
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
          <label>候选答案类型</label>
          <select v-model="templateEditForm.candidateAnswerType">
            <option value="fixed">fixed</option>
            <option value="dynamic">dynamic</option>
            <option value="open">open</option>
          </select>
        </div>
        <div class="field-block">
          <label>事件域</label>
          <input v-model="templateEditForm.eventDomain" />
        </div>
        <div class="field-block">
          <label>事件类型</label>
          <input v-model="templateEditForm.eventType" />
        </div>
        <div class="field-block">
          <label>事件类型ID</label>
          <input v-model="templateEditForm.eventTypeId" />
        </div>
        <div class="field-block">
          <label>作战层级</label>
          <input v-model="templateEditForm.operationLevel" />
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
          <label>序号</label>
          <input v-model.number="createTemplateForm.templateIndex" type="number" min="1" step="1" />
        </div>
        <div class="field-block">
          <label>问题模板</label>
          <textarea v-model="createTemplateForm.questionTemplate" rows="3"></textarea>
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
          <label>候选答案类型</label>
          <select v-model="createTemplateForm.candidateAnswerType">
            <option value="fixed">fixed</option>
            <option value="dynamic">dynamic</option>
            <option value="open">open</option>
          </select>
        </div>
        <div class="field-block">
          <label>事件域</label>
          <input v-model="createTemplateForm.eventDomain" />
        </div>
        <div class="field-block">
          <label>事件类型</label>
          <input v-model="createTemplateForm.eventType" />
        </div>
        <div class="field-block">
          <label>事件类型ID</label>
          <input v-model="createTemplateForm.eventTypeId" />
        </div>
        <div class="field-block">
          <label>作战层级</label>
          <input v-model="createTemplateForm.operationLevel" />
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
          <label>URL（可选）</label>
          <input v-model="draftEvent.url" placeholder="https://example.com/news" />
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
          <div class="question-event-multi-select" @scroll.passive="handleQuestionEventSelectScroll('create', $event)">
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
            <p v-if="questionEventSearchLoadingMore" class="item-subtle">正在加载更多...</p>
            <p
              v-else-if="backendOnline && questionEventSearchMode === 'create' && !questionEventSearchHasMore && filteredKnownEventsForQuestion.length > 0"
              class="item-subtle"
            >
              已加载全部匹配事件
            </p>
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
          <label>匹配分数（可选）</label>
          <input v-model="draftQuestion.matchScore" type="number" step="0.0001" min="0" placeholder="例如 0.7074" />
        </div>
        <div class="field-block">
          <label>事件域（可选）</label>
          <input v-model="draftQuestion.eventDomain" placeholder="例如 外交" />
        </div>
        <div class="field-block">
          <label>事件类型（可选）</label>
          <input v-model="draftQuestion.eventType" placeholder="例如 外交对话" />
        </div>
        <div class="field-block">
          <label>区域（可选）</label>
          <input v-model="draftQuestion.area" placeholder="例如 伊朗 - 以色列" />
        </div>
        <div class="field-block">
          <label>输入类型（可选）</label>
          <input v-model="draftQuestion.inputType" placeholder="例如 news" />
        </div>
        <div class="field-block">
          <label>背景（可选）</label>
          <textarea v-model="draftQuestion.background" rows="3" placeholder="问题背景描述"></textarea>
        </div>
        <div class="field-block">
          <label>初始状态</label>
          <select v-model="draftQuestion.status">
            <option value="draft">收集中</option>
            <option value="pending_review">待评审</option>
            <option value="published">已发布</option>
            <option value="expired">已过期</option>
            <option value="matched">已匹配</option>
            <option value="closed">已解析</option>
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

    <div v-if="apiKeyCreateDialogOpen" class="dialog-backdrop" @click.self="apiKeyCreateDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>新增 API Key</h2>
          <button class="action-btn" @click="apiKeyCreateDialogOpen = false">关闭</button>
        </div>
        <div class="field-block">
          <label>用户名称 <small>(不允许重复)</small></label>
          <input v-model="apiKeyFormName" placeholder="输入名称" />
        </div>
        <div class="field-block">
          <label>使用者类型</label>
          <select v-model="apiKeyFormUserType">
            <option value="agent">Agent</option>
            <option value="user">User</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="field-block">
          <label>用途 <small>(可选)</small></label>
          <select v-model="apiKeyFormPurpose">
            <option value="">不设置</option>
            <option value="模型问答">模型问答</option>
            <option value="接口调用">接口调用</option>
            <option value="其他">其他</option>
          </select>
        </div>
        <div class="action-row action-right">
          <button class="action-btn" @click="createApiKey">确定</button>
        </div>
      </section>
    </div>

    <div v-if="apiKeyEditDialogOpen" class="dialog-backdrop" @click.self="apiKeyEditDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>编辑 API Key</h2>
          <button class="action-btn" @click="apiKeyEditDialogOpen = false">关闭</button>
        </div>
        <div class="field-block">
          <label>用户名称 <small>(不允许重复)</small></label>
          <input v-model="apiKeyEditName" placeholder="输入名称" />
        </div>
        <div class="field-block">
          <label>使用者类型</label>
          <select v-model="apiKeyEditUserType">
            <option value="agent">Agent</option>
            <option value="user">User</option>
            <option value="other">Other</option>
          </select>
        </div>
        <div class="field-block">
          <label>用途 <small>(可选)</small></label>
          <select v-model="apiKeyEditPurpose">
            <option value="">不设置</option>
            <option value="模型问答">模型问答</option>
            <option value="接口调用">接口调用</option>
            <option value="其他">其他</option>
          </select>
        </div>
        <div class="action-row action-right">
          <button class="action-btn" @click="submitApiKeyEdit">保存</button>
        </div>
      </section>
    </div>

    <div v-if="apiKeyCreatedToken" class="dialog-backdrop" @click.self="apiKeyCreatedToken = ''">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>API Key 创建成功</h2>
        </div>
        <div class="field-block">
          <p><strong>{{ apiKeyCreatedName }}</strong> 的 API Key 已生成，请立即复制保存。关闭后可随时在列表中查看。</p>
        </div>
        <div class="field-block">
          <label>Token</label>
          <div class="action-row">
            <input :value="apiKeyCreatedToken" readonly style="flex:1" />
            <button class="action-btn" @click="copyToClipboard(apiKeyCreatedToken)">复制</button>
          </div>
        </div>
        <div class="action-row action-right">
          <button class="action-btn" @click="apiKeyCreatedToken = ''">关闭</button>
        </div>
      </section>
    </div>

    <div v-if="modelEndpointFormDialogOpen" class="dialog-backdrop" @click.self="modelEndpointFormDialogOpen = false">
      <section class="dialog-panel">
        <div class="panel-head">
          <h2>{{ modelEndpointFormIsEdit ? '编辑模型端点' : '新增模型端点' }}</h2>
          <button class="action-btn" @click="modelEndpointFormDialogOpen = false">关闭</button>
        </div>
        <div class="field-block">
          <label>名称 *</label>
          <input v-model="meFormName" placeholder="如：通义千问-Plus" />
        </div>
        <div class="field-block">
          <label>标识符 *</label>
          <input v-model="meFormIdentifier" :disabled="modelEndpointFormIsEdit" placeholder="如：qwen-plus" />
        </div>
        <div class="field-block">
          <label>提供商</label>
          <select v-model="meFormProvider" :disabled="modelEndpointFormIsEdit">
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
            <option value="custom">Custom</option>
            <option value="internal">Internal</option>
          </select>
        </div>
        <div class="field-block">
          <label>接口地址 *</label>
          <input v-model="meFormEndpointUrl" placeholder="https://api.example.com/v1" />
        </div>
        <div class="field-block">
          <label>API Key</label>
          <div class="action-row">
            <input :type="meApiKeyVisible ? 'text' : 'password'" v-model="meFormApiKeyRef" placeholder="sk-..." style="flex:1" />
            <button class="action-btn" @click="meApiKeyVisible = !meApiKeyVisible">{{ meApiKeyVisible ? '隐藏' : '显示' }}</button>
          </div>
        </div>
        <div class="field-block">
          <label>模型名称 *</label>
          <input v-model="meFormModelName" placeholder="如：qwen-plus" />
        </div>
        <div class="field-block">
          <label>版本</label>
          <input v-model="meFormModelVersion" placeholder="v1.0" />
        </div>
        <div class="field-block">
          <label>最大Token数</label>
          <input v-model="meFormMaxTokens" type="number" />
        </div>
        <div class="field-block">
          <label>温度 (0-2)</label>
          <input v-model="meFormTemperature" type="number" step="0.1" min="0" max="2" />
        </div>
        <div class="field-block">
          <label>超时时间(秒)</label>
          <input v-model="meFormTimeoutSeconds" type="number" />
        </div>
        <div class="field-block">
          <label>状态</label>
          <select v-model="meFormStatus">
            <option value="active">active</option>
            <option value="inactive">inactive</option>
            <option value="archived">archived</option>
          </select>
        </div>
        <div class="field-block">
          <label style="display:flex;align-items:center;gap:0.5rem">
            <input type="checkbox" :checked="meFormIsAvailable" @change="meFormIsAvailable = ($event.target as HTMLInputElement).checked" />
            可用
          </label>
        </div>
        <div class="action-row action-right">
          <button class="action-btn" @click="submitModelEndpoint()">{{ modelEndpointFormIsEdit ? '保存' : '确定' }}</button>
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
