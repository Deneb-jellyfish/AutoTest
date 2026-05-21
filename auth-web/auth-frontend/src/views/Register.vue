<script setup lang="ts">
import { reactive, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useMessage, NForm, NFormItem, NInput, NButton, NCard, NSpace } from 'naive-ui';
import { fetchGetVerificationCode, fetchRegister } from '@/api/auth';

const router = useRouter();
const message = useMessage();
const loading = ref(false);
const codeLoading = ref(false);
const countdown = ref(0);

const model = reactive({
  username: '',
  email: '',
  code: '',
  password: '',
  confirmPassword: ''
});

const codeLabel = computed(() => (countdown.value > 0 ? `${countdown.value}s` : '获取验证码'));

async function sendCode() {
  if (!model.email) {
    message.warning('请先填写邮箱');
    return;
  }
  codeLoading.value = true;
  const { error } = await fetchGetVerificationCode(model.email);
  codeLoading.value = false;
  if (error) {
    message.error(error);
    return;
  }
  message.success('验证码已发送，请查收邮件');
  countdown.value = 60;
  const timer = setInterval(() => {
    countdown.value -= 1;
    if (countdown.value <= 0) clearInterval(timer);
  }, 1000);
}

async function handleSubmit() {
  if (!model.username || !model.email || !model.code || !model.password) {
    message.warning('请填写完整信息');
    return;
  }
  if (model.password !== model.confirmPassword) {
    message.warning('两次密码不一致');
    return;
  }
  loading.value = true;
  const { error } = await fetchRegister(model.username, model.password, model.email, model.code);
  loading.value = false;
  if (error) {
    message.error(error);
    return;
  }
  message.success('注册成功，请登录');
  router.push('/login');
}
</script>

<template>
  <NCard title="注册">
    <NForm @keyup.enter="handleSubmit">
      <NFormItem label="用户名">
        <NInput v-model:value="model.username" placeholder="用户名" />
      </NFormItem>
      <NFormItem label="邮箱">
        <NInput v-model:value="model.email" placeholder="email@example.com" />
      </NFormItem>
      <NFormItem label="验证码">
        <NSpace style="width: 100%">
          <NInput v-model:value="model.code" placeholder="6位验证码" style="flex: 1" />
          <NButton :disabled="countdown > 0" :loading="codeLoading" @click="sendCode">{{ codeLabel }}</NButton>
        </NSpace>
      </NFormItem>
      <NFormItem label="密码">
        <NInput v-model:value="model.password" type="password" show-password-on="click" />
      </NFormItem>
      <NFormItem label="确认密码">
        <NInput v-model:value="model.confirmPassword" type="password" show-password-on="click" />
      </NFormItem>
      <NSpace vertical>
        <NButton type="primary" block :loading="loading" @click="handleSubmit">注册</NButton>
        <NButton quaternary block @click="router.push('/login')">返回登录</NButton>
      </NSpace>
    </NForm>
  </NCard>
</template>
