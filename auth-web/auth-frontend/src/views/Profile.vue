<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useMessage, NForm, NFormItem, NInput, NButton, NCard, NSpace, NText } from 'naive-ui';
import type { UserInfo } from '@/api/types';
import { fetchUpdateProfile } from '@/api/auth';

const router = useRouter();
const message = useMessage();
const loading = ref(false);
const tokenPreview = ref('');
const user = ref<UserInfo | null>(null);

const model = reactive({
  name: '',
  phone: '',
  website: ''
});

onMounted(() => {
  const token = localStorage.getItem('auth_token');
  if (!token) {
    router.replace('/login');
    return;
  }
  tokenPreview.value = token.length > 24 ? `${token.slice(0, 24)}...` : token;
  const raw = localStorage.getItem('auth_user');
  if (raw) {
    user.value = JSON.parse(raw) as UserInfo;
    model.name = user.value.name || '';
    model.phone = user.value.phone || '';
    model.website = user.value.website || '';
  }
});

function logout() {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('auth_user');
  router.push('/login');
}

async function handleSave() {
  loading.value = true;
  const { data, error } = await fetchUpdateProfile({
    name: model.name || undefined,
    phone: model.phone || undefined,
    website: model.website || undefined
  });
  loading.value = false;
  if (error || !data) {
    message.error(error || '更新失败');
    return;
  }
  localStorage.setItem('auth_user', JSON.stringify(data));
  user.value = data;
  message.success('资料已更新');
}
</script>

<template>
  <NCard title="登录成功">
    <NSpace vertical>
      <NText v-if="user">用户：{{ user.username }} ({{ user.email }})</NText>
      <NText depth="3">Token：{{ tokenPreview }}</NText>
    </NSpace>
    <NForm style="margin-top: 16px" label-placement="top">
      <NFormItem label="姓名">
        <NInput v-model:value="model.name" />
      </NFormItem>
      <NFormItem label="电话">
        <NInput v-model:value="model.phone" />
      </NFormItem>
      <NFormItem label="主页">
        <NInput v-model:value="model.website" />
      </NFormItem>
      <NSpace vertical>
        <NButton type="primary" block :loading="loading" @click="handleSave">保存资料 (PUT /users/me)</NButton>
        <NButton block @click="logout">退出登录</NButton>
      </NSpace>
    </NForm>
  </NCard>
</template>
