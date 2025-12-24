import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pathlib import Path
import unicodedata
import io

# ===============================
# 기본 설정
# ===============================
st.set_page_config(
    page_title="🌱 극지식물 최적 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (Streamlit + Plotly)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")

DATA_DIR = Path("data")

SCHOOL_INFO = {
    "송도고": {"ec": 1.0, "color": "#4C78A8"},
    "하늘고": {"ec": 2.0, "color": "#F58518"},  # 최적
    "아라고": {"ec": 4.0, "color": "#54A24B"},
    "동산고": {"ec": 8.0, "color": "#E45756"},
}

# ===============================
# 유틸 함수 (한글 파일명 안전)
# ===============================
def normalize_name(name: str, form: str):
    return unicodedata.normalize(form, name)

def find_file_by_name(directory: Path, target_name: str):
    for p in directory.iterdir():
        if not p.is_file():
            continue
        for form in ["NFC", "NFD"]:
            if normalize_name(p.name, form) == normalize_name(target_name, form):
                return p
    return None

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_environment_data():
    data = {}
    with st.spinner("환경 데이터 로딩 중..."):
        for school in SCHOOL_INFO.keys():
            filename = f"{school}_환경데이터.csv"
            file_path = find_file_by_name(DATA_DIR, filename)
            if file_path is None:
                st.error(f"❌ 환경 데이터 파일을 찾을 수 없음: {filename}")
                return None
            df = pd.read_csv(file_path)
            df["school"] = school
            data[school] = df
    return data

@st.cache_data
def load_growth_data():
    with st.spinner("생육 결과 데이터 로딩 중..."):
        xlsx_path = find_file_by_name(DATA_DIR, "4개교_생육결과데이터.xlsx")
        if xlsx_path is None:
            st.error("❌ 생육 결과 XLSX 파일을 찾을 수 없음")
            return None

        xls = pd.ExcelFile(xlsx_path)
        sheets = {}
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            df["school"] = sheet
            sheets[sheet] = df
    return sheets

env_data = load_environment_data()
growth_data = load_growth_data()

if env_data is None or growth_data is None:
    st.stop()

# ===============================
# 사이드바
# ===============================
st.sidebar.title("🔎 학교 선택")
selected_school = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(SCHOOL_INFO.keys())
)

# ===============================
# 메인 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ===============================
# Tab 1: 실험 개요
# ===============================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write(
        "본 연구는 서로 다른 EC 조건에서 극지식물의 생육 특성을 비교하여 "
        "최적의 EC 농도를 도출하는 것을 목적으로 한다."
    )

    info_rows = []
    total_count = 0
    for school, df in growth_data.items():
        info_rows.append({
            "학교명": school,
            "EC 목표": SCHOOL_INFO[school]["ec"],
            "개체수": len(df),
            "색상": SCHOOL_INFO[school]["color"]
        })
        total_count += len(df)

    info_df = pd.DataFrame(info_rows)
    st.dataframe(info_df, use_container_width=True)

    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", total_count)
    c2.metric("평균 온도", f"{avg_temp:.1f} ℃")
    c3.metric("평균 습도", f"{avg_hum:.1f} %")
    c4.metric("최적 EC", "2.0 (하늘고) ⭐")

# ===============================
# Tab 2: 환경 데이터
# ===============================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg_rows = []
    for school, df in env_data.items():
        avg_rows.append({
            "school": school,
            "temperature": df["temperature"].mean(),
            "humidity": df["humidity"].mean(),
            "ph": df["ph"].mean(),
            "ec": df["ec"].mean(),
            "target_ec": SCHOOL_INFO[school]["ec"]
        })
    avg_df = pd.DataFrame(avg_rows)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_bar(x=avg_df["school"], y=avg_df["temperature"], row=1, col=1)
    fig.add_bar(x=avg_df["school"], y=avg_df["humidity"], row=1, col=2)
    fig.add_bar(x=avg_df["school"], y=avg_df["ph"], row=2, col=1)

    fig.add_bar(
        x=avg_df["school"],
        y=avg_df["ec"],
        name="실측 EC",
        row=2, col=2
    )
    fig.add_bar(
        x=avg_df["school"],
        y=avg_df["target_ec"],
        name="목표 EC",
        row=2, col=2
    )

    fig.update_layout(
        height=700,
        font=PLOTLY_FONT,
        showlegend=True
    )
    st.plotly_chart(fig, use_container_width=True)

    if selected_school != "전체":
        st.subheader(f"{selected_school} 시계열 변화")
        df = env_data[selected_school]

        fig_ts = go.Figure()
        fig_ts.add_scatter(x=df["time"], y=df["temperature"], name="온도")
        fig_ts.add_scatter(x=df["time"], y=df["humidity"], name="습도")
        fig_ts.add_scatter(x=df["time"], y=df["ec"], name="EC")
        fig_ts.add_hline(
            y=SCHOOL_INFO[selected_school]["ec"],
            line_dash="dash",
            annotation_text="목표 EC"
        )
        fig_ts.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig_ts, use_container_width=True)

        with st.expander("📄 환경 데이터 원본"):
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "CSV 다운로드",
                data=csv,
                file_name=f"{selected_school}_환경데이터.csv",
                mime="text/csv"
            )

# ===============================
# Tab 3: 생육 결과
# ===============================
with tab3:
    st.subheader("🥇 EC별 평균 생중량")

    summary = []
    for school, df in growth_data.items():
        summary.append({
            "school": school,
            "ec": SCHOOL_INFO[school]["ec"],
            "weight": df["생중량(g)"].mean(),
            "leaf": df["잎 수(장)"].mean(),
            "shoot": df["지상부 길이(mm)"].mean(),
            "count": len(df)
        })
    sum_df = pd.DataFrame(summary)

    best_row = sum_df.loc[sum_df["weight"].idxmax()]

    st.metric(
        "최대 평균 생중량",
        f"{best_row['weight']:.2f} g",
        delta=f"EC {best_row['ec']} (하늘고 ⭐)"
    )

    fig_bar = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 생중량", "평균 잎 수", "평균 지상부 길이", "개체수"]
    )

    fig_bar.add_bar(x=sum_df["school"], y=sum_df["weight"], row=1, col=1)
    fig_bar.add_bar(x=sum_df["school"], y=sum_df["leaf"], row=1, col=2)
    fig_bar.add_bar(x=sum_df["school"], y=sum_df["shoot"], row=2, col=1)
    fig_bar.add_bar(x=sum_df["school"], y=sum_df["count"], row=2, col=2)

    fig_bar.update_layout(font=PLOTLY_FONT, height=700)
    st.plotly_chart(fig_bar, use_container_width=True)

    all_growth = pd.concat(growth_data.values(), ignore_index=True)

    fig_box = px.box(
        all_growth,
        x="school",
        y="생중량(g)",
        color="school"
    )
    fig_box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_box, use_container_width=True)

    fig_sc1 = px.scatter(
        all_growth,
        x="잎 수(장)",
        y="생중량(g)",
        color="school"
    )
    fig_sc1.update_layout(font=PLOTLY_FONT)

    fig_sc2 = px.scatter(
        all_growth,
        x="지상부 길이(mm)",
        y="생중량(g)",
        color="school"
    )
    fig_sc2.update_layout(font=PLOTLY_FONT)

    st.plotly_chart(fig_sc1, use_container_width=True)
    st.plotly_chart(fig_sc2, use_container_width=True)

    with st.expander("📄 생육 데이터 원본 다운로드"):
        st.dataframe(all_growth, use_container_width=True)
        buffer = io.BytesIO()
        all_growth.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="4개교_생육결과_통합.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
