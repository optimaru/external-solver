"""external_solver — exact CP-SAT models for the optimaru use cases.

Every use case is a subpackage named like its ``optimaru`` counterpart and
takes the same problem model and constraint selection::

    from optimaru.knapsack.models import KnapsackProblemModel
    from external_solver import knapsack

    result = knapsack.solve(problem, time_limit_seconds=10)

Subpackages load on first access, so importing ``external_solver`` does not
import OR-Tools or any engine domain.
"""

import importlib
from importlib.metadata import PackageNotFoundError, version

from .errors import NoSolutionError

try:
    __version__ = version("external-solver")
except PackageNotFoundError:  # running from a source tree
    __version__ = "0.0.0"

__all__ = [
    "NoSolutionError",
    "assembly_line_balancing",
    "bed_allocation",
    "bin_packing",
    "conference_scheduling",
    "employee_scheduling",
    "facility_location",
    "flight_crew_scheduling",
    "food_packaging",
    "knapsack",
    "maintenance_scheduling",
    "max_cut",
    "meeting_scheduling",
    "order_picking",
    "pickup_delivery",
    "project_job_scheduling",
    "quadratic_assignment",
    "semiconductor_scheduling",
    "sports_league_scheduling",
    "task_assigning",
    "tournament_scheduling",
]


def __getattr__(name):
    if name in __all__ and name != "NoSolutionError":
        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
