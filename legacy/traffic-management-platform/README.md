# Final Assignment Agent

一个面向交通违法处理场景的可部署全栈系统基线，包含 Spring Boot 后端、Flutter 客户端、容器化部署编排和生产环境运维文档。项目在原有业务系统基础上补齐了运行时配置、容器部署、反向代理和运维检查能力，更强调交付与部署落地。

## 项目概览

- 项目类型：可部署的全栈业务系统基线
- 业务方向：交通违法处理与后台管理
- 主要能力：后端业务接口、JWT 鉴权、实时通信、中间件集成、Flutter 客户端、容器化部署
- 适合阅读对象：HR 初筛、后端开发、全栈开发、交付工程与运维方向面试官

## 核心功能

- 用户认证、权限控制与业务数据管理
- 基于 Redis、Kafka、Elasticsearch 的中间件集成
- 支持 REST API、WebSocket 与 Vert.x 代理能力
- Flutter 客户端支持运行时注入服务端地址
- Docker Compose 提供本地和生产环境部署基线
- 配套生产部署、发布流程和运维检查文档

## 承担内容

- 完成后端业务基线、部署基线与客户端运行时配置改造
- 完成 Docker Compose 编排、Nginx 反向代理与生产覆盖层设计
- 完成 JWT、缓存、消息、检索和运行时健康检查链路整理
- 完成 Flutter 客户端与后端地址解耦，支持运行时注入配置
- 完成发布、部署、运维和冒烟检查文档沉淀

## 关键技术实现

- 使用 `Spring Boot 4 + MyBatis Plus + Spring Security` 构建主业务后端
- 使用 `Redis + Redpanda/Kafka + Elasticsearch` 提供缓存、消息和检索能力
- 使用 `Vert.x` 支撑代理与异步通信场景
- 使用 `Flyway` 管理数据库迁移
- 使用 `Docker Compose` 构建本地与生产环境部署基线
- 使用 `Nginx` 提供生产环境网关与 TLS 就绪入口
- Flutter 客户端通过 `--dart-define` 注入 API / WS 地址，不再依赖硬编码

## 技术栈

| 分层 | 技术方案 |
| --- | --- |
| 后端 | Spring Boot 4、Spring Security、MyBatis Plus、WebFlux、WebSocket、Vert.x |
| 数据与中间件 | MySQL、Redis、Redpanda/Kafka、Elasticsearch、Flyway |
| 客户端 | Flutter |
| 部署 | Docker Compose、Nginx |
| 运维 | Actuator、PowerShell smoke test、部署与发布 runbook |

## 仓库结构

```text
Final-Assignment-Agent
├─ backend/             # Spring Boot 后端
├─ flutter_app/         # Flutter 客户端
├─ docs/                # 生产部署、发布与运维文档
├─ ops/                 # 运维脚本与检查脚本
├─ compose.yaml         # 本地部署基线
├─ compose.prod.yaml    # 生产环境覆盖层
└─ README.md            # 项目说明
```

## 主要模块说明

### 1. Spring Boot 后端

主线业务模块，负责鉴权、业务接口、中间件集成和健康检查。

- 路径：`backend/`
- 技术关键词：`Spring Boot 4`、`JWT`、`MyBatis Plus`、`Redis`、`Kafka`、`Elasticsearch`
- 主要能力：
  - JWT Auth
  - 业务数据访问
  - Redis 缓存
  - Kafka / Redpanda 消息处理
  - Elasticsearch 检索
  - WebSocket / Vert.x 代理

### 2. Flutter 客户端

负责跨平台业务界面和运行时服务地址适配。

- 路径：`flutter_app/`
- 技术关键词：`Flutter`
- 主要能力：
  - 业务页面与管理界面
  - API / WS 地址运行时注入
  - 多端启动与发布构建

### 3. 容器化部署基线

负责本地启动、生产覆盖和网关入口。

- `compose.yaml`
  - MySQL
  - Redis
  - Redpanda
  - Elasticsearch
  - Backend
- `compose.prod.yaml`
  - Nginx reverse proxy
  - TLS-ready entrypoints

### 4. 文档与运维

用于支撑发布、部署和基础运维检查。

- 路径：`docs/`、`ops/`
- 相关文档：
  - `production-deployment.md`
  - `release-playbook.md`
  - `operations-runbook.md`

## 运行说明

### 环境准备

- JDK 25+
- Maven 3.9+
- Flutter 3+
- Docker

### 生产部署基线

1. 复制 `.env.example` 为 `.env`
2. 替换其中的密钥和本地默认地址
3. 提供满足长度要求的 Base64 JWT Secret
4. 构建并启动服务

```bash
docker compose build
docker compose up -d
```

如需启用网关与生产覆盖层：

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

### 健康检查

```bash
curl http://localhost:8080/actuator/health
curl http://localhost:8080/actuator/info
powershell -ExecutionPolicy Bypass -File .\ops\smoke-test.ps1
```

默认暴露端口：

- `8080`：Spring Boot REST API 与 Actuator
- `8081`：Vert.x 代理与 WebSocket / Event Bus
- `80/443`：生产覆盖层中的 Nginx 入口

## 客户端运行时配置

Flutter 客户端通过 `--dart-define` 注入运行时地址：

```bash
flutter run --dart-define=API_BASE_URL=http://localhost:8080 --dart-define=WS_BASE_URL=http://localhost:8081
```

发布构建示例：

```bash
flutter build windows --dart-define=API_BASE_URL=https://api.example.com --dart-define=WS_BASE_URL=https://ws.example.com
```

## 相关文档

- 后端说明：[backend/README.md](backend/README.md)
- 客户端说明：[flutter_app/README.md](flutter_app/README.md)
- 生产部署文档：[docs/production-deployment.md](docs/production-deployment.md)
- 发布流程文档：[docs/release-playbook.md](docs/release-playbook.md)
- 运维手册：[docs/operations-runbook.md](docs/operations-runbook.md)

