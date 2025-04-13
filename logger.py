from loguru import logger
import sys
from typing import Optional, Any

# 配置默认日志格式
DEFAULT_LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"

# 移除默认处理器
logger.remove()

# 添加标志来跟踪是否已经设置了处理器
_handler_setup = False

def setup_logger(level: str = "INFO", log_format: Optional[str] = None) -> logger: # type: ignore
    """
    配置并返回应用程序日志记录器

    Args:
        level: 日志级别，可选值：TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL
        log_format: 日志格式，如果为None则使用默认格式

    Returns:
        logger: 配置好的日志记录器
    """
    global _handler_setup
    
    # 只有在未设置处理器时才添加
    if not _handler_setup:
        # 添加标准输出处理器
        logger.add(
            sys.stdout,
            format=log_format or DEFAULT_LOG_FORMAT,
            level=level.upper(),
            colorize=True,
        )
        _handler_setup = True

    return logger


# 默认设置日志记录器
setup_logger()


# 导出常用日志函数，方便直接调用
def debug(msg: str, *args, **kwargs) -> None:
    """记录DEBUG级别的日志"""
    logger.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs) -> None:
    """记录INFO级别的日志"""
    logger.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs) -> None:
    """记录WARNING级别的日志"""
    logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs) -> None:
    """记录ERROR级别的日志"""
    logger.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs) -> None:
    """记录CRITICAL级别的日志"""
    logger.critical(msg, *args, **kwargs)
