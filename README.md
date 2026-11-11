# external-solver

Exact CP-SAT models for the [optimaru](https://github.com/optimaru/optimaru)
use cases. Each use case takes the same problem model and the same constraint
selection as its `optimaru` counterpart, and every result is rescored by the
engine's own `constraint_costs`, so a metaheuristic run and an exact run can be
compared score for score.

It is released on GitHub, not on PyPI. Install a release tag:

```sh
pip install "external-solver @ git+https://github.com/optimaru/external-solver@v0.2.2"
```

or, as a dependency in `pyproject.toml`:

```toml
dependencies = ["external-solver @ git+https://github.com/optimaru/external-solver@v0.2.2"]
```

```python
from optimaru import knapsack as engine
from optimaru.knapsack.models import KnapsackProblemModel
from external_solver import knapsack as exact

problem = KnapsackProblemModel.model_validate(data)
result = exact.solve(problem, time_limit_seconds=10, num_workers=8)
print(result.score_hard, result.score_soft)
```

## Use cases

Every subpackage is named like the `optimaru` subpackage it mirrors:

| Subpackage | Entry point |
| --- | --- |
| `assembly_line_balancing`, `bed_allocation`, `bin_packing`, `conference_scheduling`, `facility_location`, `flight_crew_scheduling`, `food_packaging`, `knapsack`, `maintenance_scheduling`, `max_cut`, `meeting_scheduling`, `project_job_scheduling`, `quadratic_assignment`, `semiconductor_scheduling`, `sports_league_scheduling`, `task_assigning`, `tournament_scheduling` | `solve(problem, *, time_limit_seconds=30.0, random_seed=0, num_workers=1, constraints=None)` |
| `employee_scheduling` | `solve(problem, *, time_limit_seconds=30.0, random_seed=0, num_workers=1)` and `solve_request(request)`, which returns the engine's `ScheduleSolution`; the rules are `problem.model_input.rules` |
| `order_picking` | `solve(...)` and `solve_request(request, ...)` |
| `pickup_delivery` | `solve_request(request, *, constraints=None, ...)` |

A `solve_request` reads the time limit, seed and worker count from the request,
like the engine's `solve_request`, and returns the same result model. Each
subpackage also has `catalog()`, the selectable constraints with their default level
and weight. `vehicle_routing` and `school_timetabling` have no model here yet.

## Constraint selection

`constraints` takes what the engine takes: the domain's constraint objects
(`optimaru.<case>.constraints`), names, or `{"name": ..., "weight": ...,
"level": ..., "offset": ..., "clip": ...}` mappings. `None` keeps the defaults;
a list replaces them. CP-SAT accepts only `exponent=1`, integral weights and
integral offsets, and some constraints are structural in a CP-SAT model, so
moving them to `level="soft"` is refused. Levels are optimized
lexicographically, hard first.

## Time limit

`time_limit_seconds` is CP-SAT's limit on the search; building the model comes
on top of it. When the score levels of a model do not fit one 64-bit objective
(that depends on the instance), they are minimized one after another, hard
first, and each level gets an equal share of the time that is left. A first
level that has no solution when its share ends keeps searching and stops at the
first solution it finds, so a solve ends without a solution only when the whole
limit passed without one. A later level that finds nothing in its share returns
the solution of the level before it.

## When there is no solution

A solve that ends without any solution raises `external_solver.NoSolutionError`
(a `RuntimeError`). Its `status` is CP-SAT's status name, and `infeasible` is
true only when CP-SAT proved that no solution exists; otherwise the time ran
out before a first solution was found.

## Versions

`external-solver 0.2.x` follows the `optimaru 0.4` constraint contract. The
models are the reference CP-SAT formulations kept in optimaru's `benchmarks/`
directory, packaged here so they can be installed next to the engine.

## Releasing

Bump `version` in `pyproject.toml` and merge it to `main`. The release workflow
checks that the package installs from source, tags the commit `v<version>` and
creates a GitHub release. Nothing is prebuilt; installing from the tag builds the
pure-Python package from source.

## Development

```sh
uv sync
uv run pytest -q
uv run ruff check src && uv run ruff format --check src
```
