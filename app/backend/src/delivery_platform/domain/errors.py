class InvalidOrderTransition(Exception):
    """Raised when an order is asked to move to an invalid state."""


class DemoScenarioError(Exception):
    """Raised when a deterministic demo command cannot be applied."""
