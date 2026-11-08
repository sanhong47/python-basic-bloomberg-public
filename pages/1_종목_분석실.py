from datetime import date

import requests
import streamlit as st

from utils.analysis import build_order_gap_summary, compute_indicators, normalize_ohlcv
from utils.ai_assistant import ask_analysis_copilot
from utils.ai_assistant import summarize_news_briefing
from utils.formatting import format_percent, format_won
from utils.kis_client import (
    get_current_price,
    get_price_history,
    submit_paper_order,
)
from utils.navigation import render_sidebar_navigation
from utils.news_client import fetch_company_news
from utils.storage import init_session_state


def _clear_order_preview() -> None:
    st.session_state.order_preview = None
    st.session_state.order_draft = None
    st.session_state.order_result = None


@st.cache_data(ttl=900)
def _load_company_news(company_name: str, symbol: str) -> list[dict]:
    return fetch_company_news(company_name=company_name, symbol=symbol)


@st.cache_data(ttl=60)
def _load_current_price(symbol: str) -> dict:
    return get_current_price(symbol)


@st.cache_data(ttl=300)
def _load_price_history(symbol: str, start_date: date, end_date: date) -> list[dict]:
    return get_price_history(symbol, start_date, end_date)


st.set_page_config(
    page_title="Bloomberg | 종목 분석실",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_session_state()
render_sidebar_navigation(active_page="analysis")

st.title("종목 분석실")

with st.sidebar:
    st.subheader("주문 패널")

    account_mode = st.selectbox(
        "계좌 모드",
        options=["demo", "real"],
        key="order_ticket_account_mode",
        on_change=_clear_order_preview,
        format_func=lambda value: "모의투자" if value == "demo" else "실전투자",
    )
    order_symbol = st.text_input(
        "종목코드",
        key="order_ticket_symbol",
        on_change=_clear_order_preview,
    ).strip()
    side = st.selectbox(
        "주문 구분",
        options=["buy", "sell"],
        key="order_ticket_side",
        on_change=_clear_order_preview,
        format_func=lambda value: "매수" if value == "buy" else "매도",
    )
    order_type = st.selectbox(
        "주문 유형",
        options=["market", "limit"],
        key="order_ticket_type",
        on_change=_clear_order_preview,
        format_func=lambda value: "시장가" if value == "market" else "지정가",
    )
    qty = st.number_input(
        "수량",
        min_value=1,
        step=1,
        key="order_ticket_qty",
        on_change=_clear_order_preview,
    )

    order_quote = None
    quote_error = None
    if order_symbol:
        try:
            order_quote = _load_current_price(order_symbol)
        except (requests.RequestException, RuntimeError, ValueError) as error:
            quote_error = str(error)

    if order_quote is not None:
        market_price = int(order_quote["current_price"])
        st.session_state.order_ticket_market_price = market_price
        st.session_state.order_ticket_market_as_of = order_quote.get(
            "as_of", "알 수 없음"
        )
        if st.session_state.get("order_ticket_price_symbol") != order_symbol:
            st.session_state.order_ticket_price = market_price
            st.session_state.order_ticket_price_symbol = order_symbol

    if order_type == "market":
        refresh_columns = st.columns([3, 1], vertical_alignment="bottom")
        with refresh_columns[1]:
            refresh_clicked = st.button(
                "↻",
                key="refresh_market_price",
                help="현재 시장가 새로고침",
                width="stretch",
            )

        if refresh_clicked and order_symbol:
            _clear_order_preview()
            try:
                _load_current_price.clear()
                order_quote = get_current_price(order_symbol)
                st.session_state.order_ticket_market_price = int(
                    order_quote["current_price"]
                )
                st.session_state.order_ticket_market_as_of = order_quote.get(
                    "as_of", "알 수 없음"
                )
                quote_error = None
            except (requests.RequestException, RuntimeError, ValueError) as error:
                order_quote = None
                quote_error = str(error)

        with refresh_columns[0]:
            st.text_input(
                "가격",
                value=(
                    format_won(order_quote["current_price"])
                    if order_quote is not None
                    else "현재가 조회 실패"
                ),
                disabled=True,
                key="order_ticket_market_price_display",
            )

        if order_quote is not None:
            st.caption(f"기준 시각: {st.session_state.order_ticket_market_as_of}")
        price = (
            float(order_quote["current_price"])
            if order_quote is not None
            else 0.0
        )
    else:
        if order_quote is not None:
            st.caption(f"현재가: {format_won(order_quote['current_price'])}")
        elif quote_error:
            st.warning(f"현재가를 조회하지 못했습니다: {quote_error}")
        price = st.number_input(
            "가격",
            min_value=1,
            step=500,
            key="order_ticket_price",
            on_change=_clear_order_preview,
            help="지정가 주문의 주당 가격을 입력하세요.",
        )

    preview_clicked = st.button(
        "주문 미리보기",
        key="order_preview_button",
        width="stretch",
    )
    if quote_error and order_type == "market":
        st.warning(f"현재가를 조회하지 못했습니다: {quote_error}")

    if preview_clicked:
        if not order_symbol:
            st.error("종목코드를 입력해 주세요.")
        elif order_quote is None:
            st.error("현재가를 확인할 수 없어 주문을 미리 볼 수 없습니다.")
        elif order_type == "limit" and price <= 0:
            st.error("지정가를 1원 이상 입력해 주세요.")
        else:
            preview = build_order_gap_summary(
                current_price=float(order_quote["current_price"]),
                side=side,
                order_type=order_type,
                qty=int(qty),
                price=float(price),
            )
            order_draft = {
                **preview,
                "symbol": order_symbol,
                "account_mode": account_mode,
                "estimated_amount": round(preview["price"] * int(qty), 2),
            }
            if order_draft != st.session_state.get("order_draft"):
                st.session_state.order_result = None
            st.session_state.order_preview = order_draft
            st.session_state.order_draft = dict(order_draft)

    order_preview = st.session_state.get("order_preview")
    if order_preview is not None:
        st.caption(
            f"{order_preview['symbol']} · "
            f"{'매수' if order_preview['side'] == 'buy' else '매도'} · "
            f"{'시장가' if order_preview['order_type'] == 'market' else '지정가'} · "
            f"{order_preview['qty']}주"
        )
        st.metric(
            "예상 주문금액",
            format_won(order_preview["estimated_amount"]),
        )
        gap_price = order_preview["gap_price"]
        gap_pct = order_preview["gap_pct_vs_current"]
        st.write(
            "현재가 대비 차이: "
            f"{gap_price:+,.0f}원 ({gap_pct:+.2f}%)"
        )
        if order_preview["warning"] == "정상 범위":
            st.success(order_preview["warning"])
        else:
            st.warning(order_preview["warning"])

        submit_disabled = (
            order_preview["account_mode"] != "demo"
            or st.session_state.order_result is not None
        )
        if order_preview["account_mode"] == "demo":
            submit_clicked = st.button(
                "주문하기",
                key="submit_order_button",
                type="primary",
                disabled=submit_disabled,
                width="stretch",
            )
            if submit_clicked:
                try:
                    st.session_state.order_result = submit_paper_order(
                        st.session_state.order_draft
                    )
                except (requests.RequestException, RuntimeError, ValueError) as error:
                    st.session_state.order_result = {
                        "ok": False,
                        "message": str(error),
                    }
                st.rerun()
        else:
            st.button(
                "실전 주문 (미지원)",
                key="submit_real_order_button",
                disabled=True,
                width="stretch",
            )

    order_result = st.session_state.get("order_result")
    if order_result is not None:
        message = order_result.get("message", "주문 결과를 확인할 수 없습니다.")
        if order_result.get("ok"):
            st.success(message)
            if order_result.get("order_no"):
                st.caption(f"주문번호: {order_result['order_no']}")
            st.page_link(
                "pages/2_주문_보유현황.py",
                label="주문/보유현황에서 결과 확인",
            )
        else:
            st.error(f"주문 실패: {message}")
            st.caption(
                "요청 상태가 불분명하면 주문 내역을 먼저 확인하세요. "
                "재요청 전 주문 내용을 확인하고 새 미리보기를 만들어 주세요."
            )

    if account_mode == "real":
        st.caption("실전 주문 전송은 아직 구현되지 않았습니다. 미리보기만 가능합니다.")

st.write(
    "저장한 종목과 기간 기준으로 시세·지표·차트를 확인하고 AI Copilot에 질문할 수 있습니다. "
    "최신 뉴스 브리핑과 모의투자 주문도 확인할 수 있습니다."
)

left_col, right_col = st.columns([2, 1])

with left_col:
    st.subheader("분석 입력")

    analysis_form_defaults = {
        "analysis_form_symbol": "selected_symbol",
        "analysis_form_start_date": "start_date",
        "analysis_form_end_date": "end_date",
    }
    for form_key, state_key in analysis_form_defaults.items():
        if form_key not in st.session_state:
            st.session_state[form_key] = st.session_state[state_key]

    with st.form("analysis_input_form"):
        st.text_input("종목코드", key="analysis_form_symbol")
        st.date_input("시작일", key="analysis_form_start_date")
        st.date_input("종료일", key="analysis_form_end_date")
        save_analysis = st.form_submit_button("저장")

    if save_analysis:
        symbol = st.session_state.analysis_form_symbol.strip()
        start_date = st.session_state.analysis_form_start_date
        end_date = st.session_state.analysis_form_end_date

        if not symbol:
            st.error("종목코드를 입력해 주세요.")
        elif start_date > end_date:
            st.error("시작일은 종료일보다 늦을 수 없습니다.")
        else:
            st.session_state.selected_symbol = symbol
            st.session_state.start_date = start_date
            st.session_state.end_date = end_date
            st.success("분석 기준을 저장했습니다.")

    st.subheader("차트와 지표")
    symbol = st.session_state.selected_symbol
    start_date = st.session_state.start_date
    end_date = st.session_state.end_date
    analysis_ai_context = {
        "symbol": symbol,
        "company_name": symbol,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "current_quote": None,
        "indicators": None,
    }
    st.caption(f"분석 기준: {symbol} · {start_date:%Y-%m-%d} ~ {end_date:%Y-%m-%d}")

    quote = None
    try:
        quote = _load_current_price(symbol)
    except (requests.RequestException, RuntimeError, ValueError) as error:
        st.error(f"현재가를 조회하지 못했습니다: {error}")

    history_records = None
    try:
        history_records = _load_price_history(symbol, start_date, end_date)
    except (requests.RequestException, RuntimeError, ValueError) as error:
        st.error(f"기간 시세를 조회하지 못했습니다: {error}")

    if quote is not None:
        analysis_ai_context["company_name"] = quote.get("company_name", symbol)
        analysis_ai_context["current_quote"] = {
            "price": quote["current_price"],
            "change_pct": quote.get("change_pct", 0),
            "as_of": quote.get("as_of"),
        }
        quote_columns = st.columns(2)
        quote_columns[0].metric(
            "현재가",
            format_won(quote["current_price"]),
            delta=format_percent(quote.get("change_pct", 0)),
            border=True,
        )
        quote_columns[1].metric(
            "종목",
            quote.get("company_name", symbol),
            border=True,
        )
        st.caption(
            f"기준 시각: {quote.get('as_of', '알 수 없음')} · "
            f"데이터 출처: {quote.get('source', '알 수 없음')}"
        )

    if history_records is not None:
        price_df = compute_indicators(normalize_ohlcv(history_records))
        if price_df.empty:
            st.info("선택한 기간에 표시할 시세 데이터가 없습니다.")
        else:
            latest = price_df.iloc[-1]
            analysis_ai_context["indicators"] = {
                "latest_date": latest["date"].isoformat(),
                "latest_close": float(latest["close"]),
                "period_return_pct": float(latest["period_return_pct"]),
                "ma5": float(latest["ma5"]),
                "ma20": float(latest["ma20"]),
                "volatility_pct": float(latest["volatility_pct"]),
            }
            indicator_columns = st.columns(4)
            indicator_columns[0].metric(
                "기간 수익률",
                format_percent(latest["period_return_pct"]),
                border=True,
            )
            indicator_columns[1].metric(
                "5일 이동평균",
                format_won(latest["ma5"]),
                border=True,
            )
            indicator_columns[2].metric(
                "20일 이동평균",
                format_won(latest["ma20"]),
                border=True,
            )
            indicator_columns[3].metric(
                "변동성 (20일)",
                format_percent(latest["volatility_pct"]),
                border=True,
            )

            st.subheader("종가 및 이동평균")
            st.line_chart(
                price_df,
                x="date",
                y=["close", "ma5", "ma20"],
                alt=f"{symbol} 종가와 5일·20일 이동평균",
            )

            st.subheader("기간 시세")
            st.dataframe(
                price_df[["date", "open", "high", "low", "close", "volume"]],
                hide_index=True,
                column_config={
                    "date": "날짜",
                    "open": st.column_config.NumberColumn("시가", format="%d"),
                    "high": st.column_config.NumberColumn("고가", format="%d"),
                    "low": st.column_config.NumberColumn("저가", format="%d"),
                    "close": st.column_config.NumberColumn("종가", format="%d"),
                    "volume": st.column_config.NumberColumn("거래량", format="%d"),
                },
                alt=f"{symbol} 기간별 OHLCV 시세",
            )

with right_col:
    st.subheader("AI Copilot")
    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input("현재 분석 화면에 대해 질문하세요", key="analysis_copilot_input")
    if question:
        st.session_state.chat_messages.append(
            {"role": "user", "content": question}
        )
        with st.chat_message("user"):
            st.write(question)

        result = ask_analysis_copilot(analysis_ai_context, question)
        answer = result["answer"]
        st.session_state.chat_messages.append(
            {"role": "assistant", "content": answer}
        )
        with st.chat_message("assistant"):
            st.write(answer)

    st.subheader("뉴스 브리핑")
    news_company_name = analysis_ai_context["company_name"]
    news_load_failed = False
    try:
        news_items = _load_company_news(news_company_name, symbol)
    except (requests.RequestException, RuntimeError, ValueError) as error:
        st.error(f"뉴스 RSS를 불러오지 못했습니다: {error}")
        news_items = []
        news_load_failed = True

    if news_items:
        briefing = summarize_news_briefing(news_company_name, news_items)
        st.write(briefing["summary"])
        for article in news_items:
            st.link_button(
                article["title"],
                article["link"],
                width="stretch",
            )
            st.caption(
                f"{article['source_name']} · {article['published_at']}"
            )
    elif not news_load_failed:
        st.info("최근 7일 이내 관련 뉴스가 없습니다.")
