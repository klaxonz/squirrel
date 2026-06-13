import re


def parse_dynamic_sql(sql: str, params: dict) -> str:
    """Enhanced SQL parser with support for:
    1. /*{if field}*/ ... /*{endif}*/
    2. /*{if field == value}*/ ... /*{endif}*/ (supports boolean, numeric, string)
    """
    # Handle conditions with comparison operators
    compare_pattern = r'/\*\{if (\w+)\s*([=!<>]+)\s*([\'"]?)(.*?)\3\s*\}\*/(.*?)/\*\{endif}\*/'
    for match in re.finditer(compare_pattern, sql, re.DOTALL):
        field, operator, quote, value_str, content = match.groups()
        actual_value = params.get(field)

        # Type inference
        try:
            # Boolean handling
            if value_str.lower() in ["true", "false"]:
                value = value_str.lower() == "true"
            # Numeric handling
            elif "." in value_str:
                value = float(value_str)
            else:
                value = int(value_str)
        except (ValueError, AttributeError):
            # String handling
            value = value_str

        # Type-converted comparison
        condition_met = False
        try:
            if operator == "==":
                condition_met = actual_value == value
            elif operator == "!=":
                condition_met = actual_value != value
            elif operator == ">":
                condition_met = actual_value > value
            elif operator == "<":
                condition_met = actual_value < value
            elif operator == ">=":
                condition_met = actual_value >= value
            elif operator == "<=":
                condition_met = actual_value <= value
        except TypeError:
            # Treat type mismatch as condition not met
            condition_met = False

        sql = sql.replace(match.group(0), content if condition_met else "")

    # Handle basic existence check (supports boolean False)
    existence_pattern = r"/\*\{if (\w+)\}\*/(.*?)/\*\{endif}\*/"
    for match in re.finditer(existence_pattern, sql, re.DOTALL):
        field, content = match.groups()[0], match.groups()[1]
        actual_value = params.get(field)

        # Handle boolean False case
        if isinstance(actual_value, bool):
            condition_met = actual_value is True
        else:
            condition_met = actual_value not in (None, "")

        sql = sql.replace(match.group(0), content if condition_met else "")

    return sql.strip()
