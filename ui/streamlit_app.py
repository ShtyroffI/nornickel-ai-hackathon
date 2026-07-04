import os

import requests
import streamlit as st


API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")


def _get(endpoint: str, token: str | None = None) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(f"{API_URL}{endpoint}", headers=headers, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _post(endpoint: str, payload: dict, token: str | None = None, is_form: bool = False) -> dict:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
        
    if is_form:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        resp = requests.post(f"{API_URL}{endpoint}", data=payload, headers=headers, timeout=120)
    else:
        headers["Content-Type"] = "application/json"
        resp = requests.post(f"{API_URL}{endpoint}", json=payload, headers=headers, timeout=120)
        
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    st.set_page_config(page_title="Научный клубок", layout="wide")
    st.title("Научный клубок — карта знаний R&D")

    if "token" not in st.session_state:
        st.session_state.token = None

    if not st.session_state.token:
        st.info("Пожалуйста, авторизуйтесь для доступа к Базе знаний R&D.")
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("Вход в систему")
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="admin@example.com")
                password = st.text_input("Пароль", type="password")
                submitted = st.form_submit_button("Войти")
                
                if submitted:
                    try:
                        token = _post(
                            "/auth/login",
                            {"username": email, "password": password},
                            is_form=True,
                        )
                        st.session_state.token = token["access_token"]
                        st.rerun()
                    except Exception as exc:
                        st.error("Ошибка авторизации. Проверьте логин и пароль.")
        st.stop()

    with st.sidebar:
        st.header("Профиль")
        st.success("Вы авторизованы")
        if st.button("Выйти", use_container_width=True):
            st.session_state.token = None
            st.rerun()

    tab_query, tab_review, tab_analytics, tab_compare, tab_recommend, tab_graph, tab_kb = st.tabs(
        ["Поиск", "Обзор", "Пробелы", "Сравнение", "Рекомендации", "Граф", "База знаний"]
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
                if "answer" in res:
                    st.success(res["answer"])
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
                if "summary" in res:
                    st.markdown(f"### Обзор по теме: {res.get('topic', topic)}")
                    st.info(res["summary"])
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("#### ✅ Доказанные факты (Консенсус)")
                        for item in res.get("consensus", []):
                            st.success(f"- {item}")
                        if not res.get("consensus"):
                            st.write("Нет данных")
                            
                    with col2:
                        st.markdown("#### ⚠️ Спорные моменты")
                        for item in res.get("disagreements", []):
                            st.warning(f"- {item}")
                        if not res.get("disagreements"):
                            st.write("Нет данных")
                            
                    st.markdown("#### 📚 Сгруппированные источники")
                    groups = res.get("groups", {})
                    if groups:
                        for g_name, g_sources in groups.items():
                            with st.expander(f"📁 {g_name} ({len(g_sources)})", expanded=True):
                                for src in g_sources:
                                    st.write(f"- 📄 {src}")
                    else:
                        st.write("Источники не найдены")
                            
                    st.caption(f"Уверенность LLM: {int(res.get('confidence', 0)*100)}% | Найдено фрагментов графа: {res.get('sources_count', 0)}")
                else:
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
                if isinstance(res, list):
                    for gap in res:
                        sev = gap.get("severity", "unknown").lower()
                        if sev == "high":
                            color = "🔴 Высокий (Нет данных)"
                            st.error(f"**{gap.get('material', '')}** + **{gap.get('process', '')}** + **{gap.get('condition', '')}** — {color}")
                        elif sev == "medium":
                            color = "🟡 Средний (Мало данных)"
                            st.warning(f"**{gap.get('material', '')}** + **{gap.get('process', '')}** + **{gap.get('condition', '')}** — {color}")
                        elif sev == "low":
                            color = "🟢 Низкий (Изучено)"
                            st.success(f"**{gap.get('material', '')}** + **{gap.get('process', '')}** + **{gap.get('condition', '')}** — {color}")
                        else:
                            st.info(f"**{gap.get('material', '')}** + **{gap.get('process', '')}** + **{gap.get('condition', '')}** — Неизвестно")
                            
                        st.write(gap.get("reason", ""))
                        st.divider()
                else:
                    st.json(res)
            except Exception as exc:
                st.error(f"Ошибка: {exc}")

    with tab_compare:
        st.subheader("Сравнительный анализ технологий")
        var_a = st.text_input("Вариант А", "Кучное выщелачивание")
        var_b = st.text_input("Вариант Б", "Автоклавное выщелачивание")
        crit = st.text_input("Критерии (через запятую)", "Эффективность, Применимость в холодном климате, Затраты")
        if st.button("Сравнить"):
            try:
                res = _post(
                    "/analytics/compare",
                    {
                        "variant_a": var_a,
                        "variant_b": var_b,
                        "criteria": [x.strip() for x in crit.split(",")]
                    },
                    token=st.session_state.token,
                )
                if "rows" in res:
                    import pandas as pd
                    df = pd.DataFrame(res["rows"])
                    if not df.empty:
                        df.rename(columns={"criterion": "Критерий", "a_value": var_a, "b_value": var_b}, inplace=True)
                        st.table(df)
                    else:
                        st.warning("Не удалось составить сравнение на основе базы знаний.")
                else:
                    st.json(res)
            except Exception as exc:
                st.error(f"Ошибка: {exc}")

    with tab_recommend:
        st.subheader("Рекомендации и смежные области")
        rec_topic = st.text_input("Тема для рекомендаций", "электроэкстракция никеля")
        if st.button("Получить рекомендации"):
            try:
                res = _get(f"/analytics/recommend?topic={rec_topic}", token=st.session_state.token)
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("#### 🔄 Похожие кейсы")
                    for case in res.get("related_cases", []):
                        st.info(f"- {case}")
                with col2:
                    st.markdown("#### 👥 Эксперты / Авторы")
                    for expert in res.get("experts", []):
                        st.success(f"- {expert}")
                with col3:
                    st.markdown("#### 📖 Смежные темы")
                    for adj in res.get("adjacent_topics", []):
                        st.warning(f"- {adj}")
                        
            except Exception as exc:
                st.error(f"Ошибка: {exc}")

    with tab_graph:
        st.subheader("Поиск по графу знаний")
        st.write("Введите слово или фразу (например: «никель», «флотация», «Иванов») для поиска по базе.")
        
        query = st.text_input("Поисковый запрос", "никель")
        if st.button("Найти связи"):
            try:
                res = _get(f"/graph/search?q={query}&depth=2", token=st.session_state.token)
                
                nodes = res.get("nodes", [])
                edges = res.get("edges", [])
                
                if not nodes:
                    st.warning("Ничего не найдено по этому запросу.")
                else:
                    st.success(f"Найдено узлов: {len(nodes)}, связей: {len(edges)}")
                    
                    # Построение графа с помощью pyvis
                    try:
                        from pyvis.network import Network
                        import tempfile
                        
                        net = Network(height="600px", width="100%", bgcolor="#222222", font_color="white")
                        
                        # Цветовая схема для разных типов узлов
                        color_map = {
                            "Material": "#1f77b4",   # Синий
                            "Process": "#ff7f0e",    # Оранжевый
                            "Equipment": "#2ca02c",  # Зеленый
                            "Property": "#d62728",   # Красный
                            "Publication": "#9467bd",# Фиолетовый
                            "Expert": "#8c564b",     # Коричневый
                            "Facility": "#e377c2"    # Розовый
                        }
                        
                        for n in nodes:
                            n_type = n.get("type", "Entity")
                            color = color_map.get(n_type, "#7f7f7f") # Серый по умолчанию
                            
                            # Highlight search query matches
                            n_name = str(n.get("name", ""))
                            if query.lower() in n_name.lower():
                                color = "#ffffff" # Белый для точных совпадений
                                
                            net.add_node(
                                n.get("id"), 
                                label=n_name, 
                                title=f"Тип: {n_type}",
                                color=color
                            )
    
                        for e in edges:
                            source = e.get("source")
                            target = e.get("target")
                            rel_type = e.get("type", "")
                            
                            # Подсветка проблем (если есть противоречия или пробелы)
                            edge_color = "#888888"
                            if "contradicts" in rel_type.lower():
                                edge_color = "#ff0000"
                                
                            if source and target:
                                net.add_edge(source, target, label=rel_type, color=edge_color)
                        
                        # Физика графа для красивого разлета
                        net.repulsion(node_distance=150, spring_length=200)
                        
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
                            net.save_graph(tmp_file.name)
                            with open(tmp_file.name, "r", encoding="utf-8") as f:
                                html_data = f.read()
                        
                        import streamlit.components.v1 as components
                        components.html(html_data, height=650)
                        
                        st.info("💡 **Подсказка:** Используйте вкладку «Аналитика» для поиска противоречий и пробелов (например: «нет экспериментов для комбинации: холодный климат + выщелачивание»).")
                    except ImportError:
                        st.warning("Установите pyvis для отрисовки графа.")
                        st.json(res)
            except Exception as exc:
                st.error(f"Ошибка: {exc}")


    with tab_kb:
        st.subheader("Загрузка документов в базу знаний")
        
        uploaded_files = st.file_uploader("Выберите файлы (TXT, PDF, MD, DOCX)", type=["txt", "pdf", "md", "docx"], accept_multiple_files=True)
        if st.button("Загрузить файлы"):
            if uploaded_files:
                progress_text = "Подготовка к загрузке..."
                progress_bar = st.progress(0.0, text=progress_text)
                
                total = len(uploaded_files)
                for i, file in enumerate(uploaded_files):
                    # 1. Сначала получаем оценку времени и узлов
                    try:
                        headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}
                        file.seek(0)
                        files_payload = {"file": (file.name, file.getvalue(), file.type)}
                        est_resp = requests.post(f"{API_URL}/graph/upload/estimate", files=files_payload, headers=headers, timeout=60)
                        est_resp.raise_for_status()
                        est_data = est_resp.json()
                        nodes = est_data["estimated_nodes"]
                        sec = est_data["estimated_time_seconds"]
                        progress_bar.progress(i / total, text=f"Загрузка файла {i+1} из {total}: {file.name} (Ожидается узлов: ~{nodes}, Время: ~{sec} сек)...")
                    except Exception:
                        progress_bar.progress(i / total, text=f"Загрузка файла {i+1} из {total}: {file.name} (Вычисление времени...)")
                        
                    # 2. Выполняем саму загрузку
                    try:
                        file.seek(0)
                        files_payload = {"file": (file.name, file.getvalue(), file.type)}
                        import json
                        resp = requests.post(f"{API_URL}/graph/upload", files=files_payload, headers=headers, stream=True, timeout=600)
                        resp.raise_for_status()
                        
                        final_res = None
                        for line in resp.iter_lines():
                            if line:
                                data = json.loads(line)
                                if "status" in data and data["status"] == "success":
                                    final_res = data
                                else:
                                    p = data.get("processed", 0)
                                    t = data.get("total", 1)
                                    progress_bar.progress(p / t, text=f"Загрузка файла {i+1} из {total}: {file.name} (Сохранено в базу: {p} из {t})...")
                        
                        if final_res:
                            st.success(f"✅ {final_res['filename']} — Узлов: {final_res['entities_extracted']}, Связей: {final_res['triples_extracted']}")
                        else:
                            st.error(f"❌ Ошибка при загрузке {file.name}: Неожиданный ответ от сервера")
                    except Exception as exc:
                        st.error(f"❌ Ошибка при загрузке {file.name}: {exc}")
                        
                progress_bar.progress(1.0, text="Все файлы обработаны!")
            else:
                st.warning("Пожалуйста, выберите хотя бы один файл.")
                
        st.divider()
        st.subheader("Статистика базы знаний (Графа)")
        if st.button("Обновить статистику"):
            try:
                stats = _get("/graph/stats", token=st.session_state.token)
                col1, col2 = st.columns(2)
                col1.metric("Всего узлов (Nodes)", stats.get("nodes_count", 0))
                col2.metric("Всего связей (Relationships)", stats.get("relations_count", 0))
                
                st.markdown("#### Загруженные документы:")
                for doc in stats.get("loaded_documents", []):
                    st.write(f"- 📄 {doc}")
            except Exception as exc:
                st.error(f"Ошибка: {exc}")


if __name__ == "__main__":
    main()
