from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import sys
import subprocess
from typing import List, Optional
from contextlib import asynccontextmanager

# 导入自定义模块
from config import (
    API_HOST,
    API_PORT,
    DEFAULT_SEARCH_LIMIT,
    DISABLED_ENGINES,
    ENABLED_ENGINES,
)
from crawler import WebCrawler
import logger

# 全局爬虫实例
crawler: Optional[WebCrawler] = None


# 请求模型定义
class SearchRequest(BaseModel):
    """搜索请求模型"""

    query: str = Field(..., description="搜索查询字符串")
    limit: int = Field(default=DEFAULT_SEARCH_LIMIT, description="返回结果数量限制")
    disabled_engines: str = Field(
        default=DISABLED_ENGINES, description="禁用的搜索引擎列表"
    )
    enabled_engines: str = Field(
        default=ENABLED_ENGINES, description="启用的搜索引擎列表"
    )

    class Config:
        schema_extra = {
            "example": {
                "query": "Python FastAPI教程",
                "limit": 10,
                "disabled_engines": DISABLED_ENGINES,
                "enabled_engines": ENABLED_ENGINES,
            }
        }


class CrawlRequest(BaseModel):
    """爬取请求模型"""

    urls: List[str] = Field(..., description="要爬取的URL列表")
    instruction: str = Field(..., description="爬取指令")

    class Config:
        schema_extra = {
            "example": {
                "urls": ["https://example.com"],
                "instruction": "提取网页主要内容",
            }
        }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan 事件处理"""
    global crawler

    logger.setup_logger("INFO")
    logger.info("aisearch 服务启动中...")

    try:
        # 安装浏览器
        logger.info("检查并安装 Playwright 浏览器...")
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
        )
        logger.info("Playwright 浏览器安装成功")

        # 初始化爬虫
        crawler = WebCrawler()
        await crawler.initialize()
        logger.info("爬虫初始化完成")

        logger.info(f"API服务运行在: http://{API_HOST}:{API_PORT}")
        logger.info("aisearch 服务启动完成")

        yield

        # 清理资源
        if crawler:
            await crawler.close()
            logger.info("爬虫资源已释放")
        logger.info("aisearch 服务已关闭")

    except subprocess.CalledProcessError as e:
        logger.error(f"浏览器安装失败: {e.stderr.decode()}")
        raise
    except Exception as e:
        logger.error(f"启动失败: {str(e)}")
        raise


# 初始化FastAPI应用
app = FastAPI(
    title="aisearch",
    description="Tavily compatible search service based on SearXNG and Crawl4AI",
    version="1.0.0",
    lifespan=lifespan,
)


async def crawl(request: CrawlRequest):
    """执行URL爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="爬虫未初始化")
    return await crawler.crawl_urls(request.urls, request.instruction)


@app.post("/search", response_model=dict)
async def search(request: SearchRequest):
    """搜索API端点"""
    try:
        logger.info(f"开始搜索: {request.query}")

        # 执行搜索
        response = await WebCrawler.make_searxng_request(
            query=request.query,
            limit=request.limit,
            disabled_engines=request.disabled_engines,
            enabled_engines=request.enabled_engines,
        )

        # 处理搜索结果
        results = response.get("results", [])
        if not results:
            logger.warning("未找到搜索结果")
            raise HTTPException(status_code=404, detail="未找到搜索结果")

        urls = [result["url"] for result in results[: request.limit] if "url" in result]
        if not urls:
            logger.warning("未找到有效的URL")
            raise HTTPException(status_code=404, detail="未找到有效的URL")

        logger.info(f"找到 {len(urls)} 个URL，开始爬取")
        return await crawl(CrawlRequest(urls=urls, instruction=request.query))

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索过程发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    logger.info("通过命令行启动aisearch服务")
    uvicorn.run(app, host=API_HOST, port=API_PORT)
