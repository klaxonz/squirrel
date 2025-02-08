import re


def parse_dynamic_sql(sql: str, params: dict) -> str:
    """
    增强版SQL解析器，支持：
    1. /*{if field}*/ ... /*{endif}*/
    2. /*{if field == value}*/ ... /*{endif}*/ (支持布尔值、数字、字符串)
    """
    # 处理带比较操作的条件
    compare_pattern = r'/\*\{if (\w+)\s*([=!<>]+)\s*([\'"]?)(.*?)\3\s*\}\*/(.*?)/\*\{endif}\*/'
    for match in re.finditer(compare_pattern, sql, re.DOTALL):
        field, operator, quote, value_str, content = match.groups()
        actual_value = params.get(field)
        
        # 类型推断
        try:
            # 布尔值处理
            if value_str.lower() in ['true', 'false']:
                value = value_str.lower() == 'true'
            # 数字处理
            elif '.' in value_str:
                value = float(value_str)
            else:
                value = int(value_str)
        except (ValueError, AttributeError):
            # 字符串处理
            value = value_str

        # 类型转换后的比较
        condition_met = False
        try:
            if operator == '==':
                condition_met = actual_value == value
            elif operator == '!=':
                condition_met = actual_value != value
            elif operator == '>':
                condition_met = actual_value > value
            elif operator == '<':
                condition_met = actual_value < value
            elif operator == '>=':
                condition_met = actual_value >= value
            elif operator == '<=':
                condition_met = actual_value <= value
        except TypeError:
            # 类型不匹配时视为条件不满足
            condition_met = False
        
        sql = sql.replace(match.group(0), content if condition_met else '')

    # 处理原始存在性检查（支持布尔值False）
    existence_pattern = r'/\*\{if (\w+)\}\*/(.*?)/\*\{endif}\*/'
    for match in re.finditer(existence_pattern, sql, re.DOTALL):
        field, content = match.groups()[0], match.groups()[1]
        actual_value = params.get(field)
        
        # 处理布尔值False的情况
        if isinstance(actual_value, bool):
            condition_met = actual_value is True
        else:
            condition_met = actual_value not in (None, '')
        
        sql = sql.replace(match.group(0), content if condition_met else '')

    return sql.strip()
