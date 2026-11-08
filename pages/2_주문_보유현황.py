import requests
import streamlit as st

from utils.formatting import format_number, format_percent, format_won
from utils.kis_client import (
    get_balance_snapshot,
    get_open_orders,
    get_order_history,
)
from utils.navigation import render_sidebar_navigation
from utils.storage import init_session_state


def _display_order(row: dict) -> dict[str, str]:
    side_code = str(row.get("sll_buy_dvsn_cd") or "")
    side = row.get("sll_buy_dvsn_cd_name") or {
        "01": "매도",
        "02": "매수",
    }.get(side_code, side_code or "-")
    return {
        "주문일": str(row.get("ord_dt") or "-"),
        "주문시간": str(row.get("ord_tmd") or "-"),
        "주문번호": str(row.get("odno") or "-"),
        "종목코드": str(row.get("pdno") or "-"),
        "종목명": str(row.get("prdt_name") or "-"),
        "구분": str(side),
        "주문수량": format_number(row.get("ord_qty")),
        "주문가격": format_won(row.get("ord_unpr")),
        "체결수량": format_number(row.get("tot_ccld_qty")),
        "미체결수량": format_number(row.get("rmn_qty")),
    }


def _display_holding(row: dict) -> dict[str, str]:
    return {
        "종목코드": str(row.get("symbol") or "-"),
        "종목명": str(row.get("name") or "-"),
        "보유수량": format_number(row.get("quantity")),
        "평균매입가": format_won(row.get("average_price")),
        "현재가": format_won(row.get("current_price")),
        "평가금액": format_won(row.get("evaluation_amount")),
        "평가손익": format_won(row.get("profit_loss")),
        "수익률": format_percent(row.get("profit_loss_pct")),
    }


init_session_state()
render_sidebar_navigation(active_page="operations")

st.title("주문/보유현황")
st.write("모의투자 계좌의 주문 내역과 현재 잔고를 조회합니다.")

latest_order_result = st.session_state.get("order_result")
if latest_order_result is not None:
    if latest_order_result.get("ok"):
        st.success(
            "최근 주문 요청이 접수되었습니다. "
            f"{latest_order_result.get('message', '')}"
        )
        if latest_order_result.get("order_no"):
            st.caption(f"주문번호: {latest_order_result['order_no']}")
    else:
        st.error(f"최근 주문 요청 실패: {latest_order_result.get('message', '')}")

col1, col2 = st.columns(2)
with col1:
    st.subheader("최근 주문")
    try:
        order_items = get_order_history()
    except (requests.RequestException, RuntimeError, ValueError) as error:
        st.error(f"최근 주문 조회 실패: {error}")
        order_items = None

    if order_items:
        st.dataframe(
            [_display_order(row) for row in order_items],
            hide_index=True,
            alt="최근 주문 내역",
        )
    elif order_items is not None:
        st.info("최근 주문 내역이 없습니다.")

    st.subheader("미체결 주문")
    try:
        open_order_items = get_open_orders()
    except (requests.RequestException, RuntimeError, ValueError) as error:
        st.error(f"미체결 주문 조회 실패: {error}")
        open_order_items = None

    if open_order_items:
        st.dataframe(
            [_display_order(row) for row in open_order_items],
            hide_index=True,
            alt="미체결 주문 내역",
        )
    elif open_order_items is not None:
        st.info("미체결 주문이 없습니다.")

with col2:
    st.subheader("예수금 및 잔고")
    try:
        balance = get_balance_snapshot()
    except (requests.RequestException, RuntimeError, ValueError) as error:
        st.error(f"잔고 조회 실패: {error}")
        balance = None

    if balance is not None:
        summary = balance["summary"]
        metrics = st.columns(3)
        metrics[0].metric("예수금", format_won(summary["cash"]), border=True)
        metrics[1].metric(
            "평가금액",
            format_won(summary["evaluation_amount"]),
            border=True,
        )
        metrics[2].metric(
            "평가손익",
            format_won(summary["profit_loss"]),
            border=True,
        )
        st.caption(f"데이터 출처: {balance['source']}")

        st.subheader("보유 종목")
        holdings = balance["holdings"]
        if holdings:
            st.dataframe(
                [_display_holding(row) for row in holdings],
                hide_index=True,
                alt="보유 종목 및 평가 현황",
            )
        else:
            st.info("현재 보유 종목이 없습니다.")
