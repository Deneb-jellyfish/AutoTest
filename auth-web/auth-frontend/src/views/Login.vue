<script setup lang="ts">
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useMessage, NForm, NFormItem, NInput, NButton, NCard, NSpace } from 'naive-ui';
import { fetchLogin } from '@/api/auth';

const router = useRouter();
const message = useMessage();
const loading = ref(false);

const model = reactive({
  usernameOrEmail: '3516039373@qq.com',
  password: '654321'
});

async function handleSubmit() {
  if (!model.usernameOrEmail || !model.password) {
    message.warning('请输入用户名/邮箱和密码');
    return;
  }
  loading.value = true;
  const { data, error } = await fetchLogin(model.usernameOrEmail, model.password);
  loading.value = false;
  if (error || !data) {
    message.error(error || '登录失败');
    return;
  }
  localStorage.setItem('auth_token', data.token);
  localStorage.setItem('auth_user', JSON.stringify(data.user));
  message.success('登录成功');
  router.push('/profile');
}
</script>

<template>
  <NCard title="登录">
    <NForm @keyup.enter="handleSubmit">
      <NFormItem label="用户名或邮箱">
        <NInput v-model:value="model.usernameOrEmail" placeholder="用户名或邮箱" />
      </NFormItem>
      <NFormItem label="密码">
        <NInput v-model:value="model.password" type="password" show-password-on="click" placeholder="123456" />
      </NFormItem>
      <NSpace vertical>
        <NButton type="primary" block :loading="loading" @click="handleSubmit">登录</NButton>
        <NButton quaternary block @click="router.push('/register')">注册账号</NButton>
        <NButton quaternary block @click="router.push('/reset-password')">忘记密码</NButton>
      </NSpace>
    </NForm>
    <p class="hint">API：远程服务器 111.229.81.45（与主站后端相同）</p>
  </NCard>
</template>

<style scoped>
.hint {
  margin: 16px 0 0;
  font-size: 12px;
  color: #888;
}
</style>
