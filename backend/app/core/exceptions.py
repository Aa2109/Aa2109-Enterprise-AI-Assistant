
from fastapi import status
# Base
class AppException(Exception):
    """Base class for all application exceptions."""

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code

# Custom Exceptions
class DocumentNotFoundException(AppException):
    """ Raised when a requested document is not found in the database. """
    def __init__(self, document_id: int):
        super().__init__(
            message=f"Document {document_id} not found.",
            error_code="DOCUMENT_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )