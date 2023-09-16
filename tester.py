import streamlit as st

if 'num' not in st.session_state:
    st.session_state.num = 0

def wuttt():
    st.session_state.num += 1
    print(f"wtf man how does this work {st.session_state.num}")
st.toggle("wtf?", on_change= wuttt)
