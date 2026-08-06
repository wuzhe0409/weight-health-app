<template>
  <div class="page">
    <h2>AI 营养顾问</h2>

    <!-- ============================================================
        Chat dialog
       ============================================================ -->
    <el-card class="section chat-card">
      <template #header>
        <span class="accent-title">💬 对话</span>
        <span class="muted" style="margin-left:8px;font-weight:400">
          输入饮食记录或提问 · 支持 Ctrl+V 粘贴图片 · Ctrl+Enter 发送
        </span>
        <el-button size="small" text style="float:right" @click="clearHistory">清空对话</el-button>
      </template>

      <!-- Quick actions -->
      <div class="quick-actions">
        <el-tag v-for="qa in quickActions" :key="qa" class="quick-tag" @click="nlText = qa; onSendChat()">{{ qa }}</el-tag>
      </div>

      <div class="chat-messages" v-if="chatMessages.length" ref="chatBox">
        <div v-for="(m, i) in chatMessages" :key="i" :class="m.role === 'user' ? 'chat-msg-user' : 'chat-msg-ai'">
          <div class="chat-bubble" v-html="renderMd(m.content)" />
          <div v-if="m.images && m.images.length" class="chat-images">
            <img v-for="(img, j) in m.images" :key="j" :src="img.dataUrl" class="chat-thumb" />
          </div>
        </div>
        <div v-if="chatLoading" class="chat-msg-ai">
          <div class="chat-bubble"><el-icon class="is-loading"><Loading /></el-icon> AI 思考中…</div>
        </div>
      </div>

      <div class="paste-area" @paste="onPaste">
        <el-input v-model="nlText" type="textarea" :rows="3" placeholder="8月5日 体重49.0 早饭吃了... 午饭..." @keydown.enter.ctrl="onSendChat" />
        <div v-if="imageList.length" class="image-preview-row">
          <div v-for="(img, i) in imageList" :key="i" class="image-preview-item">
            <img :src="img.dataUrl" />
            <el-button size="small" circle @click="removeImage(i)" class="img-remove-btn">✕</el-button>
          </div>
        </div>
      </div>

      <div style="margin-top:10px;display:flex;gap:10px">
        <el-button type="primary" @click="onAiAnalyze" :loading="aiLoading">
          <el-icon style="margin-right:4px"><MagicStick /></el-icon>智能分析
        </el-button>
        <el-button @click="onSendChat" :loading="chatLoading" :disabled="!nlText.trim()">发送提问</el-button>
      </div>
    </el-card>

    <!-- ============================================================
        AI Analyze result + Save to record
       ============================================================ -->
    <div class="section" v-if="aiResult">
      <el-card>
        <template #header>
          <div style="display:flex;align-items:center;justify-content:space-between">
            <span class="accent-title">分析结果</span>
            <div>
              <el-tag v-if="aiResult.score != null" type="warning" effect="dark" style="margin-right:10px">评分 {{ aiResult.score }}</el-tag>
              <el-button type="success" @click="saveToRecord" :loading="saving">保存记录</el-button>
              <el-button size="small" style="margin-left:8px" @click="jumpToToday" :disabled="!savedDate">去今日记录查看 →</el-button>
            </div>
          </div>
        </template>

        <div v-if="aiResult.kcal_breakdown && aiResult.kcal_breakdown.length">
          <div class="accent-title" style="margin-bottom:8px">热量估算明细</div>
          <el-table :data="aiResult.kcal_breakdown" size="small" border>
            <el-table-column prop="meal" label="餐次" width="80" />
            <el-table-column prop="food" label="食物" />
            <el-table-column prop="quantity" label="份量" width="160" />
            <el-table-column label="热量" width="130">
              <template #default="{ row }">
                <span v-if="row.kcal_min != null && row.kcal_max != null">{{ row.kcal_min }}~{{ row.kcal_max }}</span>
                <span v-else class="muted">未估算</span>
              </template>
            </el-table-column>
            <el-table-column prop="note" label="说明" min-width="160" />
          </el-table>
          <div style="margin-top:10px;font-size:15px">
            今日总热量：<b class="stat-num-purple">{{ aiResult.structured?.total_kcal_min ?? '—' }} ~ {{ aiResult.structured?.total_kcal_max ?? '—' }}</b> kcal
          </div>
        </div>

        <div v-if="aiResult.weight_analysis" style="margin-top:16px">
          <div class="accent-title" style="margin-bottom:8px">体重分析</div>
          <div class="ai-markdown" v-html="renderMd(aiResult.weight_analysis)" />
        </div>
        <div v-if="aiResult.weight_prediction" style="margin-top:16px">
          <div class="accent-title" style="margin-bottom:8px">明天体重预测</div>
          <div class="ai-markdown" v-html="renderMd(aiResult.weight_prediction)" />
        </div>
        <div v-if="aiResult.suggestions" style="margin-top:16px">
          <div class="accent-title" style="margin-bottom:8px">建议</div>
          <div class="ai-markdown" v-html="renderMd(aiResult.suggestions)" />
        </div>

        <!-- Fallback: 模型未返回结构化分析（如图片不兼容 / 配置错误）时展示原始提示 -->
        <el-alert
          v-if="aiResult.markdown && !hasStructuredContent(aiResult)"
          type="warning" :closable="false"
          :title="extractTitle(aiResult.markdown)"
          style="margin-top:12px"
        >
          <div v-html="renderMd(aiResult.markdown)" style="white-space:pre-wrap;line-height:1.7" />
        </el-alert>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { MagicStick, Loading } from '@element-plus/icons-vue'
import api from '@/api'

const CHAT_STORAGE_KEY = 'weight-health-chat-history'

const router = useRouter()
const nlText = ref('')
const imageList = ref<{ name: string; dataUrl: string }[]>([])
const aiLoading = ref(false)
const chatLoading = ref(false)
const saving = ref(false)
const aiResult = ref<any>(null)
const savedDate = ref('')
const chatMessages = ref<{ role: string; content: string; images?: { name: string; dataUrl: string }[] }[]>([])
const chatBox = ref<HTMLElement | null>(null)

const quickActions = [
  '我今天还能吃什么？',
  '分析一下我这周的体重趋势',
  '最近饮食有什么问题吗？',
  '明天体重会涨还是跌？',
]

// ── Persistent history (V2) ──
function loadHistory() {
  try {
    const saved = localStorage.getItem(CHAT_STORAGE_KEY)
    if (saved) chatMessages.value = JSON.parse(saved)
  } catch { /* ignore */ }
}
function saveHistory() {
  try {
    // Only save last 30 messages to avoid bloating
    const recent = chatMessages.value.slice(-30)
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(recent))
  } catch { /* ignore */ }
}
function clearHistory() {
  chatMessages.value = []
  localStorage.removeItem(CHAT_STORAGE_KEY)
  ElMessage.success('对话已清空')
}
watch(chatMessages, () => saveHistory(), { deep: true })
onMounted(loadHistory)

function renderMd(text: string) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function hasStructuredContent(r: any) {
  return !!(r?.kcal_breakdown?.length || r?.weight_analysis || r?.suggestions)
}

function extractTitle(md: string) {
  // 把 markdown 里第一个 **...** 当作 alert 标题
  const m = (md || '').match(/\*\*(.+?)\*\*/)
  return m ? m[1].replace(/\n/g, ' ') : 'AI 反馈'
}

function onPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of Array.from(items)) {
    if (!item.type.startsWith('image/')) continue
    e.preventDefault()
    const file = item.getAsFile()
    if (!file) continue
    const reader = new FileReader()
    reader.onload = () => imageList.value.push({ name: `clipboard-${Date.now()}.png`, dataUrl: String(reader.result) })
    reader.readAsDataURL(file)
  }
}
function removeImage(i: number) { imageList.value.splice(i, 1) }

function scrollChat() {
  nextTick(() => { if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight })
}

// ---- AI Chat ----
async function onSendChat() {
  const msg = nlText.value.trim()
  if (!msg) return
  const imgs = imageList.value.length ? [...imageList.value] : []
  chatMessages.value.push({ role: 'user', content: msg, images: imgs })
  nlText.value = ''
  imageList.value = []
  chatLoading.value = true
  await nextTick(); scrollChat()

  try {
    const history = chatMessages.value.slice(0, -1).map(m => ({ role: m.role, content: m.content }))
    const { data } = await api.aiChat(msg, history)
    chatMessages.value.push({ role: 'assistant', content: data.reply })
  } catch (e: any) {
    chatMessages.value.push({ role: 'assistant', content: `出错了：${e.response?.data?.detail || e.message}` })
  } finally {
    chatLoading.value = false
    await nextTick(); scrollChat()
  }
}

// ---- AI Analyze ----
async function onAiAnalyze() {
  if (!nlText.value.trim() && !imageList.value.length) { ElMessage.warning('请先输入文字或粘贴图片'); return }
  aiLoading.value = true
  try {
    const { data } = await api.aiAnalyze({
      text: nlText.value,
      record_date: new Date().toISOString().slice(0, 10),
      images: imageList.value.map(i => i.dataUrl),
    })
    aiResult.value = data
    savedDate.value = data.structured?.record_date || ''
    if (data.kcal_breakdown?.length || data.weight_analysis || data.suggestions) {
      ElMessage.success('分析完成，点击「保存记录」即可存入')
    } else if (data.image_note) {
      ElMessage.warning('当前模型不支持图片，已跳过图片分析')
    } else if (data.markdown) {
      ElMessage.warning(data.markdown.slice(0, 60))
    } else {
      ElMessage.warning('AI 未返回结构化结果')
    }
  } catch (e: any) {
    ElMessage.error(`分析失败：${e.response?.data?.detail || e.message}`)
  } finally { aiLoading.value = false }
}

// ---- Save to record ----
async function saveToRecord() {
  if (!aiResult.value) return
  const s = aiResult.value.structured || {}
  const recordDate = s.record_date || new Date().toISOString().slice(0, 10)

  const foodEntries = (aiResult.value.kcal_breakdown || []).map((item: any) => ({
    meal_type: item.meal || 'snack',
    food_name: item.food || '',
    quantity_text: item.quantity || '',
    kcal: item.kcal_max ?? item.kcal_min ?? null,
    kcal_source: 'estimated',
  }))

  const payload = {
    record_date: recordDate,
    weight_kg: s.weight_kg ?? null,
    bowel_movement: s.bowel_movement || 'unknown',
    period_status: s.period_status || null,
    period_day: s.period_day ?? null,
    period_days_until: s.period_days_until ?? null,
    total_kcal_min: s.total_kcal_min ?? null,
    total_kcal_max: s.total_kcal_max ?? null,
    total_kcal_confirmed: null,
    analysis: [aiResult.value.weight_analysis, aiResult.value.suggestions].filter(Boolean).join('\n\n'),
    notes: '',
    data_status: s.data_status || 'estimated',
    raw_input: null,
    food_entries: foodEntries,
  }

  saving.value = true
  try {
    // Check if already exists to decide save vs revision
    try {
      await api.getRecord(recordDate)
      // exists – use revision
      await api.revision(recordDate, payload)
      ElMessage.success('已更新保存（原记录已修订）')
    } catch {
      await api.saveRecord(payload)
      ElMessage.success(`已保存到 ${recordDate} 的记录`)
    }
    savedDate.value = recordDate
  } catch (e: any) {
    ElMessage.error(`保存失败：${e.response?.data?.detail || e.message}`)
  } finally { saving.value = false }
}

function jumpToToday() {
  if (savedDate.value) router.push(`/today?date=${savedDate.value}`)
}
</script>

<style scoped>
.chat-card { border: 2px solid var(--brand-200) !important; }
.chat-messages {
  max-height: 400px;
  overflow-y: auto;
  margin-bottom: 12px;
  padding-right: 4px;
}
.chat-msg-user { display: flex; justify-content: flex-end; margin-bottom: 10px; }
.chat-msg-ai   { display: flex; justify-content: flex-start; margin-bottom: 10px; }
.chat-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 14px;
  line-height: 1.65;
  font-size: 14px;
}
.chat-msg-user .chat-bubble {
  background: var(--brand-grad);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.chat-msg-ai .chat-bubble {
  background: #f3f0fb;
  color: #2e293b;
  border-bottom-left-radius: 4px;
}
.chat-images { display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.chat-thumb { width: 80px; height: 80px; object-fit: cover; border-radius: 10px; border: 1px solid var(--brand-100); }

.paste-area {
  border: 2px dashed var(--brand-200);
  border-radius: 12px;
  padding: 10px;
  transition: border-color 0.2s;
}
.paste-area:focus-within { border-color: var(--brand-400); }

.image-preview-row { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.image-preview-item { position: relative; width: 72px; height: 72px; }
.image-preview-item img { width: 100%; height: 100%; object-fit: cover; border-radius: 10px; border: 1px solid var(--brand-100); }
.img-remove-btn {
  position: absolute; top: -6px; right: -6px;
  width: 20px; height: 20px; font-size: 11px;
}

.ai-markdown {
  line-height: 1.7; color: #4b5563;
  background: #faf8ff; padding: 12px 14px;
  border-radius: 10px; border: 1px solid #ede7fb;
}

/* ── V2: 快速提问 ── */
.quick-actions {
  display: flex; gap: 8px; flex-wrap: wrap;
  margin-bottom: 12px; padding-bottom: 12px;
  border-bottom: 1px solid var(--brand-100);
}
.quick-tag {
  cursor: pointer; transition: all 0.2s;
  background: var(--brand-50); color: var(--brand-700);
  border-color: var(--brand-200);
}
.quick-tag:hover {
  background: var(--brand-200); color: var(--brand-900);
  transform: translateY(-1px);
}
</style>
