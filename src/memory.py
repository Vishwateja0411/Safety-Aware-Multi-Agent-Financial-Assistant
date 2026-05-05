_SESSIONS: dict[str, list[dict[str, str]]] = {}


def get_prior_user_turns(session_id: str) -> list[str]:
    turns = _SESSIONS.get(session_id, [])
    return [turn["content"] for turn in turns if turn.get("role") == "user"]


def save_turn(session_id: str, role: str, content: str) -> None:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = []
    _SESSIONS[session_id].append({"role": role, "content": content})


def clear_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
