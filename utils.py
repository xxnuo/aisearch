def trim_slash(url: str) -> str:
    """
    去除URL中的首尾斜杠
    """
    return url.rstrip("/").lstrip("/")
