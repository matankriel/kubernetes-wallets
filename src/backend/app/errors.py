class InfraHubError(Exception):
    status_code: int = 500
    code = "INTERNAL_ERROR"
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str = ""):
        super().__init__(message)
        self.message = message


class NotFoundError(InfraHubError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    code = "NOT_FOUND"


class UnauthorizedError(InfraHubError):
    """Raised when authentication is missing or invalid."""

    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(InfraHubError):
    """Raised when the user lacks permission for the action."""

    status_code = 403
    code = "FORBIDDEN"


class QuotaExceededError(InfraHubError):
    """Raised when quota would exceed the configured limit."""

    status_code = 409
    code = "QUOTA_EXCEEDED"


class ConflictError(InfraHubError):
    """Raised when a resource already exists or a conflict occurs."""

    status_code = 409
    code = "CONFLICT"


class ValidationError(InfraHubError):
    """Raised when input data fails business-level validation."""

    status_code = 422
    code = "VALIDATION_ERROR"
