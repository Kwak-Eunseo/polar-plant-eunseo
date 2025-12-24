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
    page_title="극지식물 최적의 EC 농도 연구",
    layout="wide"
)

# 한글 폰트 (Streamlit)
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(
    family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"
)

DATA_DIR = Path("data")

SCHOOL_INFO = {
    "송도고": 1.0,
    "하늘고": 2.0,  # 최적
    "아라고": 4.0,
    "동산고": 8.0,
}

# ===============================
# 한글 파일명 안전 처리
# ===============================
def normalize(text, form):
    return unicodedata.normalize(form, text)

def find_file(directory: Path, filename: str):
    for p in directory.iterdir():
        if not p.is_file():
            continue
        for form in ["NFC", "NFD"]:
            if normalize(p.name, form) == normalize(filename, form):
                return p
    return None

# ===============================
# 데이터 로딩
# ===============================
@st.cache_data
def load_env_data():
    with st.spinner("환경 데이터 로딩 중..."):
        env = {}
        for school in SCHOOL_INFO:
            fname = f"{school}_환경데이터.csv"
            path = find_file(DATA_DIR, fname)
            if path is None:
                st.error(f"❌ 환경 데이터 없음: {fname}")
                return None
            df = pd.read_csv(path)
            df["school"] = school
            env[school] = df
    return env

@st.cache_data
def load_growth_data():
    with st.spinner("생육 데이터 로딩 중..."):
        path = find_file(DATA_DIR, "4개교_생육결과데이터.xlsx")
        if path is None:
            st.error("❌ 생육 결과 XLSX 파일 없음")
            return None

        xls = pd.ExcelFile(path)
        data = {}
        for sheet in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet)
            df["school"] = sheet
            data[sheet] = df
    return data

env_data = load_env_data()
growth_data = load_growth_data()

if env_data is None or growth_data is None:
    st.stop()

# ===============================
# 사이드바
# ===============================
st.sidebar.title("학교 선택")
school_selected = st.sidebar.selectbox(
    "학교",
    ["전체"] + list(SCHOOL_INFO.keys())
)

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적의 EC 농도 연구")

tab1, tab2, tab3 = st.tabs([
    "📖 실험 개요",
    "🌡️ EC · 온도 조건",
    "📊 생육 결과 분석"
])

# ===============================
# Tab 1: 실험 개요
# ===============================
with tab1:
    st.subheader("연구 목적 및 핵심 가설")

    st.markdown("""
- **EC 4.0 + 저온 환경**에서 극지식물의 생육이 가장 활발하게 나타난다.
- **고EC 조건(EC 8.0)**은 온도와 무관하게 생육을 저해할 수 있다.
- **전처리 없이 단순 평균을 사용하는 경우**, 연구 결론에 큰 영향을 미칠 수 있다.
""")

    info = []
    for s, df in growth_data.items():
        info.append({
            "학교": s,
            "EC 조건": SCHOOL_INFO[s],
            "개체 수": len(df)
        })

    st.dataframe(pd.DataFrame(info), use_container_width=True)

# ===============================
# Tab 2: EC & 온도 산점도
# ===============================
with tab2:
    st.subheader("학교별 EC–온도 조건 분포")

    env_all = pd.concat(env_data.values(), ignore_index=True)

    fig_scatter = px.scatter(
        env_all,
        x="temperature",
        y="ec",
        color="school",
        opacity=0.7,
        labels={
            "temperature": "온도 (℃)",
            "ec": "EC"
        }
    )

    fig_scatter.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.caption("▶ 학교별 EC 수준과 온도 분포를 직관적으로 비교")

# ===============================
# Tab 3: 생육 결과 분석
# ===============================
with tab3:
    st.subheader("EC·온도 조건별 생중량 비교")

    # 환경 평균 + 생육 평균 결합
    env_mean = []
    for s, df in env_data.items():
        env_mean.append({
            "school": s,
            "temperature": df["temperature"].mean(),
            "ec": df["ec"].mean()
        })

    env_mean_df = pd.DataFrame(env_mean)

    growth_mean = []
    for s, df in growth_data.items():
        growth_mean.append({
            "school": s,
            "weight": df["생중량(g)"].mean()
        })

    growth_mean_df = pd.DataFrame(growth_mean)

    merged = pd.merge(env_mean_df, growth_mean_df, on="school")

    fig_bubble = px.scatter(
        merged,
        x="temperature",
        y="weight",
        size="ec",
        color="school",
        labels={
            "temperature": "평균 온도 (℃)",
            "weight": "평균 생중량 (g)",
            "ec": "EC"
        }
    )

    fig_bubble.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_bubble, use_container_width=True)

    st.markdown("⭐ **EC 4.0 (아라고)** 조건에서 저온 대비 생중량이 가장 높게 나타남")

    # ===============================
    # 상관관계 히트맵
    # ===============================
    st.subheader("온도 · EC · 생중량 상관관계")

    corr_df = merged[["temperature", "ec", "weight"]].corr()

    fig_heat = go.Figure(
        data=go.Heatmap(
            z=corr_df.values,
            x=corr_df.columns,
            y=corr_df.columns,
            colorscale="RdBu",
            zmid=0
        )
    )

    fig_heat.update_layout(
        font=PLOTLY_FONT,
        height=500
    )

    st.plotly_chart(fig_heat, use_container_width=True)

    # ===============================
    # 다운로드
    # ===============================
    with st.expander("📥 분석 데이터 다운로드"):
        buffer = io.BytesIO()
        merged.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="EC_온도_생중량_분석결과.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
