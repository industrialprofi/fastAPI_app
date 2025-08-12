"""Custom exception classes for the application"""


class RateLimitException(Exception):
    """Base class for rate limit exceptions"""

    def __init__(self, message: str, limit_type: str = None):
        self.message = message
        self.limit_type = limit_type
        super().__init__(self.message)


class DailyLimitExceededException(RateLimitException):
    """Raised when daily request limit is exceeded"""

    def __init__(self, requests_per_day: int):
        message = f"Daily limit exceeded. Plan allows {requests_per_day} requests per day."
        super().__init__(message, "daily")
        self.requests_per_day = requests_per_day


class MinuteLimitExceededException(RateLimitException):
    """Raised when per-minute request limit is exceeded"""

    def __init__(self, requests_per_minute: int):
        message = f"Rate limit exceeded. Plan allows {requests_per_minute} requests per minute."
        super().__init__(message, "minute")
        self.requests_per_minute = requests_per_minute


class NoActiveSubscriptionException(Exception):
    """Raised when user has no active subscription"""

    def __init__(self, message: str = "No active subscription found"):
        self.message = message
        super().__init__(self.message)


# Authentication-related exceptions
class AuthenticationException(Exception):
    """Base class for authentication exceptions"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class EmailNotVerifiedException(AuthenticationException):
    """Raised when user's email is not verified"""

    def __init__(self, message: str = "Email not verified. Please check your email for verification link."):
        super().__init__(message)


class InvalidCredentialsException(AuthenticationException):
    """Raised when credentials are invalid or cannot be validated"""

    def __init__(self, message: str = "Could not validate credentials"):
        super().__init__(message)
