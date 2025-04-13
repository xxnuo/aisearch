import os
from dotenv import load_dotenv
from logger import setup_logger
from utils import trim_slash

# 配置日志
logger = setup_logger()

# 加载.env文件中的环境变量
load_dotenv()
logger.info("加载环境变量配置")


# SearXNG 配置
def get_searxng_config():
    """获取 SearXNG 相关配置"""
    api_base = os.getenv("SEARXNG_API_BASE")
    if api_base:
        api_base = trim_slash(api_base)
        url = api_base.split("/")[2]
        path = "/".join(api_base.split("/")[3:])
    else:
        url = trim_slash(os.getenv("SEARXNG_URL", "http://localhost:8080"))
        path = trim_slash(os.getenv("SEARXNG_PATH", "search"))
        api_base = f"{url}/{path}"
    return url, path, api_base


SEARXNG_URL, SEARXNG_PATH, SEARXNG_API_BASE = get_searxng_config()

# API 服务配置
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "3000"))

# 爬虫配置
DEFAULT_SEARCH_LIMIT = int(os.getenv("DEFAULT_SEARCH_LIMIT", "10"))
CONTENT_FILTER_THRESHOLD = float(os.getenv("CONTENT_FILTER_THRESHOLD", "0.6"))
WORD_COUNT_THRESHOLD = int(os.getenv("WORD_COUNT_THRESHOLD", "10"))

# 搜索引擎配置
DEFAULT_DISABLED_ENGINES = (
    "wikipedia__general,currency__general,wikidata__general,duckduckgo__general,"
    "google__general,lingva__general,qwant__general,startpage__general,"
    "dictzone__general,mymemory translated__general,brave__general"
)
DISABLED_ENGINES = os.getenv("DISABLED_ENGINES", DEFAULT_DISABLED_ENGINES)
ENABLED_ENGINES = os.getenv("ENABLED_ENGINES", "baidu__general")

# 配置类型定义
CONFIG_SCHEMA = {
    "searxng": {"url": str, "path": str, "api_base": str},
    "api": {"host": str, "port": int},
    "crawler": {
        "default_search_limit": int,
        "content_filter_threshold": float,
        "word_count_threshold": int,
    },
    "search_engines": {"disabled": str, "enabled": str},
}


def get_config_info() -> dict:
    """返回当前配置信息的字典

    Returns:
        dict: 包含所有配置参数的字典，结构符合CONFIG_SCHEMA定义
    """
    return {
        "searxng": {
            "url": SEARXNG_URL,
            "path": SEARXNG_PATH,
            "api_base": SEARXNG_API_BASE,
        },
        "api": {"host": API_HOST, "port": API_PORT},
        "crawler": {
            "default_search_limit": DEFAULT_SEARCH_LIMIT,
            "content_filter_threshold": CONTENT_FILTER_THRESHOLD,
            "word_count_threshold": WORD_COUNT_THRESHOLD,
        },
        "search_engines": {"disabled": DISABLED_ENGINES, "enabled": ENABLED_ENGINES},
    }
