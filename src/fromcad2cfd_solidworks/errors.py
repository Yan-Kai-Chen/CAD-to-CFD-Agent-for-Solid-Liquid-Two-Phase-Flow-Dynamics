class SolidWorksAgentError(RuntimeError):
    """Base error for controlled SolidWorks agent operations."""


class WorkspacePathError(SolidWorksAgentError):
    """Raised when an operation would read/write outside the allowed workspace."""


class SolidWorksConnectionError(SolidWorksAgentError):
    """Raised when SolidWorks COM connection fails."""


class SolidWorksOperationError(SolidWorksAgentError):
    """Raised when a SolidWorks operation fails."""

