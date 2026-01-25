# 智能采购管理系统 - 部署手册

## 系统概述

智能采购管理系统是一个基于 AI 的采购需求分析与库存匹配平台，支持：
- 文本/Excel 采购需求解析
- DeepSeek AI 智能匹配库存
- 采购清单 Excel 导出
- RBAC 权限管理

## 技术栈

| 组件 | 技术 | 版本要求 |
|------|------|----------|
| 后端 | Python + FastAPI | Python 3.10+ |
| 前端 | Vue3 + Element Plus | Node.js 18+ |
| 数据库 | MySQL | 8.0+ |
| AI服务 | DeepSeek API | - |
| 部署 | Docker | 20.0+ |

## 环境要求

### 服务器配置
- CPU: 2核+
- 内存: 4GB+
- 磁盘: 20GB+
- 操作系统: Linux (推荐 Ubuntu 20.04+)

### 必需软件
- Docker 20.0+
- Docker Compose 2.0+ (可选)
- Node.js 18+ (仅构建前端时需要)

## 配置说明

### 环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `DATABASE_URL` | MySQL 数据库连接串 | `mysql+pymysql://user:pass@host:port/dbname` |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | `sk-xxxxxxxxxxxx` |
| `DEEPSEEK_API_URL` | DeepSeek API 地址 | `https://api.deepseek.com/v1` |

### 数据库准备

系统首次启动时会自动创建以下数据表：
- `sys_user` - 用户表
- `sys_role` - 角色表
- `sys_menu` - 菜单表
- `user_role` - 用户角色关联表
- `role_menu` - 角色菜单关联表
- `asset_inventory` - 库存表
- `procurement_task` - 采购任务表
- `procurement_detail` - 采购明细表

**默认管理员账号**: `admin` / `admin123`

---

## 部署方式一：Docker 命令行部署（推荐）

### 步骤 1：构建前端

```bash
cd frontend
npm install
npm run build
cd ..
```

### 步骤 2：构建 Docker 镜像

```bash
docker build -f Dockerfile.simple -t smart-procurement .
```

### 步骤 3：运行容器

```bash
docker run -d \
  --name smart-procurement-app \
  -p 8080:80 \
  -e DATABASE_URL="mysql+pymysql://用户名:密码@数据库地址:端口/数据库名" \
  -e DEEPSEEK_API_KEY="your-deepseek-api-key" \
  -e DEEPSEEK_API_URL="https://api.deepseek.com/v1" \
  --restart unless-stopped \
  smart-procurement
```

### 步骤 4：验证部署

```bash
# 检查容器状态
docker ps | grep smart-procurement

# 查看日志
docker logs -f smart-procurement-app
```

访问 `http://服务器IP:8080` 即可使用系统。

---

## 部署方式二：Docker Compose 部署

### 步骤 1：修改配置

编辑 `docker-compose.yml`，修改环境变量：

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.simple
    container_name: smart-procurement
    ports:
      - "8080:80"
    environment:
      - DATABASE_URL=mysql+pymysql://用户名:密码@数据库地址:端口/数据库名
      - DEEPSEEK_API_KEY=your-deepseek-api-key
      - DEEPSEEK_API_URL=https://api.deepseek.com/v1
    restart: unless-stopped
```

### 步骤 2：构建前端并启动

```bash
# 构建前端
cd frontend && npm install && npm run build && cd ..

# 启动服务
docker-compose up -d --build
```

### 步骤 3：查看状态

```bash
docker-compose ps
docker-compose logs -f
```

---

## 部署方式三：本地开发部署

### 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DATABASE_URL="mysql+pymysql://用户名:密码@数据库地址:端口/数据库名"
export DEEPSEEK_API_KEY="your-deepseek-api-key"
export DEEPSEEK_API_URL="https://api.deepseek.com/v1"

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端开发服务器运行在 `http://localhost:5173`，API 代理到后端 `http://localhost:8000`。

---

## 运维管理

### 常用命令

```bash
# 查看容器状态
docker ps

# 查看实时日志
docker logs -f smart-procurement-app

# 重启容器
docker restart smart-procurement-app

# 停止容器
docker stop smart-procurement-app

# 删除容器
docker rm smart-procurement-app

# 更新部署
docker stop smart-procurement-app
docker rm smart-procurement-app
docker build -f Dockerfile.simple -t smart-procurement .
docker run -d --name smart-procurement-app ... (同上)
```

### 数据备份

库存数据存储在 MySQL 数据库中，请定期备份数据库：

```bash
mysqldump -h 数据库地址 -P 端口 -u 用户名 -p 数据库名 > backup_$(date +%Y%m%d).sql
```

### 日志查看

```bash
# 查看最近100行日志
docker logs --tail 100 smart-procurement-app

# 实时跟踪日志
docker logs -f smart-procurement-app
```

---

## 故障排查

### 1. 容器启动失败

```bash
# 查看详细错误
docker logs smart-procurement-app
```

常见原因：
- 数据库连接失败：检查 DATABASE_URL 配置
- 端口被占用：修改映射端口或停止占用端口的服务

### 2. DeepSeek API 调用失败

- **401 错误**: API Key 无效，检查 DEEPSEEK_API_KEY 配置
- **超时**: 网络问题，检查服务器是否能访问 api.deepseek.com
- **429 错误**: 请求频率超限，稍后重试

### 3. 数据库连接失败

检查项：
- 数据库地址和端口是否正确
- 用户名密码是否正确
- 数据库用户是否有相应权限
- 防火墙是否放行数据库端口

### 4. 前端页面空白

- 清除浏览器缓存后重试
- 检查前端是否正确构建（frontend/dist 目录是否存在）
- 检查 Nginx/容器日志

---

## 端口说明

| 端口 | 用途 |
|------|------|
| 80 | 容器内部服务端口 |
| 8080 | 默认对外映射端口（可自定义） |

---

## 安全建议

1. **修改默认密码**: 首次登录后立即修改 admin 账号密码
2. **使用 HTTPS**: 生产环境建议配置 SSL 证书
3. **限制访问**: 通过防火墙限制访问来源 IP
4. **定期备份**: 建立数据库定期备份机制
5. **API Key 保护**: 不要将 API Key 提交到代码仓库

---

## 联系支持

如遇到部署问题，请检查：
1. 本文档的故障排查章节
2. Docker 和系统日志
3. 数据库连接状态

---

*文档版本: 1.0*
*最后更新: 2026-01-25*
