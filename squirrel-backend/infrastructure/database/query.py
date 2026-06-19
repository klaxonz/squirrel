"""SQL 查询工具函数。"""


def escape_ilike(term: str) -> str:
    """转义 ILIKE 模式中的特殊字符(反斜杠、%、_),避免用户输入干扰模式匹配。"""
    return term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
