# AiSearch

AiSearch 是一个强大的智能搜索服务，它结合了 SearXNG 搜索引擎和高级网页爬虫功能，提供了类似 Tavily API 的搜索体验。该服务能够进行精确的网页内容提取、智能搜索结果聚合，并支持多种高级搜索特性。

## 🌟 主要特性

- 🔍 **智能搜索**
  - 支持通用搜索和新闻搜索
  - 可配置搜索深度和结果数量
  - 支持时间范围过滤
  - 域名包含/排除过滤
  - 多搜索引擎结果聚合

- 🕷️ **高级网页爬虫**
  - 智能内容提取
  - 自动内容过滤和优化
  - 支持批量URL处理
  - 自动重试机制
  - Markdown 格式化输出

- 🛠️ **API 兼容性**
  - 完全兼容 Tavily API 规范
  - RESTful API 设计
  - 支持异步处理
  - 优雅的错误处理

## 📦 安装要求

- Docker
- SearXNG 实例

## 🚀 快速开始

```bash
# API 服务配置
API_HOST=0.0.0.0
API_PORT=3000

# SearXNG 配置
SEARXNG_URL=http://localhost:8080

# 搜索配置
SEARCH_RESULT_LIMIT=5
```

## 📚 API 使用说明

完全兼容 Tavily, 查看 [官方文档](https://docs.tavily.com/documentation/api-reference/endpoint/search) 

简要说明：

### 搜索 API

```http
POST /search
Content-Type: application/json

{
    "query": "搜索关键词",
    "max_results": 5
}
```

### 内容提取 API

```http
POST /extract
Content-Type: application/json

{
    "urls": ["https://example.com"],
}
```

### 构建和运行

```bash
# 构建镜像
docker build -t aisearch .

# 使用 docker-compose 运行
docker-compose up -d
```