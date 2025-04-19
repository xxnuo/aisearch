from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import sys
import subprocess
from typing import List, Optional, Union, Dict
from contextlib import asynccontextmanager
import time
import asyncio

# 导入自定义模块
import config
from crawler import WebCrawler
import logger

# 全局爬虫实例
crawler: Optional[WebCrawler] = None

# 全局变量用于跟踪关闭状态
is_shutting_down = False
shutdown_event = None
active_connections: List[asyncio.Task] = []

def handle_shutdown_signal(signum, frame):
    """处理关闭信号"""
    global is_shutting_down
    
    if is_shutting_down:
        # 如果已经在关闭中，收到第二次信号则强制退出
        logger.warning("收到第二次关闭信号，强制退出...")
        sys.exit(1)
        
    logger.warning(f"收到关闭信号 {signum}, 开始优雅关闭...")
    is_shutting_down = True
    
    if shutdown_event:
        shutdown_event.set()


# 请求模型定义
class SearchRequest(BaseModel):
    """搜索请求模型 - 遵循Tavily API规范"""

    query: str = Field(..., description="搜索查询字符串")
    include_raw_content: bool = Field(default=False, description="是否包含原始HTML内容")
    topic: str = Field(default="general", description="搜索类别: general或news")
    search_depth: str = Field(default="basic", description="搜索深度: basic或advanced")
    chunks_per_source: int = Field(
        default=3, ge=1, le=3, description="每个源的内容块数量"
    )
    max_results: int = Field(
        default=config.SEARCH_RESULT_LIMIT, ge=0, le=20, description="最大返回结果数"
    )
    time_range: Optional[str] = Field(
        default=None, description="时间范围: day/week/month/year"
    )
    days: int = Field(default=7, ge=1, description="新闻搜索时的天数限制")
    include_answer: bool = Field(default=False, description="是否包含AI生成的答案")
    include_images: bool = Field(default=False, description="是否包含图片搜索结果")
    include_image_descriptions: bool = Field(
        default=False, description="是否包含图片描述"
    )
    include_domains: List[str] = Field(default=[], description="指定包含的域名列表")
    exclude_domains: List[str] = Field(default=[], description="指定排除的域名列表")

    class Config:
        schema_extra = {
            "example": {
                "query": "Python FastAPI教程",
                "max_results": config.SEARCH_RESULT_LIMIT,
            }
        }


class CrawlRequest(BaseModel):
    """爬取请求模型"""

    urls: List[str] = Field(..., description="要爬取的URL列表")

    class Config:
        schema_extra = {
            "example": {
                "urls": ["https://example.com"],
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


class ExtractRequest(BaseModel):
    """Tavily Extract API请求模型"""
    
    urls: Union[str, List[str]] = Field(..., description="要提取内容的URL或URL列表")
    include_images: bool = Field(default=False, description="是否包含图片")
    extract_depth: str = Field(
        default="basic",
        description="提取深度: basic或advanced",
        pattern="^(basic|advanced)$"
    )

    class Config:
        schema_extra = {
            "example": {
                "urls": "https://example.com",
                "include_images": False,
                "extract_depth": "basic"
            }
        }


class ExtractResult(BaseModel):
    """提取结果模型"""
    
    url: str
    raw_content: str
    images: List[str] = []


class ExtractResponse(BaseModel):
    """Tavily Extract API响应模型"""
    
    results: List[ExtractResult]
    failed_results: List[Dict[str, str]] = []
    response_time: float


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

        logger.info(f"API服务运行在: http://{config.API_HOST}:{config.API_PORT}")
        logger.info("aisearch 服务启动完成")

        yield

        # 清理资源
        logger.info("开始关闭服务...")
        if crawler:
            try:
                await crawler.close()
            except Exception:
                pass
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
    lifespan=lifespan,
)

@app.get("/health")
async def health():
    return {"status": "ok"}

async def crawl(request: CrawlRequest):
    """执行URL爬取"""
    if not crawler:
        raise HTTPException(status_code=500, detail="爬虫未初始化")
    return await crawler.crawl_urls(request.urls)


@app.post("/search", response_model=TavilySearchResponse)
async def search(request: SearchRequest):
    """搜索API端点"""
    if is_shutting_down:
        raise HTTPException(status_code=503, detail="服务正在关闭")

    # 创建并跟踪当前任务
    current_task = asyncio.current_task()
    if current_task:
        active_connections.append(current_task)

    try:
        start_time = time.time()
        logger.info(f"开始搜索: {request.query}")

        # 执行搜索
        response = await WebCrawler.make_searxng_request(
            query=request.query,
            limit=request.max_results,
            disabled_engines=config.DISABLED_ENGINES,
            enabled_engines=config.ENABLED_ENGINES,
            exclude_domains=request.exclude_domains,
            include_domains=request.include_domains,
            time_range=request.time_range,
            days=request.days,
        )

        # 处理搜索结果
        results = response.get("results", [])
        if not results:
            logger.warning("未找到搜索结果")
            raise HTTPException(status_code=404, detail="未找到搜索结果")

        urls = [
            result["url"]
            for result in results[: request.max_results]
            if "url" in result
        ]
        if not urls:
            logger.warning("未找到有效的URL")
            raise HTTPException(status_code=404, detail="未找到有效的URL")

        logger.info(f"找到 {len(urls)} 个URL，开始爬取")
        crawl_result = await crawl(CrawlRequest(urls=urls))

        # 构建Tavily格式的响应
        search_results = []
        for i, result in enumerate(results[: request.max_results]):
            search_result = SearchResult(
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", ""),
                score=1.0 - (i * 0.05),  # 简单的相关性评分
                raw_content=crawl_result.get("content")
                if request.include_raw_content
                else None,
            )
            search_results.append(search_result)

        response_time = f"{time.time() - start_time:.2f}"

        return TavilySearchResponse(
            query=request.query,
            answer=crawl_result.get("content")
            if request.include_answer
            else None,
            images=[],  # 暂不支持图片搜索
            results=search_results,
            response_time=response_time,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索过程发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理活跃连接列表
        if current_task and current_task in active_connections:
            active_connections.remove(current_task)
            logger.debug("已清理完成的搜索请求")


@app.post("/extract", response_model=ExtractResponse)
async def extract(request: ExtractRequest):
    """提取URL内容的API端点"""
    if is_shutting_down:
        raise HTTPException(status_code=503, detail="服务正在关闭")

    # 创建并跟踪当前任务
    current_task = asyncio.current_task()
    if current_task:
        active_connections.append(current_task)

    try:
        start_time = time.time()
        
        # 处理单个URL的情况
        urls = [request.urls] if isinstance(request.urls, str) else request.urls
        logger.info(f"开始提取内容: {', '.join(urls)}")

        # 执行内容提取
        crawl_result = await crawl(CrawlRequest(urls=urls))

        # 构建响应
        results = []
        for url in urls:
            if url not in crawl_result.get("failed_urls", []):
                result = ExtractResult(
                    url=url,
                    raw_content=crawl_result.get("content", ""),
                    images=[] if not request.include_images else []  # 暂不支持图片提取
                )
                results.append(result)

        # 处理失败的URL
        failed_results = [
            {"url": url, "error": "提取失败"}
            for url in crawl_result.get("failed_urls", [])
        ]

        response_time = time.time() - start_time

        return ExtractResponse(
            results=results,
            failed_results=failed_results,
            response_time=response_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"内容提取过程发生异常: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 清理活跃连接列表
        if current_task and current_task in active_connections:
            active_connections.remove(current_task)
            logger.debug("已清理完成的提取请求")
