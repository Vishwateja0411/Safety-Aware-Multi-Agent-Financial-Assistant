from typing import Any


def _normalize_ticker(ticker: str) -> str:
    return ticker.upper().split(".")[0]


def _normalize_index(index: str) -> str:
    return index.upper().replace(" ", "")


def matches_entities(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    for field, exp_value in expected.items():
        act_value = actual.get(field)
        if act_value is None:
            return False

        if field == "tickers":
            exp_set = {_normalize_ticker(t) for t in exp_value}
            act_set = {_normalize_ticker(t) for t in act_value}
            if not exp_set.issubset(act_set):
                return False
        elif field in ("topics", "sectors"):
            exp_set = {s.lower() for s in exp_value}
            act_set = {s.lower() for s in act_value}
            if not exp_set.issubset(act_set):
                return False
        elif field in ("amount", "rate"):
            if abs(act_value - exp_value) > abs(exp_value) * 0.05:
                return False
        elif field == "period_years":
            if int(act_value) != int(exp_value):
                return False
        elif field == "index":
            if _normalize_index(str(act_value)) != _normalize_index(str(exp_value)):
                return False
        else:
            if str(act_value).lower() != str(exp_value).lower():
                return False
    return True


def test_classifier_routing_accuracy(gold_classifier_queries, mock_llm):
    from src.classifier import classify

    correct = 0
    for case in gold_classifier_queries:
        result = classify(case["query"], llm=mock_llm)
        if result.agent == case["expected_agent"]:
            correct += 1

    accuracy = correct / len(gold_classifier_queries)
    assert accuracy >= 0.85, f"Routing accuracy {accuracy:.2%} below 85%"


def test_classifier_entity_extraction(gold_classifier_queries, mock_llm):
    from src.classifier import classify

    matched = 0
    total_with_entities = 0
    for case in gold_classifier_queries:
        if not case["expected_entities"]:
            continue
        total_with_entities += 1
        result = classify(case["query"], llm=mock_llm)
        if matches_entities(result.entities, case["expected_entities"]):
            matched += 1

    rate = matched / total_with_entities if total_with_entities else 0.0
    assert rate >= 0.75, f"Entity match rate {rate:.2%} below 75%"


def test_classifier_conversation_followups(conversation_test_cases, mock_llm):
    from src.classifier import classify

    all_cases = (
        conversation_test_cases("follow_up_session")
        + conversation_test_cases("multi_intent_session")
        + conversation_test_cases("ambiguous_session")
    )

    for case in all_cases:
        result = classify(
            case["current_user_turn"],
            prior_user_turns=case["prior_user_turns"],
            llm=mock_llm,
        )
        assert result.agent == case["expected"]["agent"], case["case_id"]
        assert matches_entities(result.entities, case["expected"]["entities"]), case["case_id"]
