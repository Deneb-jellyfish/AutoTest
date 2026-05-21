<script setup lang="ts">
import { NConfigProvider, NMessageProvider, zhCN, dateZhCN } from 'naive-ui';
</script>

<template>
  <NConfigProvider :locale="zhCN" :date-locale="dateZhCN">
    <NMessageProvider>
      <div class="app-shell">
        <header class="app-header">
          <h1>Auth SUT</h1>
          <p>zdmj 用户认证 — 软测作业被测应用</p>
        </header>
        <main class="app-main">
          <RouterView />
        </main>
      </div>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style>
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  background: #f5f7fa;
}
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 16px;
}
.app-header {
  text-align: center;
  margin-bottom: 24px;
}
.app-header h1 {
  margin: 0 0 8px;
  font-size: 1.5rem;
}
.app-header p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}
.app-main {
  width: 100%;
  max-width: 420px;
}
</style>
