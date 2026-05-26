"""Re-export ORM models for Tortoise and backward-compatible imports."""

from service.functional_test.case.models import (
    FunctionalCase,
    FunctionalCaseCatalog,
    FunctionalTestPoint,
)
from service.functional_test.requirement.models import RequirementCandidate, RequirementDoc

__all__ = [
    "RequirementCandidate",
    "RequirementDoc",
    "FunctionalCaseCatalog",
    "FunctionalTestPoint",
    "FunctionalCase",
]
