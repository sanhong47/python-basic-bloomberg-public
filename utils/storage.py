from copy import deepcopy
from datetime import date, timedelta
from typing import Any

import streamlit as st

DEFAULT_SESSION_STATE = {
    "selected_symbol": "005930",
    "start_date": date.today() - timedelta(days=90),
    "end_date": date.today(),
    "price_df": None,
    "analysis_summary": None,
    "analysis_context": None,
    "chat_messages": [],
    "news_items": [],
    "news_briefing": None,
    "order_draft": None,
    "order_result": None,
    "order_preview": None,
    "order_ticket_account_mode": "demo",
    "order_ticket_symbol": "005930",
    "order_ticket_side": "buy",
    "order_ticket_type": "market",
    "order_ticket_qty": 1,
    "order_ticket_price": 70000,
    "order_ticket_market_price": 70100,
    "order_ticket_market_as_of": "예시 시각",
    "portfolio_items": [],
    "order_items": [],
    "open_order_items": [],
}


def _clone_default(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return deepcopy(value)
    return value


def init_session_state() -> None:
    for key, value in DEFAULT_SESSION_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = _clone_default(value)
