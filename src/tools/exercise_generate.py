from langchain_core.tools import tool

@tool
def add(a: float, b: float) -> float:
    """Return a + b."""
    return a + b