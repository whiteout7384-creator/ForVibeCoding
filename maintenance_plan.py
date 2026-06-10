import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="유지보수 계획 수립", layout="wide", initial_sidebar_state="expanded")

# ─────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────
TODAY = pd.Timestamp("2025-12-31")

INSPECTION_RESULT_SCORES = {"정상": 0, "주의": 10, "경고": 20, "불량": 30}

DEFAULT_CYCLES = {
    "펌프": 30, "모터": 45, "냉각기": 60, "컴프레서": 30,
    "밸브": 90, "센서": 90, "분사기": 60, "제어판": 120,
    "변압기": 180, "열교환기": 60,
}

RISK_COLORS = {"긴급": "#e74c3c", "위험": "#e67e22", "주의": "#f1c40f", "양호": "#2ecc71"}
RISK_ORDER = ["긴급", "위험", "주의", "양호"]

MAINT_AVG_COST = {"예방정비": 150000, "사후정비": 250000, "개선정비": 300000, "응급정비": 400000}

# ─────────────────────────────────────────────
# 데이터 로드
# ─────────────────────────────────────────────
@st.cache_data
def load_all_data():
    master      = pd.read_csv("data/기기마스터.csv",      encoding="utf-8-sig")
    inspection  = pd.read_csv("data/점검기록.csv",        encoding="utf-8-sig")
    maintenance = pd.read_csv("data/유지보수기록.csv",    encoding="utf-8-sig")
    replacement = pd.read_csv("data/부품교체이력.csv",    encoding="utf-8-sig")
    status      = pd.read_csv("data/월별기기상태.csv",    encoding="utf-8-sig")
    history     = pd.read_csv("data/기기이력카드.csv",    encoding="utf-8-sig")

    inspection["점검일자"]      = pd.to_datetime(inspection["점검일자"])
    maintenance["유지보수일자"] = pd.to_datetime(maintenance["유지보수일자"])
    replacement["교체일자"]     = pd.to_datetime(replacement["교체일자"])
    master["설치일자"]          = pd.to_datetime(master["설치일자"])

    return {
        "master": master, "inspection": inspection,
        "maintenance": maintenance, "replacement": replacement,
        "status": status, "history": history,
    }

# ─────────────────────────────────────────────
# 위험도 스코어링 함수군
# ─────────────────────────────────────────────
def score_inspection_result(device_id: str, inspection_df: pd.DataFrame) -> float:
    """A. 최근 5회 점검결과 가중평균 (최대 30점)"""
    rows = inspection_df[inspection_df["기기ID"] == device_id].sort_values("점검일자", ascending=False).head(5)
    if rows.empty:
        return 15.0
    weights = np.array([1.0, 0.8, 0.6, 0.4, 0.2][: len(rows)])
    scores  = rows["점검결과"].map(INSPECTION_RESULT_SCORES).fillna(10).values
    return float(np.dot(scores, weights) / weights.sum())


def score_age(install_date: pd.Timestamp) -> float:
    """B. 설치 경과연수 (최대 20점)"""
    years = (TODAY - install_date).days / 365
    if years >= 5:   return 20.0
    elif years >= 4: return 16.0
    elif years >= 3: return 12.0
    elif years >= 2: return 8.0
    else:            return 4.0


def score_error_frequency(device_id: str, status_df: pd.DataFrame) -> float:
    """C. 최근 6개월 평균 에러발생횟수 (최대 25점)"""
    rows = status_df[status_df["기기ID"] == device_id].sort_values("연월", ascending=False).head(6)
    if rows.empty:
        return 6.0
    avg = rows["에러발생횟수"].mean()
    if avg >= 4:   return 25.0
    elif avg >= 3: return 18.0
    elif avg >= 2: return 12.0
    elif avg >= 1: return 6.0
    else:          return 0.0


def score_maintenance_history(device_id: str, maintenance_df: pd.DataFrame) -> float:
    """D. 응급정비 비율 + 미완료 패널티 (최대 15점)"""
    rows = maintenance_df[maintenance_df["기기ID"] == device_id]
    if rows.empty:
        return 0.0
    emergency_ratio = (rows["유지보수유형"] == "응급정비").sum() / len(rows)
    incomplete      = rows["완료상태"].isin(["진행중", "예정"]).sum()
    return min(emergency_ratio * 20 + incomplete * 3, 15.0)


def score_inspection_gap(device_id: str, inspection_df: pd.DataFrame) -> float:
    """E. 마지막 점검 후 경과일 (최대 10점)"""
    rows = inspection_df[inspection_df["기기ID"] == device_id]
    if rows.empty:
        return 10.0
    days = (TODAY - rows["점검일자"].max()).days
    if days >= 180: return 10.0
    elif days >= 90: return 7.0
    elif days >= 60: return 5.0
    elif days >= 30: return 2.0
    else:            return 0.0


def classify_risk_level(score: float) -> str:
    if score >= 70: return "긴급"
    elif score >= 50: return "위험"
    elif score >= 30: return "주의"
    else: return "양호"


def generate_action_reason(row: pd.Series) -> str:
    parts = []
    if row["A_점검결과"] >= 20:
        parts.append(f"최근 점검 결과 불량/경고({row['A_점검결과']:.0f}점)")
    if row["C_에러발생"] >= 18:
        parts.append(f"월 평균 에러 빈번({row['C_에러발생']:.0f}점)")
    if row["B_경과연수"] >= 16:
        parts.append(f"설치 후 4년 이상 경과({row['B_경과연수']:.0f}점)")
    if row["D_유지보수이력"] >= 10:
        parts.append(f"응급정비 비율 높음({row['D_유지보수이력']:.0f}점)")
    if row["E_점검미실시"] >= 7:
        parts.append(f"장기 미점검({row['E_점검미실시']:.0f}점)")
    return " / ".join(parts) if parts else "정기 점검 대상"


def recommend_maintenance_type(risk_level: str, recent_result: str) -> dict:
    if risk_level == "긴급" or recent_result == "불량":
        return {"type": "응급정비", "timing": "즉시"}
    elif risk_level == "위험" or recent_result == "경고":
        return {"type": "사후정비", "timing": "1주일 내"}
    elif risk_level == "주의" or recent_result == "주의":
        return {"type": "예방정비", "timing": "1개월 내"}
    else:
        return {"type": "예방정비", "timing": "정기 주기 유지"}


@st.cache_data
def build_risk_dataframe(_master_df, _inspection_df, _maintenance_df, _status_df):
    """전체 기기 위험도 DataFrame 구축"""
    records = []
    for _, row in _master_df.iterrows():
        did = row["기기ID"]
        a = score_inspection_result(did, _inspection_df)
        b = score_age(row["설치일자"])
        c = score_error_frequency(did, _status_df)
        d = score_maintenance_history(did, _maintenance_df)
        e = score_inspection_gap(did, _inspection_df)
        total = a + b + c + d + e
        level = classify_risk_level(total)

        insp_rows = _inspection_df[_inspection_df["기기ID"] == did].sort_values("점검일자", ascending=False)
        recent_result = insp_rows.iloc[0]["점검결과"] if not insp_rows.empty else "미점검"
        last_insp_date = insp_rows.iloc[0]["점검일자"] if not insp_rows.empty else pd.NaT
        maint_rec = recommend_maintenance_type(level, recent_result)

        records.append({
            "기기ID": did,
            "기기명": row["기기명"],
            "기기유형": row["기기유형"],
            "설치위치": row["설치위치"],
            "제조사": row["제조사"],
            "설치일자": row["설치일자"],
            "기기상태": row["기기상태"],
            "위험도점수": round(total, 1),
            "위험등급": level,
            "A_점검결과": round(a, 1),
            "B_경과연수": round(b, 1),
            "C_에러발생": round(c, 1),
            "D_유지보수이력": round(d, 1),
            "E_점검미실시": round(e, 1),
            "최근점검결과": recent_result,
            "최근점검일자": last_insp_date,
            "권고유지보수유형": maint_rec["type"],
            "권고시기": maint_rec["timing"],
        })

    df = pd.DataFrame(records).sort_values("위험도점수", ascending=False).reset_index(drop=True)
    df["조치근거"] = df.apply(generate_action_reason, axis=1)
    df["순위"] = df.index + 1
    return df


# ─────────────────────────────────────────────
# 스케줄 계산 함수군
# ─────────────────────────────────────────────
def calculate_next_inspection_date(device_id: str, eq_type: str, risk_level: str, inspection_df: pd.DataFrame) -> pd.Timestamp:
    rows = inspection_df[inspection_df["기기ID"] == device_id].sort_values("점검일자")
    if len(rows) >= 2:
        gaps = rows["점검일자"].diff().dropna().dt.days.values
        w = np.array([0.4, 0.3, 0.15, 0.1, 0.05][: len(gaps)])
        w = w / w.sum()
        cycle = int(np.dot(gaps[-len(w):], w))
    else:
        cycle = DEFAULT_CYCLES.get(eq_type, 60)

    if risk_level in ("긴급", "위험"):
        cycle = max(int(cycle * 0.7), 7)

    last_date = rows.iloc[-1]["점검일자"] if not rows.empty else TODAY
    return last_date + pd.Timedelta(days=cycle)


@st.cache_data
def build_schedule_dataframe(_risk_df, _inspection_df):
    records = []
    for _, row in _risk_df.iterrows():
        next_date = calculate_next_inspection_date(
            row["기기ID"], row["기기유형"], row["위험등급"], _inspection_df
        )
        days_left = (next_date - TODAY).days
        records.append({
            "기기ID": row["기기ID"],
            "기기명": row["기기명"],
            "기기유형": row["기기유형"],
            "설치위치": row["설치위치"],
            "위험등급": row["위험등급"],
            "최근점검일자": row["최근점검일자"],
            "다음점검예정일": next_date,
            "잔여일수": days_left,
        })
    return pd.DataFrame(records).sort_values("다음점검예정일")


# ─────────────────────────────────────────────
# 비용/부품 예측 함수군
# ─────────────────────────────────────────────
def estimate_maintenance_cost(device_id: str, maint_type: str, maintenance_df: pd.DataFrame) -> int:
    rows = maintenance_df[
        (maintenance_df["기기ID"] == device_id) &
        (maintenance_df["유지보수유형"] == maint_type)
    ].sort_values("유지보수일자", ascending=False).head(3)
    if len(rows) >= 3:
        return int(rows["비용(원)"].mean())
    type_avg = maintenance_df[maintenance_df["유지보수유형"] == maint_type]["비용(원)"].mean()
    return int(type_avg) if not np.isnan(type_avg) else MAINT_AVG_COST.get(maint_type, 200000)


@st.cache_data
def build_maintenance_plan(_risk_df, _maintenance_df, plan_months: int):
    plan_end = TODAY + pd.DateOffset(months=plan_months)
    records = []
    for _, row in _risk_df.iterrows():
        cost = estimate_maintenance_cost(row["기기ID"], row["권고유지보수유형"], _maintenance_df)
        records.append({
            "기기ID": row["기기ID"],
            "기기명": row["기기명"],
            "기기유형": row["기기유형"],
            "설치위치": row["설치위치"],
            "위험등급": row["위험등급"],
            "위험도점수": row["위험도점수"],
            "권고유지보수유형": row["권고유지보수유형"],
            "권고시기": row["권고시기"],
            "예상비용(원)": cost,
            "조치근거": row["조치근거"],
        })
    return pd.DataFrame(records)


@st.cache_data
def build_parts_prediction(_replacement_df, plan_months: int):
    plan_end = TODAY + pd.DateOffset(months=plan_months)

    part_avg_cycle = (
        _replacement_df.sort_values(["기기ID", "부품명", "교체일자"])
        .groupby(["기기ID", "부품명"])["교체일자"]
        .apply(lambda x: x.diff().dt.days.mean() if len(x) > 1 else np.nan)
        .reset_index(name="평균주기(일)")
    )
    global_avg = _replacement_df.groupby("부품명").apply(
        lambda x: x.sort_values("교체일자")["교체일자"].diff().dt.days.mean()
    ).reset_index(name="전체평균주기(일)")

    latest_repl = _replacement_df.sort_values("교체일자").groupby(["기기ID", "부품명"]).tail(1)
    latest_repl = latest_repl[["기기ID", "부품명", "교체일자", "부품비(원)", "공임(원)"]]

    merged = latest_repl.merge(part_avg_cycle, on=["기기ID", "부품명"], how="left")
    merged = merged.merge(global_avg, on="부품명", how="left")

    merged["추정주기(일)"] = merged["평균주기(일)"].fillna(merged["전체평균주기(일)"])
    merged["추정주기(일)"] = merged["추정주기(일)"].fillna(365)
    merged["다음교체예측일"] = merged["교체일자"] + pd.to_timedelta(merged["추정주기(일)"], unit="D")
    merged["예상총비용(원)"] = merged["부품비(원)"] + merged["공임(원)"]
    merged["잔여일수"] = (merged["다음교체예측일"] - TODAY).dt.days
    merged["교체긴급도"] = merged["잔여일수"].apply(
        lambda d: "긴급" if d <= 30 else ("예정" if d <= 90 else "여유")
    )

    return merged[merged["다음교체예측일"] <= plan_end].sort_values("다음교체예측일")


# ─────────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────────
def render_sidebar(master_df):
    with st.sidebar:
        st.header("⚙️ 필터 설정")

        # 전체 선택/해제 체크박스
        all_locations = sorted(master_df["설치위치"].unique().tolist())
        all_eq_types  = sorted(master_df["기기유형"].unique().tolist())

        st.markdown("**📍 설치 위치**")
        select_all_loc = st.checkbox("전체 선택", value=True, key="all_loc")
        locations = st.multiselect(
            "위치 선택",
            options=all_locations,
            default=all_locations if select_all_loc else [],
            label_visibility="collapsed",
        )
        if not locations:
            locations = all_locations  # 아무것도 선택 안 하면 전체 적용

        st.markdown("**🔧 기기 유형**")
        select_all_type = st.checkbox("전체 선택", value=True, key="all_type")
        eq_types = st.multiselect(
            "유형 선택",
            options=all_eq_types,
            default=all_eq_types if select_all_type else [],
            label_visibility="collapsed",
        )
        if not eq_types:
            eq_types = all_eq_types

        st.markdown("**⚠️ 위험도 등급**")
        risk_filter = st.radio(
            "등급 선택",
            ["전체", "주의 이상", "위험 이상", "긴급만"],
            horizontal=False,
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.markdown("**📅 계획 기간**")
        plan_months = st.select_slider(
            "기간 선택",
            options=[1, 2, 3, 6],
            value=3,
            format_func=lambda x: f"{x}개월",
            label_visibility="collapsed",
        )
        st.info(f"계획 기간: **{plan_months}개월**  \n기준일: {TODAY.strftime('%Y-%m-%d')}")

    return {
        "locations": locations,
        "eq_types": eq_types,
        "risk_filter": risk_filter,
        "plan_months": plan_months,
    }


def apply_filters(risk_df, filters):
    df = risk_df.copy()
    df = df[df["설치위치"].isin(filters["locations"])]
    df = df[df["기기유형"].isin(filters["eq_types"])]
    rf = filters["risk_filter"]
    if rf == "주의 이상":
        df = df[df["위험등급"].isin(["주의", "위험", "긴급"])]
    elif rf == "위험 이상":
        df = df[df["위험등급"].isin(["위험", "긴급"])]
    elif rf == "긴급만":
        df = df[df["위험등급"] == "긴급"]
    return df.reset_index(drop=True)


# ─────────────────────────────────────────────
# Tab 1 – 위험도 우선순위
# ─────────────────────────────────────────────
def render_tab_risk_priority(df):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("전체 기기", len(df))
    c2.metric("긴급", len(df[df["위험등급"] == "긴급"]), delta=None)
    c3.metric("위험", len(df[df["위험등급"] == "위험"]))
    c4.metric("주의", len(df[df["위험등급"] == "주의"]))

    st.markdown("---")

    top20 = df.head(20).sort_values("위험도점수")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("위험도 상위 20개 기기")
        fig = px.bar(
            top20, x="위험도점수", y="기기명", orientation="h",
            color="위험등급",
            color_discrete_map=RISK_COLORS,
            category_orders={"위험등급": RISK_ORDER},
            labels={"위험도점수": "점수", "기기명": ""},
            height=500,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("위험등급 분포")
        level_cnt = df["위험등급"].value_counts().reindex(RISK_ORDER).dropna()
        fig2 = px.pie(
            values=level_cnt.values, names=level_cnt.index,
            color=level_cnt.index,
            color_discrete_map=RISK_COLORS,
            hole=0.45,
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("인자별 점수 기여도 (상위 15개)")
    top15 = df.head(15)
    fig3 = go.Figure()
    factors = {
        "A_점검결과": "점검결과(A)", "B_경과연수": "경과연수(B)",
        "C_에러발생": "에러발생(C)", "D_유지보수이력": "유지보수이력(D)", "E_점검미실시": "점검미실시(E)",
    }
    colors = ["#e74c3c", "#e67e22", "#f39c12", "#3498db", "#9b59b6"]
    for (col, label), color in zip(factors.items(), colors):
        fig3.add_trace(go.Bar(name=label, x=top15["기기명"], y=top15[col], marker_color=color))
    fig3.update_layout(barmode="stack", xaxis_tickangle=-30, height=400)
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("우선순위 액션 테이블")
    display_cols = ["순위", "기기ID", "기기명", "설치위치", "위험등급", "위험도점수",
                    "최근점검결과", "권고유지보수유형", "권고시기", "조치근거"]
    st.dataframe(df[display_cols], use_container_width=True, height=400)

    csv = df[display_cols].to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📥 우선순위 목록 CSV 다운로드", data=csv, file_name="위험도우선순위.csv", mime="text/csv")


# ─────────────────────────────────────────────
# Tab 2 – 점검 스케줄
# ─────────────────────────────────────────────
def render_tab_inspection_schedule(filtered_risk_df, inspection_df, plan_months):
    schedule_df = build_schedule_dataframe(filtered_risk_df, inspection_df)
    plan_end = TODAY + pd.DateOffset(months=plan_months)
    upcoming = schedule_df[schedule_df["다음점검예정일"] <= plan_end].copy()

    # ── 긴급도 구분 컬럼 추가
    def urgency(days):
        if days < 0:    return "⛔ 기한초과"
        elif days <= 14: return "🔴 14일 이내"
        elif days <= 30: return "🟠 30일 이내"
        elif days <= 60: return "🟡 60일 이내"
        else:            return "🟢 여유"

    upcoming["긴급도"] = upcoming["잔여일수"].apply(urgency)
    urgency_order = ["⛔ 기한초과", "🔴 14일 이내", "🟠 30일 이내", "🟡 60일 이내", "🟢 여유"]
    urgency_colors = {
        "⛔ 기한초과": "#c0392b",
        "🔴 14일 이내": "#e74c3c",
        "🟠 30일 이내": "#e67e22",
        "🟡 60일 이내": "#f1c40f",
        "🟢 여유":      "#2ecc71",
    }

    # ── 상단 KPI 카드
    overdue  = len(upcoming[upcoming["잔여일수"] < 0])
    urgent14 = len(upcoming[(upcoming["잔여일수"] >= 0) & (upcoming["잔여일수"] <= 14)])
    urgent30 = len(upcoming[(upcoming["잔여일수"] > 14) & (upcoming["잔여일수"] <= 30)])
    normal   = len(upcoming[upcoming["잔여일수"] > 30])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⛔ 기한 초과",  overdue,  delta=None)
    c2.metric("🔴 14일 이내", urgent14, delta=None)
    c3.metric("🟠 30일 이내", urgent30, delta=None)
    c4.metric("🟢 여유",      normal,   delta=None)

    st.markdown("---")

    # ── 월별 점검 부하 + 긴급도 스택 바
    st.subheader("📅 월별 점검 부하")
    if not upcoming.empty:
        upcoming["연월"] = upcoming["다음점검예정일"].dt.to_period("M").astype(str)
        monthly_stack = (
            upcoming.groupby(["연월", "긴급도"])
            .size()
            .reset_index(name="건수")
        )
        threshold = 40
        fig_bar = px.bar(
            monthly_stack, x="연월", y="건수", color="긴급도",
            color_discrete_map=urgency_colors,
            category_orders={"긴급도": urgency_order},
            labels={"연월": "월", "건수": "점검 건수"},
            height=320,
        )
        fig_bar.add_hline(
            y=threshold, line_dash="dash", line_color="#7f8c8d",
            annotation_text=f"부하 임계치 ({threshold}건)",
            annotation_position="top right",
        )
        fig_bar.update_layout(bargap=0.25, legend_title_text="긴급도")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # ── 설치위치 × 긴급도 히트맵
    col1, col2 = st.columns([1.2, 1])
    with col1:
        st.subheader("📍 위치별 점검 현황")
        if not upcoming.empty:
            pivot = (
                upcoming.groupby(["설치위치", "긴급도"])
                .size()
                .unstack(fill_value=0)
                .reindex(columns=[c for c in urgency_order if c in upcoming["긴급도"].unique()], fill_value=0)
            )
            fig_heat = px.imshow(
                pivot,
                color_continuous_scale=["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#c0392b"],
                text_auto=True,
                labels={"x": "긴급도", "y": "설치위치", "color": "건수"},
                aspect="auto",
                height=300,
            )
            fig_heat.update_coloraxes(showscale=False)
            st.plotly_chart(fig_heat, use_container_width=True)

    with col2:
        st.subheader("⚠️ 긴급도 분포")
        if not upcoming.empty:
            urgency_cnt = upcoming["긴급도"].value_counts().reindex(
                [u for u in urgency_order if u in upcoming["긴급도"].values]
            ).dropna()
            fig_pie = px.pie(
                values=urgency_cnt.values, names=urgency_cnt.index,
                color=urgency_cnt.index,
                color_discrete_map=urgency_colors,
                hole=0.5,
                height=300,
            )
            fig_pie.update_traces(textposition="outside", textinfo="label+value")
            fig_pie.update_layout(showlegend=False, margin=dict(t=20, b=20))
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # ── 점검 스케줄 상세 테이블 (색상 강조)
    st.subheader("📋 점검 스케줄 상세")

    if not upcoming.empty:
        # 긴급도 필터
        urgency_filter = st.multiselect(
            "긴급도 필터",
            options=urgency_order,
            default=urgency_order,
            key="urgency_filter",
        )
        disp = upcoming[upcoming["긴급도"].isin(urgency_filter)].copy()
        disp = disp.sort_values("잔여일수")

        disp["다음점검예정일"] = disp["다음점검예정일"].dt.strftime("%Y-%m-%d")
        disp["최근점검일자"]  = pd.to_datetime(disp["최근점검일자"]).dt.strftime("%Y-%m-%d")
        disp["잔여일수표시"]  = disp["잔여일수"].apply(
            lambda d: f"D{d:+d}" if d != 0 else "D-Day"
        )

        show_cols = ["기기ID", "기기명", "기기유형", "설치위치", "위험등급",
                     "긴급도", "최근점검일자", "다음점검예정일", "잔여일수표시"]

        styled = (
            disp[show_cols]
            .style
            .apply(lambda row: [
                "background-color: #fadbd8" if row["긴급도"] in ("⛔ 기한초과", "🔴 14일 이내")
                else "background-color: #fdebd0" if row["긴급도"] == "🟠 30일 이내"
                else "background-color: #fef9e7" if row["긴급도"] == "🟡 60일 이내"
                else "" for _ in row
            ], axis=1)
        )
        st.dataframe(styled, use_container_width=True, height=420)

        csv = disp[show_cols].to_csv(index=False, encoding="utf-8-sig")
        st.download_button("📥 스케줄 CSV 다운로드", data=csv,
                           file_name="점검스케줄.csv", mime="text/csv")
    else:
        st.info("해당 기간 내 점검 예정 기기가 없습니다.")


# ─────────────────────────────────────────────
# Tab 3 – 유지보수 계획서
# ─────────────────────────────────────────────
def render_tab_maintenance_plan(filtered_risk_df, maintenance_df, plan_months):
    plan_df = build_maintenance_plan(filtered_risk_df, maintenance_df, plan_months)

    total_cost = plan_df["예상비용(원)"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("계획 기기 수", len(plan_df))
    c2.metric("예상 총 비용", f"{total_cost:,.0f}원")
    c3.metric("기기당 평균 비용", f"{total_cost / max(len(plan_df), 1):,.0f}원")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("권고 유지보수 유형 분포")
        type_cnt = plan_df["권고유지보수유형"].value_counts()
        fig = px.pie(values=type_cnt.values, names=type_cnt.index, hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("유지보수유형별 평균 예상비용")
        avg_cost = plan_df.groupby("권고유지보수유형")["예상비용(원)"].mean().reset_index()
        fig2 = px.bar(avg_cost, x="권고유지보수유형", y="예상비용(원)", color="권고유지보수유형",
                      labels={"권고유지보수유형": "유형", "예상비용(원)": "평균 비용(원)"})
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("위치별 유지보수 계획 히트맵")
    heatmap_data = plan_df.groupby(["설치위치", "권고시기"]).size().unstack(fill_value=0)
    if not heatmap_data.empty:
        fig3 = px.imshow(
            heatmap_data, color_continuous_scale="Reds",
            labels={"x": "권고시기", "y": "설치위치", "color": "건수"},
            text_auto=True,
        )
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("유지보수 계획 상세서")
    display_cols = ["기기ID", "기기명", "기기유형", "설치위치", "위험등급", "위험도점수",
                    "권고유지보수유형", "권고시기", "예상비용(원)", "조치근거"]
    st.dataframe(plan_df[display_cols], use_container_width=True, height=400)

    csv = plan_df[display_cols].to_csv(index=False, encoding="utf-8-sig")
    st.download_button("📥 유지보수 계획서 CSV 다운로드", data=csv, file_name="유지보수계획서.csv", mime="text/csv")


# ─────────────────────────────────────────────
# Tab 4 – 부품 교체 예측
# ─────────────────────────────────────────────
def render_tab_parts_prediction(filtered_risk_df, replacement_df, plan_months):
    filt_repl = replacement_df[replacement_df["기기ID"].isin(filtered_risk_df["기기ID"])]
    parts_df = build_parts_prediction(filt_repl, plan_months)

    c1, c2, c3 = st.columns(3)
    c1.metric(f"{plan_months}개월 내 교체 예측", len(parts_df))
    c2.metric("30일 내 긴급 교체", len(parts_df[parts_df["교체긴급도"] == "긴급"]))
    c3.metric("예상 총 부품비", f"{parts_df['예상총비용(원)'].sum():,.0f}원" if not parts_df.empty else "0원")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("부품유형별 평균 교체 주기")
        if not filt_repl.empty:
            sorted_repl = filt_repl.sort_values(["기기ID", "부품명", "교체일자"])
            part_cycle = (
                sorted_repl.groupby(["기기ID", "부품명"])["교체일자"]
                .apply(lambda x: x.diff().dt.days.mean())
                .reset_index(name="주기(일)")
            )
            global_cycle = part_cycle.groupby("부품명")["주기(일)"].mean().reset_index().dropna()
            fig = px.bar(global_cycle.sort_values("주기(일)"), x="부품명", y="주기(일)",
                         labels={"부품명": "부품", "주기(일)": "평균 교체 주기(일)"})
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("교체 사유 트렌드")
        if not filt_repl.empty:
            filt_repl2 = filt_repl.copy()
            filt_repl2["연월"] = filt_repl2["교체일자"].dt.to_period("M").astype(str)
            trend = filt_repl2.groupby(["연월", "교체사유"]).size().reset_index(name="건수")
            fig2 = px.line(trend, x="연월", y="건수", color="교체사유", markers=True,
                           labels={"연월": "월", "건수": "교체 건수"})
            st.plotly_chart(fig2, use_container_width=True)

    if not parts_df.empty:
        st.subheader("부품 교체 예측 목록")
        display = parts_df[["기기ID", "부품명", "교체일자", "추정주기(일)", "다음교체예측일", "예상총비용(원)", "교체긴급도"]].copy()
        display["교체일자"]       = display["교체일자"].dt.strftime("%Y-%m-%d")
        display["다음교체예측일"] = display["다음교체예측일"].dt.strftime("%Y-%m-%d")
        st.dataframe(display, use_container_width=True, height=350)
    else:
        st.info(f"{plan_months}개월 내 교체 예측 부품이 없습니다.")


# ─────────────────────────────────────────────
# Tab 5 – 비용/리소스 계획
# ─────────────────────────────────────────────
def render_tab_cost_resource(filtered_risk_df, maintenance_df, replacement_df, plan_months):
    plan_df = build_maintenance_plan(filtered_risk_df, maintenance_df, plan_months)
    filt_repl = replacement_df[replacement_df["기기ID"].isin(filtered_risk_df["기기ID"])]
    parts_df = build_parts_prediction(filt_repl, plan_months)

    st.subheader("월별 예상 비용 vs 실적 비교")
    actual_monthly = (
        maintenance_df[maintenance_df["기기ID"].isin(filtered_risk_df["기기ID"])]
        .copy()
    )
    actual_monthly["연월"] = actual_monthly["유지보수일자"].dt.to_period("M").astype(str)
    actual_agg = actual_monthly.groupby("연월")["비용(원)"].sum().reset_index(name="실적비용")

    plan_months_list = [
        (TODAY + pd.DateOffset(months=i)).strftime("%Y-%m") for i in range(1, plan_months + 1)
    ]
    monthly_plan_cost = plan_df.groupby("권고유지보수유형")["예상비용(원)"].sum()
    total_plan_cost = monthly_plan_cost.sum()
    forecast_df = pd.DataFrame({
        "연월": plan_months_list,
        "예상비용": [total_plan_cost / plan_months] * plan_months,
    })

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=actual_agg["연월"], y=actual_agg["실적비용"],
        mode="lines+markers", name="실적 비용", line=dict(color="#3498db")
    ))
    fig.add_trace(go.Scatter(
        x=forecast_df["연월"], y=forecast_df["예상비용"],
        mode="lines+markers", name="예상 비용", line=dict(color="#e74c3c", dash="dash")
    ))
    fig.update_layout(xaxis_title="월", yaxis_title="비용(원)", height=350)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("위험등급별 비용 구성")
        cost_by_level = plan_df.groupby("위험등급")["예상비용(원)"].sum().reset_index()
        fig2 = px.bar(cost_by_level, x="위험등급", y="예상비용(원)",
                      color="위험등급", color_discrete_map=RISK_COLORS,
                      category_orders={"위험등급": RISK_ORDER})
        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        st.subheader("유지보수유형별 비용 비중")
        type_cost = plan_df.groupby("권고유지보수유형")["예상비용(원)"].sum().reset_index()
        fig3 = px.pie(type_cost, values="예상비용(원)", names="권고유지보수유형", hole=0.4)
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("월별 예산 계획 요약")
    budget_rows = []
    prev_cost = None
    for m in plan_months_list:
        mc = total_plan_cost / plan_months
        parts_cost = parts_df["예상총비용(원)"].sum() / plan_months if not parts_df.empty else 0
        total = mc + parts_cost
        delta = f"+{(total - prev_cost):,.0f}" if prev_cost else "-"
        budget_rows.append({
            "연월": m,
            "유지보수 예상비용(원)": f"{mc:,.0f}",
            "부품교체 예상비용(원)": f"{parts_cost:,.0f}",
            "합계(원)": f"{total:,.0f}",
            "전월대비": delta,
        })
        prev_cost = total
    budget_df = pd.DataFrame(budget_rows)
    st.dataframe(budget_df, use_container_width=True)

    total_6m = total_plan_cost + (parts_df["예상총비용(원)"].sum() if not parts_df.empty else 0)
    st.success(f"**{plan_months}개월 총 예상 예산: {total_6m:,.0f}원**")


# ─────────────────────────────────────────────
# main
# ─────────────────────────────────────────────
def main():
    st.title("🔧 유지보수 계획 수립 대시보드")
    st.caption(f"기준일: {TODAY.strftime('%Y-%m-%d')}  |  점검기록 기반 위험도 분석 및 계획 수립")
    st.markdown("---")

    data = load_all_data()
    filters = render_sidebar(data["master"])
    plan_months = filters["plan_months"]

    with st.spinner("위험도 분석 중..."):
        risk_df = build_risk_dataframe(
            data["master"], data["inspection"],
            data["maintenance"], data["status"]
        )

    filtered = apply_filters(risk_df, filters)

    if filtered.empty:
        st.warning("선택한 필터 조건에 해당하는 기기가 없습니다.")
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 위험도 우선순위",
        "📅 점검 스케줄",
        "📋 유지보수 계획서",
        "🔩 부품 교체 예측",
        "💰 비용/리소스 계획",
    ])

    with tab1:
        render_tab_risk_priority(filtered)
    with tab2:
        render_tab_inspection_schedule(filtered, data["inspection"], plan_months)
    with tab3:
        render_tab_maintenance_plan(filtered, data["maintenance"], plan_months)
    with tab4:
        render_tab_parts_prediction(filtered, data["replacement"], plan_months)
    with tab5:
        render_tab_cost_resource(filtered, data["maintenance"], data["replacement"], plan_months)


if __name__ == "__main__":
    main()
