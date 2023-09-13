import streamlit as st

#top components
st.set_page_config(layout='wide')
conversation_col, transcription_col =st.columns(2,gap="small")

with conversation_col:
    st.text_area("Conversation", height=350)

with transcription_col:
    st.text_area("Transcription", height=350)

#middle components
st.slider("Update Response Interval:", min_value=0.00, max_value=5.00)
st.selectbox("Languages", options=("eng","fre"), placeholder="Languages")

#lower button components
toggle_col, button_col =st.columns((30,12),gap="large")

with toggle_col:
    st.toggle("Speaker")
    st.toggle("Microphone")
with button_col:    
    st.button("Suggest Responses")
    st.button("Suggest Responses Continuously")

#sidebar components
sidebar_copy_button = st.sidebar.button("Copy conversation")
sidebar_download_button = st.sidebar.download_button("Download your conversation", data="123")
sidebar_clear_chat = st.sidebar.button("Clear Chat")