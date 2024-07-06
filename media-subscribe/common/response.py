def success(data=None):
    return {
        'code': 0,
        'msg': 'success',
        'data': data
    }


def error(code, msg):
    return {
        'code': code,
        'msg': msg
    }
