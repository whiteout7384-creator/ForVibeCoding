import streamlit as st
import pandas as pd
import os
from datetime import datetime

st.set_page_config(page_title="CSV 파일 뷰어", layout="wide")

st.title("📊 CSV 파일 뷰어")

# data 폴더의 CSV 파일 목록
csv_files = [f for f in os.listdir('data') if f.endswith('.csv')]
csv_files.sort()

if not csv_files:
    st.error("data 폴더에 CSV 파일이 없습니다.")
else:
    # 파일 선택
    selected_file = st.selectbox("파일 선택", csv_files)

    st.markdown("---")

    # CSV 파일 로드 및 표시
    file_path = f'data/{selected_file}'
    df = pd.read_csv(file_path)

    # 파일 정보
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("행(Row) 수", len(df))
    with col2:
        st.metric("열(Column) 수", len(df.columns))
    with col3:
        file_size = os.path.getsize(file_path) / 1024
        st.metric("파일 크기", f"{file_size:.2f} KB")

    st.markdown("---")

    # 데이터 미리보기
    st.subheader("데이터 미리보기")
    rows_to_show = st.slider("표시할 행 수", 5, min(100, len(df)), 20)
    st.dataframe(df.head(rows_to_show), use_container_width=True, height=400)

    st.markdown("---")

    # 컬럼 정보
    st.subheader("컬럼 정보")
    col_info = pd.DataFrame({
        '컬럼명': df.columns,
        '데이터타입': df.dtypes.values,
        '널값': df.isnull().sum().values,
        '유니크값': [df[col].nunique() for col in df.columns]
    })
    st.dataframe(col_info, use_container_width=True)

    st.markdown("---")

    # 통계 정보 (숫자 컬럼만)
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()

    if numeric_cols:
        st.subheader("통계 정보")
        st.dataframe(df[numeric_cols].describe(), use_container_width=True)

        st.markdown("---")

    # 다운로드 버튼
    st.subheader("다운로드")
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label=f"📥 {selected_file} 다운로드",
        data=csv,
        file_name=selected_file,
        mime="text/csv"
    )

    st.markdown("---")

    # 모든 파일 요약
    st.subheader("📁 생성된 모든 CSV 파일 요약")

    summary_data = []
    for file in csv_files:
        df_temp = pd.read_csv(f'data/{file}')
        summary_data.append({
            '파일명': file,
            '행 수': len(df_temp),
            '열 수': len(df_temp.columns),
            '파일 크기(KB)': round(os.path.getsize(f'data/{file}') / 1024, 2)
        })

    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True)

st.markdown("---")
st.caption(f"마지막 새로고침: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
