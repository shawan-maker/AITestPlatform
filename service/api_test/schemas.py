"""Re-export commonly used schemas."""

from service.api_test.case.schemas import CaseOut, PaginatedCases
from service.api_test.interface.schemas import InterfaceOut, PaginatedInterfaces

__all__ = [
    "InterfaceOut",
    "PaginatedInterfaces",
    "CaseOut",
    "PaginatedCases",
]
