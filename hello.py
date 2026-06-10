import streamlit as st

st.title("Hello Streamlit!")
st.write("안녕하세요! 이것은 Streamlit 앱입니다.")

name = st.text_input("이름을 입력하세요:")
if name:
    st.write(f"안녕하세요, {name}님!")
