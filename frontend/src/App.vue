<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

type Level = 'L1' | 'L2' | 'L3' | 'L4'

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

const draftExpert = reactive({ name: '', answer: '', reason: '' })
const draftExpertComments = reactive<Record<string, string>>({})
const draftQuestionComment = ref('')

const selectedEvent = computed(() => events.value.find((eventItem) => eventItem.id === selectedEventId.value))
const selectedTemplate = computed(() => templateState[selectedLevel.value])
const selectedQuestion = computed(() => questions.value.find((question) => question.id === selectedQuestionId.value))

const filteredQuestions = computed(() =>
  questions.value.filter((question) => !selectedEventId.value || question.eventId === selectedEventId.value),
)

const selectedQuestionAnswers = computed(() => answersByQuestion[selectedQuestionId.value] ?? [])
const selectedExpertAnswers = computed(() => expertAnswersByQuestion[selectedQuestionId.value] ?? [])
const selectedQuestionComments = computed(() => questionCommentsByQuestion[selectedQuestionId.value] ?? [])

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
</script>

<template>
  <div class="mission-shell">
    <header class="topbar panel">
      <div>
        <p class="eyebrow">MOPPA 战术控制台</p>
        <h1>模型预测指挥甲板</h1>
      </div>
      <div class="status-pills">
        <span class="chip">数据源：模拟</span>
        <span class="chip">模式：训练沙盘</span>
      </div>
    </header>

    <main class="layout-grid">
      <section class="left-column">
        <article class="panel">
          <div class="panel-head">
            <h2>1) 事件监看</h2>
            <span>{{ events.length }} 条活跃</span>
          </div>
          <ul class="event-list">
            <li
              v-for="eventItem in events"
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
  </div>
</template>
