"""InfraHub domain error hierarchy.

All service-layer errors inherit from InfraHubError. The global exception
handler in main.py converts these to structured JSON responses with the
correct HTTP status code and a request_id for traceability.
"""


class InfraHubError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = "") -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(InfraHubError):
    status_code = 404
    code = "NOT_FOUND"


class UnauthorizedError(InfraHubError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(InfraHubError):
    status_code = 403
    code = "FORBIDDEN"


class QuotaExceededError(InfraHubError):
    status_code = 409
    code = "QUOTA_EXCEEDED"


class ConflictError(InfraHubError):
    status_code = 409
    code = "CONFLICT"


class ValidationError(InfraHubError):
    status_code = 422
    code = "VALIDATION_ERROR"
