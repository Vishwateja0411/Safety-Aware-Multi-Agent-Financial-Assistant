from src.portfolio_health import run as run_portfolio_health
from src.schemas import ClassificationResult


def dispatch(classification: ClassificationResult, user_context: dict | None = None, llm=None) -> dict:
    if classification.agent == "portfolio_health":
        return run_portfolio_health(user_context or {}, llm=llm)

    return {
        "intent": classification.intent,
        "agent": classification.agent,
        "entities": classification.entities,
        "message": (
            f"The {classification.agent} agent is not implemented in this MVP. "
            "The router still classified and dispatched the request successfully."
        ),
    }
