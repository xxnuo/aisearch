import os
from dotenv import load_dotenv
from logger import setup_logger
from utils import trim_slash
import const

VERSION = const.VERSION

# 配置日志
logger = setup_logger()

# 加载.env文件中的环境变量
load_dotenv()
logger.info("加载环境变量配置")


# SearXNG 配置
def get_searxng_server_config():
    """获取 SearXNG 相关配置"""
    api_base = os.getenv("SEARXNG_API_BASE")
    if api_base:
        api_base = trim_slash(api_base)
        url = "/".join(api_base.split("/")[:-1])
        path = api_base.split("/")[-1]
    else:
        url = trim_slash(os.getenv("SEARXNG_URL", "http://localhost:8080"))
        path = trim_slash(os.getenv("SEARXNG_PATH", "search"))
        api_base = f"{url}/{path}"
    return url, path, api_base


SEARXNG_URL, SEARXNG_PATH, SEARXNG_API_BASE = get_searxng_server_config()

# API 服务配置
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "3000"))

# 搜索引擎配置
SEARCH_RESULT_LIMIT = int(os.getenv("SEARCH_RESULT_LIMIT", "5"))

DEFAULT_DISABLED_ENGINES = (
    "wikipedia__general,currency__general,wikidata__general,duckduckgo__general,"
    "google__general,lingva__general,qwant__general,startpage__general,"
    "dictzone__general,mymemory translated__general,brave__general"
)
DISABLED_ENGINES = os.getenv("DISABLED_ENGINES", DEFAULT_DISABLED_ENGINES)
ENABLED_ENGINES = os.getenv("ENABLED_ENGINES", "baidu__general")

CONTENT_FILTER_THRESHOLD = float(os.getenv("CONTENT_FILTER_THRESHOLD", "0.6"))
WORD_COUNT_THRESHOLD = int(os.getenv("WORD_COUNT_THRESHOLD", "10"))
