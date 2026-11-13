"""Typed failures consumed by services instead of Qt widgets."""


class ApiError(RuntimeError):
    """Failure while communicating with Firebase or the REST API."""
    def __init__(self, status: int | None, data: object = None) -> None:
        super().__init__(f"{status}: {data}")
        self.status = status
        self.data = data


class ApiNotConfiguredError(ApiError):
    """Raised when a service needs an API URL that is not configured."""


class ApiRequestError(ApiError):
    """Raised for transport or HTTP errors returned by the API."""
