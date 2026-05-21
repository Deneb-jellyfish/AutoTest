# Auth SUT — 软测作业被测应用

独立的**用户认证服务**，用于软件测试课程作业（AutoTestDesign 工具的被测目标应用）。

## 目录结构

| 路径 | 说明 |
|------|------|
| `auth-backend/` | Spring Boot 3.5 + 用户认证模块 |
| `auth-frontend/` | Vue 3 + Vite + Naive UI 简易页面 |
| `docker-compose.yml` | 可选：本机 PostgreSQL / Redis / MailHog |

## 快速启动

### 1. 后端（可选，本地调试）

配置见 [`auth-backend/src/main/resources/application.yml`](auth-backend/src/main/resources/application.yml)：

- PostgreSQL、Redis、邮件：远程服务器
- 本地默认端口：`8081`

```bash
cd sut/auth-backend
mvn spring-boot:run
```

健康检查：http://localhost:8081/actuator/health

### 2. 前端（默认对接服务器后端）

```bash
cd sut/auth-frontend
pnpm install
pnpm dev
```

浏览器：http://localhost:5173  
API 地址：`http://111.229.81.45/api/zdmj`（见 [`auth-frontend/.env`](auth-frontend/.env)）

> 日常使用前端即可，无需本地启动 `auth-backend`。改连本地后端见 `auth-frontend/.env.local.example`。

### 3. 测试账号

使用远程库 `users` 表中已有账号，或在前端完成注册。

> `sql/seed.sql` 仅用于 `docker compose` 本地库。

### 4. 可选：纯本地 Docker 环境

若无法访问远程服务器：

```bash
cd sut
docker compose up -d
```

并将 `application.yml` 中的 datasource / redis / mail 改为 `localhost:5433`、`6380`、MailHog（见 `docker-compose.yml`）。

## API 一览（前缀 `/api/zdmj`）

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/users` | 否 | 注册 |
| POST | `/users/login` | 否 | 登录 |
| POST | `/users/verification-codes?email=` | 否 | 发送验证码 |
| PUT | `/users/password` | 否 | 重置密码 |
| GET | `/users/validation/username` | 否 | 用户名是否存在 |
| GET | `/users/validation/email` | 否 | 邮箱是否存在 |
| GET | `/users/{id}` | 是 | 查询用户 |
| PUT | `/users/me` | 是 | 更新当前用户资料 |

### 登录示例

```bash
curl -s -X POST http://111.229.81.45/api/zdmj/users/login \
  -H 'Content-Type: application/json' \
  -d '{"usernameOrEmail":"your@email.com","password":"your-password"}'
```

## 软测作业用法

1. **需求输入**：登录需求可参考 `UserController`、`UserLoginDTO`。
2. **被测范围**：详细设计建议聚焦 **登录**（`POST /users/login`）。
3. **自动化**：MockMvc / REST Assured 指向服务器 `http://111.229.81.45/api/zdmj`，或本地 `http://localhost:8081/api/zdmj`。

## 配置说明

- 环境变量与密钥：复制 `application-example.yml` 填写。
- 本地后端端口 `8081`，避免与其它服务占用 `8080` 冲突。
