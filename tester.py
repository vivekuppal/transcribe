import streamlit as st
import time 
import random

def hello():
    return (f"{random.randint(1,100)}")
def recursion():
    st.session_state.text = hello()
    time.sleep(0.3)
    recursion()

st.text_area("Enter text", key="text")
st.button("Upper Text", on_click=recursion)