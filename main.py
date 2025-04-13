from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn
import sys
import subprocess
from typing import List, Optional, Dict, Any, Union
from contextlib import asynccontextmanager
import time

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
    """搜索请求模型 - 遵循Tavily API规范"""
    query: str = Field(..., description="搜索查询字符串")
    topic: str = Field(default="general", description="搜索类别: general或news")
    search_depth: str = Field(default="basic", description="搜索深度: basic或advanced")
    chunks_per_source: int = Field(default=3, ge=1, le=3, description="每个源的内容块数量")
    max_results: int = Field(default=5, ge=0, le=20, description="最大返回结果数")
    time_range: Optional[str] = Field(default=None, description="时间范围: day/week/month/year")
    days: int = Field(default=7, ge=1, description="新闻搜索时的天数限制")
    include_answer: bool = Field(default=False, description="是否包含AI生成的答案")
    include_raw_content: bool = Field(default=False, description="是否包含原始HTML内容")
    include_images: bool = Field(default=False, description="是否包含图片搜索结果")
    include_image_descriptions: bool = Field(default=False, description="是否包含图片描述")
    include_domains: List[str] = Field(default=[], description="指定包含的域名列表")
    exclude_domains: List[str] = Field(default=[], description="指定排除的域名列表")

    class Config:
        schema_extra = {
            "example": {
                "query": "Python FastAPI教程",
                "topic": "general",
                "search_depth": "basic",
                "max_results": 5,
                "include_answer": True
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


class ImageResult(BaseModel):
    """图片搜索结果模型"""
    url: str
    description: Optional[str] = None


class SearchResult(BaseModel):
    """搜索结果项模型"""
    title: str
    url: str
    content: str
    score: float
    raw_content: Optional[str] = None


class TavilySearchResponse(BaseModel):
    """Tavily API响应模型"""
    query: str
    answer: Optional[str] = None
    images: List[ImageResult] = []
    results: List[SearchResult] = []
    response_time: str


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


@app.post("/search", response_model=TavilySearchResponse)
async def search(request: SearchRequest):
    """搜索API端点"""
    try:
        start_time = time.time()
        logger.info(f"开始搜索: {request.query}")

        # 执行搜索
        response = await WebCrawler.make_searxng_request(
            query=request.query,
            limit=request.max_results,
            disabled_engines=DISABLED_ENGINES,
            enabled_engines=ENABLED_ENGINES,
        )

        # 处理搜索结果
        results = response.get("results", [])
        if not results:
            logger.warning("未找到搜索结果")
            raise HTTPException(status_code=404, detail="未找到搜索结果")

        urls = [result["url"] for result in results[:request.max_results] if "url" in result]
        if not urls:
            logger.warning("未找到有效的URL")
            raise HTTPException(status_code=404, detail="未找到有效的URL")

        logger.info(f"找到 {len(urls)} 个URL，开始爬取")
        crawl_result = await crawl(CrawlRequest(urls=urls, instruction=request.query))

        # 构建Tavily格式的响应
        search_results = []
        for i, result in enumerate(results[:request.max_results]):
            search_result = SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", ""),
                score=0.8 - (i * 0.05),  # 简单的相关性评分
                raw_content=crawl_result.get("content") if request.include_raw_content else None
            )
            search_results.append(search_result)

        response_time = f"{time.time() - start_time:.2f}"
        
        return TavilySearchResponse(
            query=request.query,
            answer=crawl_result.get("content")[:500] if request.include_answer else None,
            images=[],  # 暂不支持图片搜索
            results=search_results,
            response_time=response_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索过程发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    logger.info("通过命令行启动aisearch服务")
    uvicorn.run(app, host=API_HOST, port=API_PORT)
