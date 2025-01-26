import re


def parse_dynamic_sql(sql: str, params: dict) -> str:
    """
    Parse SQL with conditional blocks
    
    Supports:
    /*{if field}*/ ... /*{endif}*/
    """

    def should_include_block(query_condition: str) -> bool:
        return params.get(query_condition) is not None and params.get(query_condition) != ''

    # Handle if conditions
    pattern = r'/\*\{if (\w+)\}\*/(.*?)/\*\{endif}\*/'
    while True:
        match = re.search(pattern, sql, re.DOTALL)
        if not match:
            break

        condition = match.group(1)
        content = match.group(2)

        if should_include_block(condition):
            sql = sql.replace(match.group(0), content)
        else:
            sql = sql.replace(match.group(0), '')

    return sql.strip()
