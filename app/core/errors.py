"""Application errors mapped to HTTP responses by the API layer."""


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class QuotaExceeded(AppError):
    def __init__(self, message: str = "Provider quota exceeded"):
        super().__init__(message, 429)


class ProviderDenied(AppError):
    def __init__(self, message: str = "You do not have access to this provider"):
        super().__init__(message, 403)
