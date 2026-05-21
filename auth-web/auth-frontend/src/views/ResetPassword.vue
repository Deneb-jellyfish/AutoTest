<script setup lang="ts">
import { reactive, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useMessage, NForm, NFormItem, NInput, NButton, NCard, NSpace } from 'naive-ui';
import { fetchGetVerificationCode, fetchResetPassword } from '@/api/auth';

const router = useRouter();
const message = useMessage();
const loading = ref(false);
const codeLoading = ref(false);
const countdown = ref(0);

const model = reactive({
  email: '',
  code: '',
  newPassword: '',
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
  message.success('验证码已发送，请在 MailHog 查看');
  countdown.value = 60;
  const timer = setInterval(() => {
    countdown.value -= 1;
    if (countdown.value <= 0) clearInterval(timer);
  }, 1000);
}

async function handleSubmit() {
  if (!model.email || !model.code || !model.newPassword) {
    message.warning('请填写完整信息');
    return;
  }
  if (model.newPassword !== model.confirmPassword) {
    message.warning('两次密码不一致');
    return;
  }
  loading.value = true;
  const { error } = await fetchResetPassword(model.email, model.code, model.newPassword);
  loading.value = false;
  if (error) {
    message.error(error);
    return;
  }
  message.success('密码已重置，请登录');
  router.push('/login');
}
</script>

<template>
  <NCard title="重置密码">
    <NForm @keyup.enter="handleSubmit">
      <NFormItem label="注册邮箱">
        <NInput v-model:value="model.email" placeholder="email@example.com" />
      </NFormItem>
      <NFormItem label="验证码">
        <NSpace style="width: 100%">
          <NInput v-model:value="model.code" placeholder="6位验证码" style="flex: 1" />
          <NButton :disabled="countdown > 0" :loading="codeLoading" @click="sendCode">{{ codeLabel }}</NButton>
        </NSpace>
      </NFormItem>
      <NFormItem label="新密码">
        <NInput v-model:value="model.newPassword" type="password" show-password-on="click" />
      </NFormItem>
      <NFormItem label="确认新密码">
        <NInput v-model:value="model.confirmPassword" type="password" show-password-on="click" />
      </NFormItem>
      <NSpace vertical>
        <NButton type="primary" block :loading="loading" @click="handleSubmit">重置密码</NButton>
        <NButton quaternary block @click="router.push('/login')">返回登录</NButton>
      </NSpace>
    </NForm>
  </NCard>
</template>
