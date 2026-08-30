import pytest
from delivery_platform.routing.models import RouteProblem


def test_route_problem_rejects_non_square_cost_matrix():
    with pytest.raises(ValueError, match="square"):
        RouteProblem(
            labels=("A", "B"),
            costs=((0, 1, 2), (1, 0, 3)),
        )


def test_route_problem_defaults_origin_to_zero():
    problem = RouteProblem(labels=("A", "B"), costs=((0, 4), (4, 0)))

    assert problem.origin_index == 0


def test_route_problem_rejects_fewer_than_two_labels():
    with pytest.raises(ValueError, match="at least two"):
        RouteProblem(labels=("A",), costs=((0,),))


def test_route_problem_rejects_label_and_matrix_dimension_mismatch():
    with pytest.raises(ValueError, match="label count"):
        RouteProblem(labels=("A", "B"), costs=((0, 1), (1, 0), (2, 2)))


@pytest.mark.parametrize("origin_index", (0.5, True, -1, 2))
def test_route_problem_rejects_invalid_origin_index(origin_index: float | bool):
    with pytest.raises(ValueError, match="origin_index"):
        RouteProblem(labels=("A", "B"), costs=((0, 1), (1, 0)), origin_index=origin_index)


@pytest.mark.parametrize(
    "costs",
    (
        None,
        ((0, 1), object()),
    ),
)
def test_route_problem_normalizes_malformed_matrix_structures_to_value_error(costs: object):
    with pytest.raises(ValueError):
        RouteProblem(labels=("A", "B"), costs=costs)  # type: ignore[arg-type]


@pytest.mark.parametrize("cost", (-1, float("inf"), float("nan"), "invalid"))
def test_route_problem_rejects_invalid_cost_values(cost: float | str):
    with pytest.raises(ValueError):
        RouteProblem(labels=("A", "B"), costs=((0, cost), (1, 0)))  # type: ignore[arg-type]


def test_route_problem_normalizes_mutable_inputs_to_immutable_tuples():
    labels = ["A", "B"]
    costs = [[0, 4], [4, 0]]

    problem = RouteProblem(labels=labels, costs=costs)  # type: ignore[arg-type]
    labels[0] = "changed"
    costs[0][1] = 99

    assert problem.labels == ("A", "B")
    assert problem.costs == ((0, 4), (4, 0))
    assert isinstance(problem.labels, tuple)
    assert all(isinstance(row, tuple) for row in problem.costs)
