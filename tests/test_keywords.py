"""`parallel_solver_count` is the worker count of every `solve`; `num_workers` is its earlier name."""

import importlib
import inspect

import pytest

import external_solver
from external_solver._keywords import reads_num_workers

MODEL_CASES = [
    name
    for name in external_solver.__all__
    if name not in {"NoSolutionError", "order_picking", "pickup_delivery"}
]


@pytest.mark.parametrize("name", MODEL_CASES)
def test_every_solve_names_its_workers_like_the_engine(name: str) -> None:
    solve = importlib.import_module(f"external_solver.{name}").solve
    parameters = inspect.signature(solve).parameters
    assert parameters["parallel_solver_count"].default == 1
    assert parameters["parallel_solver_count"].kind is inspect.Parameter.KEYWORD_ONLY
    assert "num_workers" not in parameters


def test_the_earlier_name_is_read_and_both_are_refused() -> None:
    seen = []

    @reads_num_workers
    def solve(problem, *, parallel_solver_count: int = 1):
        seen.append((problem, parallel_solver_count))

    solve("p")
    solve("p", parallel_solver_count=2)
    solve("p", num_workers=3)
    assert seen == [("p", 1), ("p", 2), ("p", 3)]
    with pytest.raises(TypeError, match="parallel_solver_count and num_workers are the same keyword"):
        solve("p", num_workers=3, parallel_solver_count=3)
    assert list(inspect.signature(solve).parameters) == ["problem", "parallel_solver_count"]


def test_a_solve_reads_the_earlier_name() -> None:
    from optimaru import knapsack as engine

    from external_solver import knapsack

    problem = engine.models.KnapsackProblemModel.model_validate(
        {"capacity": 5, "items": [{"id": "a", "weight": 3, "value": 4}, {"id": "b", "weight": 4, "value": 5}]}
    )
    earlier = knapsack.solve(problem, time_limit_seconds=5, num_workers=1)
    now = knapsack.solve(problem, time_limit_seconds=5, parallel_solver_count=1)
    assert (earlier.score_hard, earlier.score_soft) == (now.score_hard, now.score_soft)
