

class ProxyException(Exception):
    """代理异常基类"""

    def __init__(self, message: str, domain: str | None = None, status_code: int = 500):
        self.message = message
        self.domain = domain
        self.status_code = status_code
        super().__init__(self.message)


class UnsupportedDomainException(ProxyException):
    """不支持的域名异常"""

    def __init__(self, domain: str):
        super().__init__(
            message=f"不支持的域名: {domain}",
            domain=domain,
            status_code=400,
        )


class ProxyTimeoutException(ProxyException):
    """代理超时异常"""

    def __init__(self, domain: str, timeout: float):
        super().__init__(
            message=f"代理请求超时: {domain} (timeout: {timeout}s)",
            domain=domain,
            status_code=504,
        )


class ProxyNetworkException(ProxyException):
    """代理网络异常"""

    def __init__(self, domain: str, original_error: str):
        super().__init__(
            message=f"代理网络错误: {domain} - {original_error}",
            domain=domain,
            status_code=502,
        )


class ProxyConfigurationException(ProxyException):
    """代理配置异常"""

    def __init__(self, domain: str, config_error: str):
        super().__init__(
            message=f"代理配置错误: {domain} - {config_error}",
            domain=domain,
            status_code=500,
        )
