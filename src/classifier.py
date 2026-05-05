import re
from typing import Any

from src.schemas import ClassificationResult


AGENTS = {
    "portfolio_health",
    "portfolio_query",
    "market_research",
    "investment_strategy",
    "financial_planning",
    "financial_calculator",
    "risk_assessment",
    "product_recommendation",
    "predictive_analysis",
    "customer_support",
    "general_query",
}


COMPANY_TICKERS = {
    "apple": "AAPL",
    "aapl": "AAPL",
    "microsoft": "MSFT",
    "microsfot": "MSFT",
    "msft": "MSFT",
    "nvidia": "NVDA",
    "nvda": "NVDA",
    "tesla": "TSLA",
    "tsla": "TSLA",
    "amd": "AMD",
    "asml": "ASML",
    "asml.as": "ASML.AS",
    "hsbc": "HSBA.L",
    "hsba": "HSBA.L",
    "barclays": "BARC.L",
    "barc": "BARC.L",
    "gold": "GOLD",
}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _extract_tickers(text: str) -> list[str]:
    q = _clean(text)
    found = []

    # Check longer keys first so "asml.as" wins over "asml".
    for name, ticker in sorted(COMPANY_TICKERS.items(), key=lambda item: len(item[0]), reverse=True):
        if re.search(rf"(?<![a-z0-9.]){re.escape(name)}(?![a-z0-9.])", q):
            if ticker not in found:
                found.append(ticker)

    for raw in re.findall(r"\b[A-Z]{2,5}(?:\.[A-Z]{1,3})?\b", text):
        if raw not in {"FIRE", "ETF", "USD", "EUR", "GBP", "JPY", "SEC", "FCA", "AML", "DCA"}:
            ticker = raw.upper()
            if ticker not in found:
                found.append(ticker)

    return found


def _last_tickers(prior_user_turns: list[str]) -> list[str]:
    tickers = []
    for turn in prior_user_turns:
        for ticker in _extract_tickers(turn):
            if ticker not in tickers:
                tickers.append(ticker)
    return tickers


def _referential_follow_up(q: str) -> bool:
    return any(
        phrase in q
        for phrase in (
            "what about",
            "compare them",
            "should i sell some",
            "how much do i own",
            "that one",
            "them",
            "it",
        )
    )


def _add_common_entities(query: str, entities: dict[str, Any]) -> dict[str, Any]:
    q = _clean(query)

    tickers = _extract_tickers(query)
    if tickers:
        entities["tickers"] = tickers

    if "s&p 500" in q or "s&p500" in q:
        entities["index"] = "S&P 500"
    elif "ftse" in q:
        entities["index"] = "FTSE 100"
    elif "nikkei" in q:
        entities["index"] = "NIKKEI 225"
    elif "msci world" in q:
        entities["index"] = "MSCI World"

    if "today" in q:
        entities["time_period"] = "today"
    elif "this week" in q:
        entities["time_period"] = "this_week"
    elif "this month" in q:
        entities["time_period"] = "this_month"
    elif "this year" in q:
        entities["time_period"] = "this_year"

    for action in ("buy", "sell", "hold", "hedge", "rebalance"):
        if action in q:
            entities["action"] = action

    if "retire" in q or "retirement" in q:
        entities["goal"] = "retirement"
    elif "college" in q or "education" in q or "child" in q:
        entities["goal"] = "education"
    elif "house" in q or "down payment" in q:
        entities["goal"] = "house"
    elif "fire" in q:
        entities["goal"] = "FIRE"
    elif "emergency fund" in q:
        entities["goal"] = "emergency_fund"

    for currency in ("USD", "EUR", "GBP", "JPY"):
        if re.search(rf"\b{currency.lower()}\b", q):
            entities["currency"] = currency

    if "%" in q:
        rate_match = re.search(r"(\d+(?:\.\d+)?)\s*%", q)
        if rate_match:
            entities["rate"] = float(rate_match.group(1)) / 100

    year_match = re.search(r"(\d+)\s*years?", q)
    if year_match:
        entities["period_years"] = int(year_match.group(1))

    if any(word in q for word in ("monthly", "month", "a month")):
        entities["frequency"] = "monthly"
    elif "weekly" in q:
        entities["frequency"] = "weekly"
    elif "daily" in q:
        entities["frequency"] = "daily"
    elif "yearly" in q or "annually" in q:
        entities["frequency"] = "yearly"

    if "6 months" in q:
        entities["horizon"] = "6_months"
    elif "1 year" in q:
        entities["horizon"] = "1_year"
    elif "5 years" in q:
        entities["horizon"] = "5_years"

    money_numbers = re.findall(r"\b(\d+(?:\.\d+)?)(k)?\b", q)
    for number, suffix in money_numbers:
        value = float(number) * (1000 if suffix else 1)
        if value >= 100 or "monthly" in q or "loan" in q or "profit" in q:
            entities.setdefault("amount", int(value) if value.is_integer() else value)
            break

    return entities


def _extract_topics_and_sectors(query: str, agent: str, entities: dict[str, Any]) -> dict[str, Any]:
    q = _clean(query)
    topics = []
    sectors = []

    topic_phrases = {
        "mutual fund": "mutual fund",
        "compound interest": "compound interest",
        "etf": "ETF",
        "index fund": "index fund",
        "p/e ratio": "P/E ratio",
        "pe ratio": "P/E ratio",
        "dollar cost averaging": "DCA",
        "dca": "DCA",
        "lump-sum": "lump-sum",
        "lump sum": "lump-sum",
        "fx": "FX",
        "eur/usd": "FX",
        "ltcg": "LTCG",
        "capital gains tax": "LTCG",
        "beta": "beta",
        "max drawdown": "max drawdown",
        "recession": "recession",
        "large cap": "large cap",
        "emerging market": "emerging markets",
        "emerging markets": "emerging markets",
        "world": "world",
        "dividend": "dividend",
        "login": "login",
        "bank account": "bank account",
        "transaction history": "transaction history",
        "recurring investment": "recurring investment",
    }
    for needle, topic in topic_phrases.items():
        if needle in q and topic not in topics:
            topics.append(topic)

    if "tech" in q or "technology" in q:
        sectors.append("technology")

    if agent == "product_recommendation" and "ETF" not in topics and "etf" in q:
        topics.append("ETF")

    if topics:
        entities["topics"] = topics
    if sectors:
        entities["sectors"] = sectors
    return entities


def _pick_agent(query: str) -> str:
    q = _clean(query)

    if q in {"hi", "hello", "thanks", "thank you", "thx"}:
        return "general_query"

    if "that thing" in q or "mentioned earlier" in q:
        return "general_query"

    if any(phrase in q for phrase in ("how is my portfolio", "health check", "well diversified", "concentration risk", "beating the market", "review my holdings", "portfolio summary")):
        return "portfolio_health"

    if "how much do i own" in q:
        return "portfolio_query"

    if any(phrase in q for phrase in ("what is", "what's the difference", "explain", "what does")) and not _extract_tickers(query):
        return "general_query"

    if any(phrase in q for phrase in ("should i", "rebalance", "equity-bond split", "good time to invest", "hedge my")):
        return "investment_strategy"

    if any(phrase in q for phrase in ("retire", "college fund", "down payment", "fire plan", "save for")):
        return "financial_planning"

    if any(phrase in q for phrase in ("calculate", "future value", "convert", "mortgage", "investing", "monthly for")):
        return "financial_calculator"

    if any(phrase in q for phrase in ("downside risk", "beta", "max drawdown", "stress test", "exposed am i")):
        return "risk_assessment"

    if any(phrase in q for phrase in ("recommend", "which fund", "best low-cost")):
        return "product_recommendation"

    if any(phrase in q for phrase in ("where will", "predict")):
        return "predictive_analysis"

    if any(phrase in q for phrase in ("can't login", "change my linked bank", "transaction history", "didn't go through")):
        return "customer_support"

    if _extract_tickers(query) or any(phrase in q for phrase in ("price of", "tell me about", "news on", "markets today", "top gainers", "gold price", "eur/usd", "ftse", "nikkei", "what happened in markets", "what about", "compare them")):
        return "market_research"

    return "general_query"


def _fallback_classify(query: str, prior_user_turns: list[str]) -> ClassificationResult:
    q = _clean(query)
    agent = _pick_agent(query)
    entities: dict[str, Any] = {}

    entities = _add_common_entities(query, entities)

    if prior_user_turns and _referential_follow_up(q):
        carried = _last_tickers(prior_user_turns)
        if "what about" in q and entities.get("tickers"):
            pass
        elif "compare them" in q and carried:
            entities["tickers"] = carried[-2:] if len(carried) >= 2 else carried
            entities["intent"] = "comparison"
        elif carried and not entities.get("tickers"):
            entities["tickers"] = [carried[-1]]

    entities = _extract_topics_and_sectors(query, agent, entities)

    return ClassificationResult(
        intent=agent,
        agent=agent,
        entities=entities,
        safety={"verdict": "safe", "reason": "informational only; local guard has precedence"},
    )


def _parse_llm_result(raw: Any) -> ClassificationResult | None:
    if isinstance(raw, ClassificationResult):
        return raw
    if not isinstance(raw, dict):
        return None

    agent = raw.get("agent") or raw.get("target_agent")
    if agent not in AGENTS:
        return None

    return ClassificationResult(
        intent=raw.get("intent") or agent,
        agent=agent,
        entities=raw.get("entities") or {},
        safety=raw.get("safety") or {"verdict": "safe", "reason": "provided by classifier"},
    )


def classify(query: str, prior_user_turns: list[str] | None = None, llm: Any = None) -> ClassificationResult:
    prior_user_turns = prior_user_turns or []

    if llm is not None:
        try:
            parsed = _parse_llm_result(llm(query=query, prior_user_turns=prior_user_turns))
            if parsed is not None:
                return parsed
        except Exception:
            pass

    return _fallback_classify(query, prior_user_turns)
