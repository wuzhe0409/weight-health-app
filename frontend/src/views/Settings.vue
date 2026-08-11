<template>
  <div class="page">
    <h2>设置</h2>

    <el-card class="section">
      <template #header>个人资料</template>
      <el-form :model="profile" label-width="120px" style="max-width:560px">
        <el-form-item label="性别"><el-input v-model="profile.gender" /></el-form-item>
        <el-form-item label="年龄"><el-input v-model.number="profile.age" type="number" /></el-form-item>
        <el-form-item label="身高(cm)"><el-input v-model.number="profile.height_cm" type="number" /></el-form-item>
        <el-form-item label="骨架">
          <el-select v-model="profile.frame_size">
            <el-option label="小" value="small" />
            <el-option label="中小" value="small_medium" />
            <el-option label="中" value="medium" />
            <el-option label="大" value="large" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标体重(kg)"><el-input v-model.number="profile.target_weight_kg" type="number" step="0.1" /></el-form-item>
        <el-form-item label="BMR 公式"><el-input v-model="profile.bmr_formula" /></el-form-item>
      </el-form>
      <el-button type="primary" @click="saveProfile">保存资料</el-button>
    </el-card>

    <el-card class="section">
      <template #header>
        <span class="accent-title">AI 模型配置</span>
      </template>
      <el-alert
        type="info"
        :closable="false"
        title="支持 OpenAI 兼容接口"
        description="可填 OpenAI、DeepSeek、智谱 GLM、腾讯混元等。Key 只保存在本地 SQLite，不会上传到我的服务器。未配置时 AI 分析会给出占位提示。"
        style="margin-bottom:16px"
      />
      <el-form :model="llm" label-width="120px" style="max-width:640px">
        <el-form-item label="服务商">
          <el-select v-model="llm.llm_provider" style="width:100%" @change="onProviderChange">
            <el-option label="DeepSeek（推荐·最划算）" value="deepseek" />
            <el-option label="OpenAI" value="openai" />
            <el-option label="智谱 GLM（支持看图）" value="zhipu" />
            <el-option label="自定义 / 腾讯混元" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="Base URL">
          <el-input v-model="llm.llm_base_url" placeholder="如 https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input
            v-model="llm.llm_api_key"
            :type="showKey ? 'text' : 'password'"
            placeholder="sk-..."
            autocomplete="off"
          >
            <template #suffix>
              <el-button link @click="showKey = !showKey">{{ showKey ? '隐藏' : '显示' }}</el-button>
            </template>
          </el-input>
          <span class="muted">已保存的 key 会被掩码显示；提交空值表示保持原 key 不变。</span>
        </el-form-item>
        <el-form-item label="模型">
          <el-input v-model="llm.llm_model" placeholder="如 gpt-4o-mini / deepseek-chat / glm-4v" />
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="saveLlm">保存模型配置</el-button>
      <el-button @click="testLlm" :loading="testing">测试连接</el-button>
    </el-card>

    <el-card class="section">
      <template #header>
        <span class="accent-title">视觉模型（图片分析专用）</span>
      </template>
      <el-alert
        type="info" :closable="false"
        title="自动切换"
        description="粘贴食物图片时自动使用此模型（如智谱 GLM-4V）。不填则图片分析退回文字模型。智谱 GLM-4V-Flash 有免费额度，注册 open.bigmodel.cn 即可。"
        style="margin-bottom:16px"
      />
      <el-form :model="vision" label-width="120px" style="max-width:560px">
        <el-form-item label="Base URL">
          <el-input v-model="vision.vision_base_url" placeholder="https://open.bigmodel.cn/api/paas/v4/" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="vision.vision_api_key" :type="showKey2 ? 'text' : 'password'" placeholder="智谱 API key" autocomplete="off">
            <template #suffix>
              <el-button link @click="showKey2 = !showKey2">{{ showKey2 ? '隐藏' : '显示' }}</el-button>
            </template>
          </el-input>
          <span class="muted">提交空值表示保持原 key。</span>
        </el-form-item>
        <el-form-item label="模型">
          <el-input v-model="vision.vision_model" placeholder="glm-4v-flash" />
        </el-form-item>
      </el-form>
      <el-button type="primary" @click="saveVision">保存视觉模型</el-button>
    </el-card>

    <el-card class="section">
      <template #header>历史数据导入（幂等 / 锁定）</template>
      <el-alert type="info" :closable="false" title="导入只追加不覆盖；已存在日期自动跳过，导入后记录锁定。" />
      <div style="margin-top:12px">
        <el-button @click="doImport(true)">试运行（dry-run）</el-button>
        <el-button type="primary" @click="doImport(false)">导入历史数据</el-button>
        <span v-if="importMsg" class="muted" style="margin-left:12px">{{ importMsg }}</span>
      </div>
    </el-card>

    <el-card class="section">
      <template #header>导出 / 备份</template>
      <el-button @click="doExport('json')">导出 JSON</el-button>
      <el-button @click="doExport('csv')">导出 CSV</el-button>
    </el-card>

    <el-card class="section">
      <template #header>数据安全策略</template>
      <ul class="muted" style="line-height:1.9">
        <li>历史数据来自开发包，导入前已做只读拷贝（seed/，权限 444），原始文件零改动。</li>
        <li>重复导入按日期跳过，不会生成重复记录（幂等）。</li>
        <li>历史记录导入后默认锁定，普通编辑不可覆盖；更正须走「修订」，并写入审计日志。</li>
        <li>估算热量始终保留最小值/最大值与数据状态，不伪装成精确值。</li>
        <li>数据库迁移 / 重新导入前建议先「导出」备份。</li>
      </ul>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api'

const profile = reactive({
  gender: 'female', age: 30, height_cm: 160, frame_size: 'small_medium',
  target_weight_kg: 48, bmr_formula: 'Mifflin-St Jeor',
})
// Preset Base URL + model per provider. Switching provider auto-fills these
// (only when the field is empty or still holds another preset's default).
const PRESETS: Record<string, { base_url: string; model: string }> = {
  openai: { base_url: 'https://api.openai.com/v1', model: 'gpt-4o-mini' },
  deepseek: { base_url: 'https://api.deepseek.com/v1', model: 'deepseek-chat' },
  zhipu: { base_url: 'https://open.bigmodel.cn/api/paas/v4/', model: 'glm-4v-flash' },
}
const PRESET_BASE_URLS = new Set(Object.values(PRESETS).map((p) => p.base_url))
const PRESET_MODELS = new Set(Object.values(PRESETS).map((p) => p.model))

const llm = reactive({
  llm_provider: 'deepseek',
  llm_base_url: '',
  llm_api_key: '',
  llm_model: 'deepseek-chat',
})
const importMsg = ref('')
const showKey = ref(false)
const showKey2 = ref(false)
const testing = ref(false)

const vision = reactive({
  vision_api_key: '',
  vision_base_url: 'https://open.bigmodel.cn/api/paas/v4/',
  vision_model: 'glm-4v-flash',
})

// Fill Base URL / model from the provider preset. `force` = user actively
// switched provider (overwrite preset values); otherwise only fill blanks.
function applyProviderDefaults(force = false) {
  const preset = PRESETS[llm.llm_provider]
  if (!preset) return
  const baseIsPreset = llm.llm_base_url === '' || PRESET_BASE_URLS.has(llm.llm_base_url)
  const modelIsPreset = llm.llm_model === '' || PRESET_MODELS.has(llm.llm_model)
  if (force || baseIsPreset) llm.llm_base_url = preset.base_url
  if (force || modelIsPreset) llm.llm_model = preset.model
}

async function loadProfile() {
  try {
    const { data } = await api.profile()
    Object.assign(profile, data)
    Object.assign(llm, {
      llm_provider: data.llm_provider || 'deepseek',
      llm_base_url: data.llm_base_url || '',
      llm_api_key: data.llm_api_key || '',
      llm_model: data.llm_model || 'deepseek-chat',
    })
    // Auto-fill preset URLs/models when the saved value is blank.
    applyProviderDefaults(false)
    Object.assign(vision, {
      vision_api_key: data.vision_api_key || '',
      vision_base_url: data.vision_base_url || 'https://open.bigmodel.cn/api/paas/v4/',
      vision_model: data.vision_model || 'glm-4v-flash',
    })
  } catch (e) { /* ignore */ }
}
async function saveProfile() {
  const payload: any = { ...profile, ...llm }
  // Strip masked placeholders AFTER merging — otherwise {...payload, ...llm}
  // would re-introduce the masked key and overwrite the real one.
  if (typeof payload.llm_api_key === 'string' && payload.llm_api_key.includes('*')) delete payload.llm_api_key
  if (typeof payload.vision_api_key === 'string' && payload.vision_api_key.includes('*')) delete payload.vision_api_key
  await api.updateProfile(payload)
  ElMessage.success('设置已保存')
  await loadProfile()
}
async function saveLlm() {
  const payload: any = { ...llm }
  // If user submitted empty key it means "keep existing"; send undefined.
  if (!payload.llm_api_key || payload.llm_api_key.includes('*')) {
    delete payload.llm_api_key
  }
  await api.updateProfile(payload)
  ElMessage.success('模型配置已保存')
  await loadProfile()
}
async function saveVision() {
  const payload: any = { ...vision }
  if (!payload.vision_api_key || payload.vision_api_key.includes('*')) {
    delete payload.vision_api_key
  }
  await api.updateProfile(payload)
  ElMessage.success('视觉模型已保存')
  await loadProfile()
}
function onProviderChange() {
  applyProviderDefaults(true)
}

async function testLlm() {
  if (!llm.llm_api_key || llm.llm_api_key.includes('*')) {
    ElMessage.warning('请先填写真实的 API Key 再测试')
    return
  }
  testing.value = true
  try {
    const payload: any = { ...llm, text: '你好，请回复"连接成功"。', record_date: new Date().toISOString().slice(0, 10) }
    await api.aiAnalyze(payload)
    ElMessage.success('连接成功')
  } catch (e: any) {
    const msg = e.response?.data?.detail || e.message
    ElMessage.error(`连接失败：${msg}`)
  } finally {
    testing.value = false
  }
}
async function doImport(dry: boolean) {
  const { data } = await api.importHistory('json', dry)
  importMsg.value = `插入 ${data.inserted} / 跳过 ${data.skipped} / 错误 ${data.errors}` + (dry ? '（试运行）' : '')
  ElMessage.success('导入完成')
}
function doExport(format: string) {
  api.exportData(format).then((r) => {
    const blob = new Blob([r.data])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `weight_records.${format}`
    a.click()
    URL.revokeObjectURL(url)
  })
}
onMounted(loadProfile)
</script>
