
from __future__ import annotations

from datetime import date
import os

import pandas as pd
import streamlit as st

from neo4j_service import (
    get_dashboard_metrics,
    get_profile,
    get_students,
    graph_neighborhood,
    list_categories,
    ping,
    recommend_books,
    record_borrow,
    search_books,
    seed_demo_data,
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="GraphBook Recommendation System",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# IMAGE PATH
# =========================================================

IMAGE_PATH = os.path.join(
    "assets",
    "graphbook.jpg"
)


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
    <style>

    /* ==============================
       Main
    ============================== */

    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }


    /* ==============================
       Sidebar
    ============================== */

    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(128,128,128,.15);
    }

    .sidebar-title {
        font-size: 1.5rem;
        font-weight: 750;
        margin-bottom: .1rem;
    }

    .sidebar-subtitle {
        font-size: .82rem;
        opacity: .65;
        margin-bottom: 1rem;
    }


    /* ==============================
       Hero
    ============================== */

    .hero {
        padding: 1.7rem 2rem;
        border-radius: 22px;

        background:
            linear-gradient(
                135deg,
                #111827 0%,
                #1f2937 55%,
                #0f766e 100%
            );

        color: white;
        margin-bottom: 1.5rem;

        box-shadow:
            0 10px 30px rgba(0,0,0,.12);
    }

    .hero h1 {
        margin: 0;
        font-size: 2.25rem;
        font-weight: 750;
        letter-spacing: -.5px;
    }

    .hero p {
        margin: .5rem 0 0 0;
        opacity: .88;
        font-size: 1rem;
        line-height: 1.7;
    }


    /* ==============================
       Section
    ============================== */

    .section-title {
        font-size: 1.35rem;
        font-weight: 700;
        margin-bottom: .8rem;
    }


    /* ==============================
       Book Card
    ============================== */

    .book-card {
        padding: 1.2rem 1.3rem;

        border: 1px solid
            rgba(128,128,128,.20);

        border-radius: 18px;

        margin-bottom: .9rem;

        background:
            rgba(255,255,255,.02);

        box-shadow:
            0 4px 14px rgba(0,0,0,.04);
    }

    .book-card h3 {
        margin-top: .55rem;
        margin-bottom: .3rem;
    }


    /* ==============================
       Score
    ============================== */

    .score-pill {
        display: inline-block;

        padding: .25rem .65rem;

        border-radius: 999px;

        background: #0f766e;

        color: white;

        font-size: .8rem;

        font-weight: 700;
    }


    /* ==============================
       Muted
    ============================== */

    .muted {
        opacity: .68;
        font-size: .9rem;
    }


    /* ==============================
       Footer
    ============================== */

    .footer {
        text-align: center;
        opacity: .5;
        padding-top: 2rem;
        font-size: .82rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# NEO4J CONNECTION
# =========================================================

def require_connection() -> None:

    try:

        if not ping():

            raise RuntimeError(
                "Neo4j did not return a healthy response"
            )

    except Exception as exc:

        st.error(
            "❌ ยังเชื่อมต่อ Neo4j Aura ไม่สำเร็จ"
        )

        st.markdown(
            "ตรวจสอบค่า Neo4j ใน Streamlit Secrets"
        )

        st.code(
            '[neo4j]\n'
            'uri = "neo4j+s://YOUR_INSTANCE.databases.neo4j.io"\n'
            'username = "neo4j"\n'
            'password = "YOUR_PASSWORD"\n'
            'database = "neo4j"',
            language="toml",
        )

        st.caption(
            "⚠️ ห้าม commit password ลง GitHub"
        )

        st.exception(exc)

        st.stop()


# =========================================================
# STUDENT SELECTOR
# =========================================================

def student_selector(
    key: str = "student"
) -> str:

    students = get_students()

    if not students:

        st.info(
            "ยังไม่มีข้อมูลนักศึกษา "
            "กรุณาไปหน้า Admin / Setup "
            "แล้วสร้างข้อมูลตัวอย่าง"
        )

        st.stop()

    labels = {
        f"{x['student_id']} — {x['name']}":
        x["student_id"]
        for x in students
    }

    chosen = st.selectbox(
        "👤 เลือกผู้ใช้",
        list(labels),
        key=key
    )

    return labels[chosen]


# =========================================================
# RECOMMENDATION REASON
# =========================================================

def explain_reason(row: dict) -> str:

    parts = []

    if row.get("friend_count", 0):

        friends = ", ".join(
            row.get("friend_names") or []
        )

        parts.append(
            f"เพื่อน {row['friend_count']} คนเคยยืม"
            + (
                f" ({friends})"
                if friends
                else ""
            )
        )

    if row.get("interest_matches", 0):

        cats = ", ".join(
            row.get("matched_categories") or []
        )

        parts.append(
            f"ตรงกับความสนใจ "
            f"{row['interest_matches']} หมวด"
            + (
                f" ({cats})"
                if cats
                else ""
            )
        )

    if row.get("popularity", 0):

        parts.append(
            f"ถูกยืมแล้ว "
            f"{row['popularity']} ครั้ง"
        )

    if row.get("avg_rating", 0):

        parts.append(
            f"คะแนนเฉลี่ย "
            f"{row['avg_rating']:.2f}/5"
        )

    return (
        " • ".join(parts)
        or "แนะนำจากข้อมูลพฤติกรรมโดยรวม"
    )


# =========================================================
# CHECK NEO4J
# =========================================================

require_connection()


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        '<div class="sidebar-title">'
        '📚 GraphBook'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="sidebar-subtitle">'
        'Graph Database Recommendation System'
        '</div>',
        unsafe_allow_html=True
    )

    st.divider()

    page = st.radio(
        "เมนูหลัก",
        [
            "Dashboard",
            "Recommendations",
            "Book Search",
            "Borrow / Rate",
            "Graph Explorer",
            "Admin / Setup",
        ],
    )

    st.divider()

    st.markdown(
        """
        **Technology**

        🟢 Neo4j Aura  
        🔵 Streamlit  
        🐍 Python  
        📊 Graph Database
        """
    )

    st.divider()

    # =====================================================
    # SMALL IMAGE
    # =====================================================

    if os.path.exists(IMAGE_PATH):

        st.image(
            IMAGE_PATH,
            width=90
        )

    else:

        st.caption(
            "⚠️ ไม่พบรูป assets/graphbook.jpg"
        )

    st.caption(
        "Bachelor-level Graph Database Project"
    )


# =========================================================
# HERO
# =========================================================

st.markdown(
    """
    <div class="hero">

        <h1>
            📚 GraphBook Recommendation System
        </h1>

        <p>
            ระบบแนะนำหนังสือด้วย Graph Database
            เพื่อวิเคราะห์ความสัมพันธ์ระหว่างผู้ใช้และหนังสือ
            และนำเสนอหนังสือที่เหมาะสมกับผู้ใช้
        </p>

    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DASHBOARD
# =========================================================

if page == "Dashboard":

    st.markdown(
        '<div class="section-title">'
        '📊 ภาพรวมระบบ'
        '</div>',
        unsafe_allow_html=True
    )

    m = get_dashboard_metrics()

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "👨‍🎓 Students",
        m.get("students", 0)
    )

    c2.metric(
        "📚 Books",
        m.get("books", 0)
    )

    c3.metric(
        "📖 Borrowed",
        m.get("borrows", 0)
    )

    c4.metric(
        "🤝 Friendships",
        m.get("friendships", 0)
    )

    st.divider()

    st.markdown(
        "### 👤 ข้อมูลผู้ใช้"
    )

    student_id = student_selector(
        "dash_student"
    )

    profile = get_profile(
        student_id
    )

    if profile:

        left, right = st.columns(
            [1, 2],
            gap="large"
        )

        with left:

            st.markdown(
                f"### {profile['name']}"
            )

            st.write(
                f"**รหัสนักศึกษา:** "
                f"{profile['student_id']}"
            )

            st.write(
                f"**สาขา:** "
                f"{profile['major']}"
            )

            st.write(
                f"**ชั้นปี:** "
                f"{profile['year']}"
            )

            interests = (
                ", ".join(
                    profile["interests"]
                )
                if profile["interests"]
                else "ยังไม่มี"
            )

            st.write(
                f"**ความสนใจ:** {interests}"
            )

        with right:

            st.markdown(
                "### 📖 ประวัติการยืม"
            )

            if profile["borrowed"]:

                st.dataframe(
                    pd.DataFrame(
                        profile["borrowed"]
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

            else:

                st.info(
                    "ยังไม่มีประวัติการยืม"
                )


# =========================================================
# RECOMMENDATIONS
# =========================================================

elif page == "Recommendations":

    st.subheader(
        "✨ หนังสือที่แนะนำ"
    )

    st.caption(
        "ระบบวิเคราะห์ความสัมพันธ์ใน Graph "
        "เพื่อสร้างคำแนะนำหนังสือ"
    )

    student_id = student_selector(
        "rec_student"
    )

    top_n = st.slider(
        "จำนวนคำแนะนำ",
        3,
        12,
        6
    )

    rows = recommend_books(
        student_id,
        top_n
    )

    st.caption(
        "คะแนนตัวอย่าง = "
        "เพื่อน × 3 + "
        "หมวดความสนใจ × 2 + "
        "ความนิยม × 0.20 + "
        "rating เฉลี่ย × 0.50"
    )

    if not rows:

        st.info(
            "ยังไม่มีคำแนะนำสำหรับผู้ใช้นี้"
        )

    for i, row in enumerate(
        rows,
        start=1
    ):

        authors = ", ".join(
            row.get("authors") or []
        ) or "ไม่ระบุผู้แต่ง"

        categories = ", ".join(
            row.get("categories") or []
        ) or "ไม่ระบุหมวด"

        st.markdown(
            f"""
            <div class="book-card">

                <span class="score-pill">
                    #{i} · Score {row['score']:.2f}
                </span>

                <h3>
                    {row['title']}
                </h3>

                <div class="muted">
                    📘 {row['book_id']}
                    &nbsp; • &nbsp;
                    ✍️ {authors}
                    &nbsp; • &nbsp;
                    🏷️ {categories}
                </div>

                <p>
                    <b>💡 เหตุผล:</b>
                    {explain_reason(row)}
                </p>

            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================================================
# BOOK SEARCH
# =========================================================

elif page == "Book Search":

    st.subheader(
        "🔎 ค้นหาหนังสือ"
    )

    st.caption(
        "ค้นหาหนังสือจากชื่อ ผู้แต่ง หรือหมวดหมู่"
    )

    c1, c2 = st.columns(
        [2, 1],
        gap="medium"
    )

    keyword = c1.text_input(
        "ชื่อหนังสือหรือผู้แต่ง",
        placeholder="เช่น Python, Neo4j, Kanya"
    )

    categories = [
        ""
    ] + list_categories()

    category = c2.selectbox(
        "หมวด",
        categories,
        format_func=lambda x:
            "ทุกหมวด"
            if x == ""
            else x
    )

    rows = search_books(
        keyword,
        category
    )

    st.divider()

    st.write(
        f"📚 พบ **{len(rows)}** รายการ"
    )

    if rows:

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "ไม่พบหนังสือที่ค้นหา"
        )


# =========================================================
# BORROW / RATE
# =========================================================

elif page == "Borrow / Rate":

    st.subheader(
        "📝 บันทึกการยืมและให้คะแนน"
    )

    st.caption(
        "สร้างความสัมพันธ์ BORROWED "
        "ระหว่าง Student และ Book"
    )

    student_id = student_selector(
        "borrow_student"
    )

    books = search_books()

    if not books:

        st.info(
            "ยังไม่มีหนังสือในระบบ"
        )

        st.stop()

    book_labels = {
        f"{b['book_id']} — {b['title']}":
        b["book_id"]
        for b in books
    }

    selected = st.selectbox(
        "📚 หนังสือ",
        list(book_labels)
    )

    borrow_date = st.date_input(
        "📅 วันที่ยืม",
        value=date.today()
    )

    use_rating = st.checkbox(
        "⭐ ให้คะแนนหนังสือพร้อมกัน"
    )

    rating = st.slider(
        "คะแนน",
        1.0,
        5.0,
        4.0,
        0.5,
        disabled=not use_rating,
    )

    st.divider()

    if st.button(
        "💾 บันทึกข้อมูล",
        type="primary",
        use_container_width=True,
    ):

        record_borrow(
            student_id,
            book_labels[selected],
            borrow_date.isoformat(),
            rating
            if use_rating
            else None,
        )

        st.success(
            "✅ บันทึกความสัมพันธ์ BORROWED แล้ว"
        )


# =========================================================
# GRAPH EXPLORER
# =========================================================

elif page == "Graph Explorer":

    st.subheader(
        "🕸️ Graph Explorer"
    )

    st.caption(
        "แสดงความสัมพันธ์ระหว่าง Student, "
        "Book, Category และ Author"
    )

    student_id = student_selector(
        "graph_student"
    )

    rows = graph_neighborhood(
        student_id
    )

    if not rows:

        st.info(
            "ยังไม่มี neighborhood graph"
        )

    else:

        dot = [
            "digraph G {",
            'rankdir="LR";',

            """
            node [
                shape=box,
                style="rounded,filled",
                fillcolor="#f8fafc",
                fontname="Arial"
            ];
            """
        ]

        seen_nodes = set()

        for r in rows:

            nodes = [

                (
                    r["source_id"],
                    r["source_label"],
                    r["source_name"]
                ),

                (
                    r["target_id"],
                    r["target_label"],
                    r["target_name"]
                ),

            ]

            for nid, label, name in nodes:

                if nid not in seen_nodes:

                    safe_name = str(
                        name
                    ).replace(
                        '"',
                        "'"
                    )

                    dot.append(
                        f'"{nid}" '
                        f'[label="{safe_name}\\n:{label}"];'
                    )

                    seen_nodes.add(nid)

            dot.append(
                f'"{r["source_id"]}" '
                f'-> "{r["target_id"]}" '
                f'[label="{r["relationship"]}"];'
            )

        dot.append("}")

        st.graphviz_chart(
            "\n".join(dot),
            use_container_width=True,
        )

        with st.expander(
            "🔍 ดูข้อมูล Edge ที่ใช้วาดกราฟ"
        ):

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )


# =========================================================
# ADMIN / SETUP
# =========================================================

elif page == "Admin / Setup":

    st.subheader(
        "⚙️ Setup ข้อมูลตัวอย่าง"
    )

    st.warning(
        "ปุ่มนี้ไม่ลบข้อมูลเดิม "
        "และใช้ MERGE จึงสามารถกดซ้ำได้"
    )

    st.markdown(
        """
        ### Graph Schema

        **Student**

        `(:Student)-[:FRIEND_OF]-(:Student)`

        **Borrow**

        `(:Student)-[:BORROWED {borrow_date, rating}]->(:Book)`

        **Interest**

        `(:Student)-[:INTERESTED_IN]->(:Category)`

        **Book Category**

        `(:Book)-[:IN_CATEGORY]->(:Category)`

        **Author**

        `(:Author)-[:WROTE]->(:Book)`
        """
    )

    st.divider()

    if st.button(
        "🚀 สร้าง Constraint + Demo Data",
        type="primary",
        use_container_width=True,
    ):

        with st.spinner(
            "กำลังสร้างข้อมูล..."
        ):

            seed_demo_data()

        st.success(
            "✅ สร้างข้อมูลตัวอย่างเรียบร้อยแล้ว"
        )

        st.rerun()


# =========================================================
# FOOTER
# =========================================================

st.markdown(
    """
    <div class="footer">

        📚 GraphBook Recommendation System
        <br>
        Neo4j Aura + Streamlit
        <br>
        Bachelor-level Graph Database Project

    </div>
    """,
    unsafe_allow_html=True,
)
