"""The level-by-level solve: how its stages share the time limit.

The models here are tiny, so CP-SAT itself never runs short of time. A
stand-in solver scripts what a large model does (a long search before the
first solution, a search that goes on after it, a stage that returns nothing)
and leaves the solutions to CP-SAT.
"""

import threading
import time

import pytest

from external_solver._plugins import ConstraintSpec, ObjectiveBuilder
from ortools.sat.python import cp_model

SPECS = (
    ConstraintSpec("capacity", "Capacity", "hard", 1),
    ConstraintSpec("load", "Load", "medium", 1),
    ConstraintSpec("distance", "Distance", "soft", 1),
)

QUIET = "quiet"  # no solution for `seconds`, then CP-SAT's
BUSY = "busy"  # CP-SAT's solution at once, then a search that goes on until stopped or out of time
LOST = "lost"  # nothing: UNKNOWN


class ScriptedSolver:
    """A `CpSolver` whose solves follow ``script`` in time; a solve past the script is CP-SAT's own."""

    def __init__(self, *script: tuple[str, float]) -> None:
        self.inner = cp_model.CpSolver()
        self.script = list(script)
        self.limits: list[float] = []
        self.fixed_to_hints: list[bool] = []
        self.took: list[float] = []
        self._stop = threading.Event()

    @property
    def parameters(self):
        return self.inner.parameters

    @property
    def objective_value(self) -> float:
        return self.inner.objective_value

    def value(self, expression) -> int:
        return self.inner.value(expression)

    def stop_search(self) -> None:
        self._stop.set()
        self.inner.stop_search()

    def solve(self, model: cp_model.CpModel, callback=None) -> int:
        limit = self.inner.parameters.max_time_in_seconds
        self.limits.append(limit)
        self.fixed_to_hints.append(self.inner.parameters.fix_variables_to_their_hinted_value)
        kind, seconds = self.script.pop(0) if self.script else ("", 0.0)
        started = time.monotonic()
        self._stop.clear()
        try:
            if kind == LOST:
                return cp_model.UNKNOWN
            if kind == QUIET:
                if limit <= seconds:
                    time.sleep(limit)
                    return cp_model.UNKNOWN
                time.sleep(seconds)
            status = self.inner.solve(model, callback)
            if kind == BUSY:
                self._stop.wait(max(0.0, limit - (time.monotonic() - started)))
                return cp_model.FEASIBLE
            return status
        finally:
            self.took.append(time.monotonic() - started)


@pytest.fixture
def staged(monkeypatch):
    """A three-level objective that does not fold, over x (hard), y (medium) and z (soft)."""
    monkeypatch.setattr("external_solver._plugins.registry._FOLD_LIMIT", 1)
    model = cp_model.CpModel()
    x = model.new_int_var(1, 4, "x")
    y = model.new_int_var(2, 5, "y")
    z = model.new_int_var(3, 6, "z")
    objective = ObjectiveBuilder(model, ("hard", "medium", "soft"), SPECS, medium_fold="into_soft")
    objective.add("capacity", x, bound=4)
    objective.add("load", y, bound=5)
    objective.add("distance", z, bound=6)
    assert not objective.folds()
    return objective


def _limited(solver: ScriptedSolver, seconds: float) -> ScriptedSolver:
    solver.parameters.max_time_in_seconds = seconds
    return solver


def test_the_levels_are_minimized_one_after_another(staged) -> None:
    solver = _limited(ScriptedSolver(), 30.0)
    assert staged.solve(solver) == cp_model.OPTIMAL
    assert staged.score(solver) == {"hard": -1, "medium": -2, "soft": -3}
    assert len(solver.limits) == 3
    assert solver.parameters.max_time_in_seconds == 30.0


def test_a_first_level_without_a_solution_at_its_share_keeps_the_time_that_is_left(staged) -> None:
    """Three levels and 1.5 s: the share is 0.5 s, and the first solution comes after 0.7 s."""
    solver = _limited(ScriptedSolver((QUIET, 0.7)), 1.5)
    assert staged.solve(solver) in (cp_model.OPTIMAL, cp_model.FEASIBLE)
    # The first solve had the whole limit, not a third of it, and the two levels after it
    # shared what it left.
    assert solver.limits[0] == pytest.approx(1.5, abs=0.05)
    assert len(solver.limits) == 3
    assert solver.limits[1] < 0.5
    score = staged.score(solver)
    assert (score["medium"], score["soft"]) == (-2, -3)
    assert solver.parameters.max_time_in_seconds == 1.5


def test_a_first_level_with_a_solution_stops_at_its_share(staged) -> None:
    """Three levels and 3 s: the first level has a solution at once and gives up the search after 1 s."""
    solver = _limited(ScriptedSolver((BUSY, 0.0)), 3.0)
    assert staged.solve(solver) == cp_model.FEASIBLE
    assert 0.9 <= solver.took[0] < 2.5
    assert len(solver.limits) == 3
    score = staged.score(solver)
    assert (score["medium"], score["soft"]) == (-2, -3)


def test_no_solution_at_all_takes_the_whole_limit(staged) -> None:
    solver = _limited(ScriptedSolver((QUIET, 5.0)), 0.6)
    assert staged.solve(solver) == cp_model.UNKNOWN
    assert solver.limits == [pytest.approx(0.6, abs=0.05)]
    assert solver.took[0] >= 0.55
    assert solver.parameters.max_time_in_seconds == 0.6


def test_a_later_level_that_returns_nothing_leaves_the_incumbent(staged) -> None:
    solver = _limited(ScriptedSolver(("", 0.0), (LOST, 0.0)), 30.0)
    assert staged.solve(solver) == cp_model.FEASIBLE
    # The third solve puts the first level's solution back, with the whole limit to do it in.
    assert solver.fixed_to_hints == [False, False, True]
    assert solver.limits[2] == 30.0
    assert not solver.parameters.fix_variables_to_their_hinted_value
    assert staged.score(solver)["hard"] == -1


def test_an_incumbent_that_cannot_be_put_back_is_no_solution(staged) -> None:
    solver = _limited(ScriptedSolver(("", 0.0), (LOST, 0.0), (LOST, 0.0)), 30.0)
    assert staged.solve(solver) == cp_model.UNKNOWN
    assert not solver.parameters.fix_variables_to_their_hinted_value
    assert solver.parameters.max_time_in_seconds == 30.0


def test_a_level_with_no_time_left_is_not_solved(staged) -> None:
    """The first solution arrives when the limit has passed: it is the result, as it stands."""
    solver = _limited(ScriptedSolver((BUSY, 0.0)), 0.3)
    solver.stop_search = lambda: None  # a search that does not stop when it is told to
    assert staged.solve(solver) == cp_model.FEASIBLE
    assert len(solver.limits) == 1
    assert staged.score(solver)["hard"] == -1


def test_one_level_that_does_not_fold_is_one_plain_solve(monkeypatch) -> None:
    monkeypatch.setattr("external_solver._plugins.registry._FOLD_LIMIT", 1)
    model = cp_model.CpModel()
    x = model.new_int_var(1, 4, "x")
    objective = ObjectiveBuilder(model, ("hard", "soft"), SPECS[:1])
    objective.add("capacity", x, bound=4)
    solver = _limited(ScriptedSolver(), 30.0)
    assert objective.solve(solver) == cp_model.OPTIMAL
    assert solver.limits == [pytest.approx(30.0, abs=0.05)]
    assert objective.score(solver) == {"hard": -1, "soft": 0}
