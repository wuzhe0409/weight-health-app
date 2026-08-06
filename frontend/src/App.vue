<template>
  <el-container>
    <el-aside width="208px" class="app-aside">
      <div class="app-brand">
        <span class="logo">💜</span>
        <span>减脂记录<span class="sub">WEIGHT · HEALTH</span></span>
      </div>
      <el-menu :default-active="active" router>
        <el-menu-item index="/ai-chat"><el-icon><ChatDotSquare /></el-icon>AI 顾问</el-menu-item>
        <el-menu-item index="/today"><el-icon><Edit /></el-icon>今日记录</el-menu-item>
        <el-menu-item index="/calendar"><el-icon><Calendar /></el-icon>历史日历</el-menu-item>
        <el-menu-item index="/trends"><el-icon><TrendCharts /></el-icon>趋势</el-menu-item>
        <el-menu-item index="/settings"><el-icon><Setting /></el-icon>设置</el-menu-item>
      </el-menu>
    </el-aside>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const active = computed(() => {
  const seg = route.path.split('/')[1] || 'today'
  return seg ? '/' + seg : '/today'
})
</script>
