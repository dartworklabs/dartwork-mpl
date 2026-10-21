"""Enhanced validation with auto-fix suggestions for agents.

Extends the base validation with actionable fixes that agents can apply.

Compatibility path: the implementation lives in the validate slice
(:mod:`dartwork_mpl.validate.fixes` and
:mod:`dartwork_mpl.validate.agent_requirements`). This module keeps the
public ``dartwork_mpl.validate_fixes`` path and ``dm.validate_fixes``.
"""

from __future__ import annotations

from .validate.agent_requirements import (
    check_agent_requirements,
    generate_validation_report,
)
from .validate.fixes import (
    FixHandler,
    get_fix_suggestions,
    register_fix,
    validate_with_fixes,
)

__all__ = [
    "FixHandler",
    "check_agent_requirements",
    "generate_validation_report",
    "get_fix_suggestions",
    "register_fix",
    "validate_with_fixes",
]
