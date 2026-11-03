"""Errors shared by every use case. Importing this module does not import OR-Tools."""


class NoSolutionError(RuntimeError):
    """CP-SAT stopped without a solution: it proved the model infeasible, or the time ran out first.

    ``status`` is CP-SAT's status name (``"INFEASIBLE"``, ``"UNKNOWN"``, ``"MODEL_INVALID"``). It is a
    ``RuntimeError`` so callers that caught that before still do.
    """

    def __init__(self, status: str, what: str = "a solution") -> None:
        self.status = status
        super().__init__(f"CP-SAT did not find {what} (status={status})")

    @property
    def infeasible(self) -> bool:
        """True when CP-SAT proved that no solution exists, not merely that none was found in time."""
        return self.status == "INFEASIBLE"
