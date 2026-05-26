import { createRouter, createWebHistory } from 'vue-router';
import Login from '@/views/Login.vue';
import Register from '@/views/Register.vue';
import ResetPassword from '@/views/ResetPassword.vue';
import Profile from '@/views/Profile.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/login' },
    { path: '/login', name: 'login', component: Login },
    { path: '/register', name: 'register', component: Register },
    { path: '/reset-password', name: 'reset-password', component: ResetPassword },
    { path: '/profile', name: 'profile', component: Profile }
  ]
});

export default router;
