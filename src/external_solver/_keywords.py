"""The earlier name of a ``solve`` keyword. Importing this module does not import OR-Tools."""

import functools


def reads_num_workers(solve):
    """Let ``solve`` take ``num_workers``, the name ``parallel_solver_count`` had up to 0.2.

    The keyword is the number of CP-SAT search workers, under the name the engine's ``solve``
    and its request models give their count of parallel starts (optimaru 0.5). The earlier
    name is read the way the engine reads a request's: either name works, both together are
    refused. The signature shows the new name only.
    """

    @functools.wraps(solve)
    def wrapper(*args, **keywords):
        if "num_workers" in keywords:
            if "parallel_solver_count" in keywords:
                raise TypeError("parallel_solver_count and num_workers are the same keyword: give one")
            keywords["parallel_solver_count"] = keywords.pop("num_workers")
        return solve(*args, **keywords)

    return wrapper
