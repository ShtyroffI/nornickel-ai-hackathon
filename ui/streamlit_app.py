import os

import requests
import streamlit as st


API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")


def _post(path: str, json: dict | None = None, token: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = requests.post(f"{API_URL}{path}", json=json, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def _get(path: str, token: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    response = requests.get(f"{API_URL}{path}", headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def main() -> None:
    st.set_page_config(page_title="Научный клубок", layout="wide")
    st.title("Научный клубок — карта знаний R&D")

    if "token" not in st.session_state:
        st.session_state.token = None

    with st.sidebar:
        st.header("Авторизация")
        email = st.text_input("Email")
        password = st.text_input("Пароль", type="password")
        if st.button("Войти"):
            try:
                token = _post(
                    "/auth/login",
                    {"username": email, "password": password},
                )
                st.session_state.token = token["access_token"]
                st.success("Вход выполнен")
            except Exception as exc:
                st.error(f"Ошибка: {exc}")

    tab_query, tab_review, tab_analytics, tab_graph = st.tabs(
        ["Поиск", "Обзор", "Аналитика", "Граф"]
    )

    with tab_query:
        st.subheader("Семантический запрос")
        text = st.text_area("Запрос", "Методы обессоливания воды при сульфатах ≤300 мг/л")
        col1, col2, col3 = st.columns(3)
        geo = col1.text_input("География")
        yf = col2.number_input("Год от", min_value=1900, max_value=2100, value=2018, step=1)
        yt = col3.number_input("Год до", min_value=1900, max_value=2100, value=2025, step=1)
        if st.button("Выполнить запрос"):
            try:
                res = _post(
                    "/query",
                    {
                        "text": text,
                        "geography": geo or None,
                        "year_from": int(yf),
                        "year_to": int(yt),
                    },
                    token=st.session_state.token,
                )
                st.json(res)
            except Exception as exc:
                st.error(f"Ошибка: {exc}")

    with tab_review:
        st.subheader("Автогенерация обзора")
        topic = st.text_input("Тема", "Электроэкстракция никеля")
        if st.button("Сгенерировать обзор"):
            try:
                res = _post(
                    "/review",
                    {"topic": topic, "group_by": ["method", "year", "geography"]},
                    token=st.session_state.token,
                )
                st.json(res)
            except Exception as exc:
                st.error(f"Ошибка: {exc}")

    with tab_analytics:
        st.subheader("Пробелы в знаниях")
        m = st.text_input("Материалы (через запятую)", "никель, медь")
        p = st.text_input("Процессы (через запятую)", "кучное выщелачивание")
        c = st.text_input("Условия (через запятую)", "холодный климат")
        if st.button("Найти пробелы"):
            try:
                res = _post(
                    "/analytics/gaps",
                    {
                        "materials": [x.strip() for x in m.split(",") if x.strip()],
                        "processes": [x.strip() for x in p.split(",") if x.strip()],
                        "conditions": [x.strip() for x in c.split(",") if x.strip()],
                    },
                    token=st.session_state.token,
                )
                st.json(res)
            except Exception as exc:
                st.error(f"Ошибка: {exc}")

    with tab_graph:
        st.subheader("Окружение сущности")
        eid = st.text_input("ID сущности")
        if st.button("Загрузить"):
            try:
                res = _get(f"/graph/entities/{eid}/neighborhood", token=st.session_state.token)
                st.json(res)
            except Exception as exc:
                st.error(f"Ошибка: {exc}")


if __name__ == "__main__":
    main()
