import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# 페이지 설정
st.set_page_config(page_title="기계설비관리 대시보드", layout="wide", initial_sidebar_state="expanded")

# 타이틀
st.title("🏭 기계설비관리 대시보드")
st.markdown("---")

# 데이터 로드 함수 (캐싱)
@st.cache_data
def load_data():
    master = pd.read_csv('data/기기마스터.csv')
    inspection = pd.read_csv('data/점검기록.csv')
    maintenance = pd.read_csv('data/유지보수기록.csv')
    replacement = pd.read_csv('data/부품교체이력.csv')
    status = pd.read_csv('data/월별기기상태.csv')
    history = pd.read_csv('data/기기이력카드.csv')
    return master, inspection, maintenance, replacement, status, history

master_df, inspection_df, maintenance_df, replacement_df, status_df, history_df = load_data()

# 사이드바 필터
with st.sidebar:
    st.header("📊 필터 설정")
    selected_location = st.multiselect(
        "설치 위치 선택",
        master_df['설치위치'].unique(),
        default=master_df['설치위치'].unique()[:3]
    )

    selected_status = st.multiselect(
        "기기 상태 선택",
        master_df['기기상태'].unique(),
        default=master_df['기기상태'].unique()
    )

# 필터된 데이터
filtered_master = master_df[
    (master_df['설치위치'].isin(selected_location)) &
    (master_df['기기상태'].isin(selected_status))
]

# 탭 생성
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📈 대시보드", "🔧 기기현황", "✅ 점검기록", "🔨 유지보수", "📊 월별추이", "📅 연도별추이", "🤖 AI 분석"])

# ============ TAB 1: 대시보드 ============
with tab1:
    st.subheader("주요 메트릭")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("총 기기 수", len(filtered_master))

    with col2:
        normal_count = len(filtered_master[filtered_master['기기상태'] == '정상'])
        st.metric("정상 기기", normal_count, f"{normal_count/len(filtered_master)*100:.1f}%")

    with col3:
        warning_count = len(filtered_master[filtered_master['기기상태'] == '주의'])
        st.metric("주의 기기", warning_count, f"{warning_count/len(filtered_master)*100:.1f}%")

    with col4:
        abnormal_count = len(filtered_master[filtered_master['기기상태'].isin(['경고', '부분결함'])])
        st.metric("이상 기기", abnormal_count, f"{abnormal_count/len(filtered_master)*100:.1f}%")

    st.markdown("---")

    # 기기 상태 분포
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("기기 상태 분포")
        status_count = filtered_master['기기상태'].value_counts()
        fig1 = px.pie(
            values=status_count.values,
            names=status_count.index,
            color_discrete_map={'정상': '#2ecc71', '주의': '#f39c12', '경고': '#e74c3c', '부분결함': '#c0392b'}
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        st.subheader("기기 유형 분포")
        type_count = filtered_master['기기유형'].value_counts()
        fig2 = px.bar(
            x=type_count.index[:10],
            y=type_count.values[:10],
            labels={'x': '기기유형', 'y': '수량'}
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # 위치별 기기 수
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("위치별 기기 현황")
        location_count = filtered_master['설치위치'].value_counts()
        fig3 = px.bar(
            y=location_count.index,
            x=location_count.values,
            orientation='h',
            labels={'x': '기기 수', 'y': '설치위치'}
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col2:
        st.subheader("제조사별 기기 현황")
        maker_count = filtered_master['제조사'].value_counts()
        fig4 = px.bar(
            x=maker_count.index,
            y=maker_count.values,
            labels={'x': '제조사', 'y': '기기 수'}
        )
        st.plotly_chart(fig4, use_container_width=True)

# ============ TAB 2: 기기현황 ============
with tab2:
    st.subheader("기기 현황 조회")

    # 기기 선택
    selected_equipment = st.selectbox(
        "기기 선택",
        filtered_master['기기ID'].values,
        format_func=lambda x: f"{x} - {filtered_master[filtered_master['기기ID']==x]['기기명'].values[0]}"
    )

    # 선택된 기기 정보
    eq_info = filtered_master[filtered_master['기기ID'] == selected_equipment].iloc[0]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**기기ID**: {eq_info['기기ID']}")
        st.write(f"**기기명**: {eq_info['기기명']}")
        st.write(f"**기기유형**: {eq_info['기기유형']}")
    with col2:
        st.write(f"**설치위치**: {eq_info['설치위치']}")
        st.write(f"**제조사**: {eq_info['제조사']}")
        st.write(f"**모델명**: {eq_info['모델명']}")
    with col3:
        st.write(f"**설치일자**: {eq_info['설치일자']}")
        st.write(f"**정격용량**: {eq_info['정격용량']}")
        st.write(f"**현재상태**: {eq_info['기기상태']}")

    st.markdown("---")

    # 이 기기의 점검 기록
    eq_inspection = inspection_df[inspection_df['기기ID'] == selected_equipment].sort_values('점검일자', ascending=False)
    st.subheader(f"{selected_equipment} 최근 점검 기록")
    if len(eq_inspection) > 0:
        st.dataframe(eq_inspection[['점검일자', '점검항목', '측정값', '측정단위', '점검결과', '담당자']].head(10), use_container_width=True)
    else:
        st.info("점검 기록이 없습니다.")

    # 이 기기의 유지보수 기록
    eq_maintenance = maintenance_df[maintenance_df['기기ID'] == selected_equipment].sort_values('유지보수일자', ascending=False)
    st.subheader(f"{selected_equipment} 최근 유지보수 기록")
    if len(eq_maintenance) > 0:
        st.dataframe(eq_maintenance[['유지보수일자', '유지보수유형', '작업내용', '소요시간(시간)', '비용(원)', '완료상태']].head(10), use_container_width=True)
    else:
        st.info("유지보수 기록이 없습니다.")

# ============ TAB 3: 점검기록 ============
with tab3:
    st.subheader("점검 기록 분석")

    # 필터링된 기기의 점검 데이터
    filtered_inspection = inspection_df[inspection_df['기기ID'].isin(filtered_master['기기ID'])]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("점검 결과 분포")
        result_count = filtered_inspection['점검결과'].value_counts()
        fig5 = px.pie(
            values=result_count.values,
            names=result_count.index,
            color_discrete_map={'정상': '#2ecc71', '주의': '#f39c12', '경고': '#e74c3c', '불량': '#c0392b'}
        )
        st.plotly_chart(fig5, use_container_width=True)

    with col2:
        st.subheader("점검 항목별 분포")
        item_count = filtered_inspection['점검항목'].value_counts()
        fig6 = px.bar(
            x=item_count.index,
            y=item_count.values,
            labels={'x': '점검항목', 'y': '점검 횟수'}
        )
        st.plotly_chart(fig6, use_container_width=True)

    st.markdown("---")

    st.subheader("최근 점검 기록")
    st.dataframe(
        filtered_inspection.sort_values('점검일자', ascending=False)[
            ['기기ID', '점검일자', '점검항목', '측정값', '점검결과', '담당자']
        ].head(50),
        use_container_width=True
    )

# ============ TAB 4: 유지보수 ============
with tab4:
    st.subheader("유지보수 현황")

    # 필터링된 기기의 유지보수 데이터
    filtered_maintenance = maintenance_df[maintenance_df['기기ID'].isin(filtered_master['기기ID'])]

    col1, col2 = st.columns(2)

    with col1:
        st.metric("총 유지보수 횟수", len(filtered_maintenance))
        st.metric("총 유지보수 비용", f"{filtered_maintenance['비용(원)'].sum():,.0f}원")

    with col2:
        st.metric("평균 유지보수 비용", f"{filtered_maintenance['비용(원)'].mean():,.0f}원")
        st.metric("평균 소요시간", f"{filtered_maintenance['소요시간(시간)'].mean():.1f}시간")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("유지보수 유형별 분포")
        type_count = filtered_maintenance['유지보수유형'].value_counts()
        fig7 = px.pie(values=type_count.values, names=type_count.index)
        st.plotly_chart(fig7, use_container_width=True)

    with col2:
        st.subheader("작업내용별 빈도")
        work_count = filtered_maintenance['작업내용'].value_counts()
        fig8 = px.bar(
            x=work_count.index,
            y=work_count.values,
            labels={'x': '작업내용', 'y': '횟수'}
        )
        st.plotly_chart(fig8, use_container_width=True)

    st.markdown("---")

    st.subheader("최근 유지보수 기록")
    st.dataframe(
        filtered_maintenance.sort_values('유지보수일자', ascending=False)[
            ['기기ID', '유지보수일자', '유지보수유형', '작업내용', '소요시간(시간)', '비용(원)']
        ].head(50),
        use_container_width=True
    )

# ============ TAB 5: 월별추이 ============
with tab5:
    st.subheader("월별 기기 상태 추이")

    # 필터링된 기기의 월별 상태 데이터
    filtered_status = status_df[status_df['기기ID'].isin(filtered_master['기기ID'])]

    # 월별 가동시간 합계
    monthly_runtime = filtered_status.groupby('연월')['가동시간(시간)'].sum().reset_index()
    fig9 = px.line(
        monthly_runtime,
        x='연월',
        y='가동시간(시간)',
        markers=True,
        title='월별 총 가동시간',
        labels={'연월': '연월', '가동시간(시간)': '가동시간(시간)'}
    )
    st.plotly_chart(fig9, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        # 월별 평균 온도
        monthly_temp = filtered_status.groupby('연월')['평균온도(℃)'].mean().reset_index()
        fig10 = px.line(
            monthly_temp,
            x='연월',
            y='평균온도(℃)',
            markers=True,
            title='월별 평균 온도',
            labels={'연월': '연월', '평균온도(℃)': '평균온도(℃)'}
        )
        st.plotly_chart(fig10, use_container_width=True)

    with col2:
        # 월별 평균 압력
        monthly_pressure = filtered_status.groupby('연월')['평균압력(bar)'].mean().reset_index()
        fig11 = px.line(
            monthly_pressure,
            x='연월',
            y='평균압력(bar)',
            markers=True,
            title='월별 평균 압력',
            labels={'연월': '연월', '평균압력(bar)': '평균압력(bar)'}
        )
        st.plotly_chart(fig11, use_container_width=True)

    st.markdown("---")

    # 종합상태 분포 (월별)
    st.subheader("월별 종합상태 분포")
    status_dist = filtered_status.groupby(['연월', '종합상태']).size().reset_index(name='count')
    fig12 = px.bar(
        status_dist,
        x='연월',
        y='count',
        color='종합상태',
        barmode='stack',
        title='월별 기기 종합상태',
        labels={'연월': '연월', 'count': '기기 수'}
    )
    st.plotly_chart(fig12, use_container_width=True)

# ============ TAB 6: 연도별추이 ============
with tab6:
    st.subheader("연도별 기기 상태 추이")

    filtered_status_y = status_df[status_df['기기ID'].isin(filtered_master['기기ID'])].copy()
    filtered_status_y['연도'] = filtered_status_y['연월'].astype(str).str[:4]

    # 연도별 가동시간 합계
    yearly_runtime = filtered_status_y.groupby('연도')['가동시간(시간)'].sum().reset_index()
    fig_y1 = px.line(
        yearly_runtime,
        x='연도',
        y='가동시간(시간)',
        markers=True,
        title='연도별 총 가동시간',
        labels={'연도': '연도', '가동시간(시간)': '가동시간(시간)'}
    )
    st.plotly_chart(fig_y1, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        yearly_temp = filtered_status_y.groupby('연도')['평균온도(℃)'].mean().reset_index()
        fig_y2 = px.line(
            yearly_temp,
            x='연도',
            y='평균온도(℃)',
            markers=True,
            title='연도별 평균 온도',
            labels={'연도': '연도', '평균온도(℃)': '평균온도(℃)'}
        )
        st.plotly_chart(fig_y2, use_container_width=True)

    with col2:
        yearly_pressure = filtered_status_y.groupby('연도')['평균압력(bar)'].mean().reset_index()
        fig_y3 = px.line(
            yearly_pressure,
            x='연도',
            y='평균압력(bar)',
            markers=True,
            title='연도별 평균 압력',
            labels={'연도': '연도', '평균압력(bar)': '평균압력(bar)'}
        )
        st.plotly_chart(fig_y3, use_container_width=True)

    st.markdown("---")

    st.subheader("연도별 종합상태 분포")
    status_dist_y = filtered_status_y.groupby(['연도', '종합상태']).size().reset_index(name='count')
    fig_y4 = px.bar(
        status_dist_y,
        x='연도',
        y='count',
        color='종합상태',
        barmode='stack',
        title='연도별 기기 종합상태',
        labels={'연도': '연도', 'count': '기기 수'}
    )
    st.plotly_chart(fig_y4, use_container_width=True)

# ============ TAB 7: AI 분석 ============
with tab7:
    st.subheader("🤖 AI 데이터 분석 도우미")
    st.markdown("대시보드 데이터에 대해 자유롭게 질문하세요. Gemini AI가 답변해드립니다.")

    if not GEMINI_API_KEY or GEMINI_API_KEY == "여기에_API_키를_입력하세요":
        st.error("⚠️ `.env` 파일에 GEMINI_API_KEY를 설정해주세요.")
        st.code("GEMINI_API_KEY=your_api_key_here", language="bash")
        st.markdown("**API 키 발급:** [Google AI Studio](https://aistudio.google.com/app/apikey)")
    else:
        client = genai.Client(api_key=GEMINI_API_KEY)

        # 데이터 요약 컨텍스트 생성
        @st.cache_data
        def build_data_context(master_len, inspection_len, maintenance_len):
            status_counts = master_df['기기상태'].value_counts().to_dict()
            location_counts = master_df['설치위치'].value_counts().head(5).to_dict()
            type_counts = master_df['기기유형'].value_counts().head(5).to_dict()
            recent_maintenance = maintenance_df.sort_values('유지보수일자', ascending=False).head(5)[
                ['기기ID', '유지보수일자', '유지보수유형', '작업내용', '비용(원)']
            ].to_string(index=False)
            inspection_results = inspection_df['점검결과'].value_counts().to_dict()
            total_cost = maintenance_df['비용(원)'].sum()
            avg_cost = maintenance_df['비용(원)'].mean()

            context = f"""당신은 기계설비관리 대시보드의 AI 분석 도우미입니다.
아래는 현재 대시보드의 실제 데이터 요약입니다. 이 데이터를 바탕으로 질문에 답하세요.

[기기 현황]
- 총 기기 수: {master_len}대
- 기기 상태 분포: {status_counts}
- 주요 설치 위치 (상위 5개): {location_counts}
- 주요 기기 유형 (상위 5개): {type_counts}

[점검 기록]
- 총 점검 건수: {inspection_len}건
- 점검 결과 분포: {inspection_results}

[유지보수 현황]
- 총 유지보수 건수: {maintenance_len}건
- 총 유지보수 비용: {total_cost:,.0f}원
- 평균 유지보수 비용: {avg_cost:,.0f}원
- 최근 유지보수 기록:
{recent_maintenance}

질문에 한국어로 명확하고 친절하게 답변하세요. 데이터에 없는 정보는 추측하지 말고 "데이터에 포함되지 않은 정보입니다"라고 답하세요."""
            return context

        data_context = build_data_context(len(master_df), len(inspection_df), len(maintenance_df))

        # 채팅 히스토리 초기화
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        # 채팅 UI
        chat_container = st.container(height=450)

        with chat_container:
            if not st.session_state.chat_history:
                st.info("💬 질문 예시: '현재 경고 상태인 기기가 몇 대인가요?', '최근 유지보수 비용이 가장 많이 든 작업은?', '어떤 설치 위치에 기기가 가장 많나요?'")
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 입력창
        user_input = st.chat_input("데이터에 대해 질문하세요...")

        col_clear, _ = st.columns([1, 5])
        with col_clear:
            if st.button("대화 초기화", use_container_width=True):
                st.session_state.chat_history = []
                st.rerun()

        if user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})

            with st.spinner("AI가 분석 중입니다..."):
                try:
                    history_text = "\n".join([
                        f"{'사용자' if m['role'] == 'user' else 'AI'}: {m['content']}"
                        for m in st.session_state.chat_history[:-1]
                    ])
                    prompt = f"{data_context}\n\n이전 대화:\n{history_text}\n\n사용자: {user_input}\n\nAI:"
                    response = client.models.generate_content(
                        model="gemini-flash-latest",
                        contents=prompt
                    )
                    answer = response.text
                except Exception as e:
                    answer = f"❌ 오류가 발생했습니다: {str(e)}"

            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            st.rerun()

# 푸터
st.markdown("---")
st.caption(f"마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
