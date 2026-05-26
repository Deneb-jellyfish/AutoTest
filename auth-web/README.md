# Auth SUT — 软测作业被测应用

独立的**用户认证服务**，用于软件测试课程作业（AutoTestDesign 工具的被测目标应用）。

## 目录结构

| 路径 | 说明 |
|------|------|
| `auth-backend/` | Spring Boot 3.5 用户认证 API 源码（需求与实现参考） |
| `auth-frontend/` | Vue 3 + Vite + Naive UI 简易页面（可选，用于手工走查） |
| `docs/` | 风险分析报告、测试计划报告 |

## 被测 API

**基址**：`http://111.229.81.45/api/zdmj`  
**前缀**：`/api/zdmj`

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

## 前端页面（可选）

用于注册、登录、重置密码、个人资料等流程的手工验证。页面请求经 Vite 代理转发至上述 API 基址。

```bash
cd auth-frontend
pnpm install
pnpm dev
```

浏览器访问：http://localhost:5173

## 软测作业用法

1. **需求输入**：登录需求可参考 `UserController`、`UserLoginDTO`。
2. **被测范围**：详细设计建议聚焦 **登录**（`POST /users/login`）。
3. **自动化**：REST Assured / Apifox 等工具直接调用 `http://111.229.81.45/api/zdmj` 下各接口编写用例。

## 相关文档

- [风险分析报告](docs/1.风险分析报告.md)
- [测试计划报告](docs/2.测试计划报告.md)
