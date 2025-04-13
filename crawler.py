from typing import List, Dict, Any
import urllib
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
)
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
import markdown
from bs4 import BeautifulSoup
import re
import json
from fastapi import HTTPException
import aiohttp

# 导入配置和日志模块
from config import (
    SEARXNG_API_BASE,
    DISABLED_ENGINES,
    ENABLED_ENGINES,
    CONTENT_FILTER_THRESHOLD,
    WORD_COUNT_THRESHOLD,
)
import logger


class WebCrawler:
    """网页爬虫类,封装了网页爬取和内容处理的功能"""

    def __init__(self):
        """初始化爬虫实例"""
        self.crawler = None
        logger.info("初始化WebCrawler实例")

    async def initialize(self) -> None:
        """初始化AsyncWebCrawler实例"""
        browser_config = BrowserConfig(headless=True, verbose=True)
        self.crawler = await AsyncWebCrawler(config=browser_config).__aenter__()
        logger.info("AsyncWebCrawler初始化完成")

    async def close(self) -> None:
        """关闭爬虫实例,释放资源"""
        if self.crawler:
            await self.crawler.__aexit__(None, None, None)
            logger.info("AsyncWebCrawler已关闭")

    @staticmethod
    def markdown_to_text_regex(markdown_str: str) -> str:
        """使用正则表达式将Markdown文本转换为纯文本"""
        # 移除标题符号
        text = re.sub(r"#+\s*", "", markdown_str)
        # 移除链接和图片
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        # 移除强调符号
        text = re.sub(r"(\*\*|__)(.*?)\1", r"\2", text)
        text = re.sub(r"(\*|_)(.*?)\1", r"\2", text)
        # 移除列表符号
        text = re.sub(r"^[\*\-\+]\s*", "", text, flags=re.MULTILINE)
        # 移除代码块
        text = re.sub(r"`{3}.*?`{3}", "", text, flags=re.DOTALL)
        text = re.sub(r"`(.*?)`", r"\1", text)
        # 移除引用块
        text = re.sub(r"^>\s*", "", text, flags=re.MULTILINE)
        return text.strip()

    @staticmethod
    def markdown_to_text(markdown_str: str) -> str:
        """使用 Markdown 和 BeautifulSoup 库将 Markdown 文本转换为纯文本"""
        html = markdown.markdown(markdown_str, extensions=["fenced_code"])
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")
        return "\n".join([line.strip() for line in text.split("\n") if line.strip()])

    @staticmethod
    async def make_searxng_request(
        query: str,
        limit: int = 10,
        disabled_engines: str = DISABLED_ENGINES,
        enabled_engines: str = ENABLED_ENGINES,
    ) -> dict:
        """向SearXNG发送搜索请求"""
        try:
            # 构建请求参数
            params = {
                "q": query,
                "format": "json",
                "language": "zh",
                "time_range": "week",
                "safesearch": "2", 
                "pageno": "1",
                "category_general": "1"
            }

            headers = {
                "Cookie": f"disabled_engines={disabled_engines};enabled_engines={enabled_engines};method=POST",
                "User-Agent": "aisearch/1.0.0",
            }

            logger.info(f"向SearXNG发送搜索请求: {query}")
            
            async with aiohttp.ClientSession() as session:
                url = f"{SEARXNG_API_BASE}"
                async with session.post(url, data=params, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP请求失败: {response.status}")
                    return await response.json()

        except Exception as e:
            logger.error(f"SearXNG请求失败: {str(e)}")
            raise Exception(f"搜索请求失败: {str(e)}")

    async def crawl_urls(self, urls: List[str], instruction: str) -> Dict[str, Any]:
        """爬取多个URL并处理内容"""
        try:
            if not self.crawler:
                logger.warning("爬虫未初始化,正在自动初始化")
                await self.initialize()

            md_generator = DefaultMarkdownGenerator(
                content_filter=PruningContentFilter(threshold=CONTENT_FILTER_THRESHOLD),
                options={
                    "ignore_links": True,
                    "ignore_images": True,
                    "escape_html": False,
                },
            )

            run_config = CrawlerRunConfig(
                word_count_threshold=WORD_COUNT_THRESHOLD,
                exclude_external_links=True,
                remove_overlay_elements=True,
                excluded_tags=["img", "header", "footer", "iframe", "nav"],
                process_iframes=True,
                markdown_generator=md_generator,
                cache_mode=CacheMode.BYPASS,  # 不使用缓存
            )

            logger.info(f"开始爬取URLs: {', '.join(urls)}")

            # 第一轮爬取
            results = await self.crawler.arun_many(urls=urls, config=run_config)
            all_results = []
            retry_urls = []
            failed_urls = []

            for i, result in enumerate(results):
                if self._is_valid_result(result):
                    all_results.append(result.markdown.fit_markdown + "\n\n")
                    logger.info(f"成功爬取URL: {urls[i]}")
                else:
                    retry_urls.append(urls[i])
                    logger.debug(f"URL需要重试: {urls[i]}")

            # 第二轮重试
            if retry_urls:
                logger.info(f"重试失败的URLs: {', '.join(retry_urls)}")
                retry_results = await self.crawler.arun_many(
                    urls=retry_urls, config=run_config
                )

                for i, result in enumerate(retry_results):
                    if self._is_valid_result(result):
                        all_results.append(result.markdown.fit_markdown + "\n\n")
                        logger.info(f"重试成功爬取URL: {retry_urls[i]}")
                    else:
                        failed_urls.append(retry_urls[i])
                        logger.debug(f"URL最终失败: {retry_urls[i]}")

            if not all_results:
                logger.error("所有URL爬取均失败")
                raise HTTPException(status_code=500, detail="所有URL爬取均失败")

            combined_content = "\n\n==========\n\n".join(all_results)
            plain_text = self.markdown_to_text_regex(
                self.markdown_to_text(combined_content)
            )

            response = {
                "content": plain_text,
                "success_count": len(all_results),
                "failed_urls": failed_urls,
            }

            logger.info(f"爬取完成,成功: {len(all_results)},失败: {len(failed_urls)}")
            return response

        except Exception as e:
            logger.error(f"爬取过程发生异常: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    def _is_valid_result(self, result) -> bool:
        """检查爬取结果是否有效"""
        return (
            result is not None
            and hasattr(result, "success")
            and result.success
            and hasattr(result, "markdown")
            and hasattr(result.markdown, "fit_markdown")
        )
