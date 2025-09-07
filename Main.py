
import streamlit as st
import requests

st.set_page_config(page_title="Interview Simulator", layout="wide")

st.markdown("""
    <style>
    /* Background */
    .stApp {
        background-color: #1a1a1a;
        color: #f2f2f2;
        font-family: 'Fira Code', monospace;
    }

    /* Title */
    h1 {
        color: #f7b500; /* LeetCode yellow */
        text-align: center;
        font-weight: bold;
    }

    /* Chat bubbles */
    .stChatMessage {
        border-radius: 10px;
        padding: 10px 15px;
        margin: 8px 0;
    }

    /* User bubble */
    .stChatMessage[data-testid="stChatMessage-user"] {
        background: #2d2d2d;
        color: #ffffff;
        border-left: 3px solid #f7b500;
    }

    /* Assistant bubble */
    .stChatMessage[data-testid="stChatMessage-assistant"] {
        background: #222222;
        color: #dcdcdc;
        border-left: 3px solid #00bcd4;
    }

    /* Manager bubble */
    .stChatMessage[data-testid="stChatMessage-assistant"] strong:contains("Manager") {
        color: #ff7043;
    }

    /* Chat input */
    .stChatInputContainer {
        background: #2d2d2d;
        border: 1px solid #444;
        border-radius: 8px;
    }

    /* Smaller text */
    span {
        font-size: 14px !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("AI Interview Simulator")


if "messages" not in st.session_state:
    st.session_state.messages = []

backend_url = "http://127.0.0.1:8000/chat"


for msg in st.session_state.messages:
    role = msg["role"]
    content = msg["content"]

    if role == "user":
        with st.chat_message("user"):
            st.markdown(f"**You:** <span>{content}</span>", unsafe_allow_html=True)
    elif role == "assistant":
        with st.chat_message("assistant"):
            st.markdown(f"**Interviewer:** <span>{content}</span>", unsafe_allow_html=True)
    elif role == "manager":
        with st.chat_message("assistant"):
            st.markdown(f"**Manager:** <span>{content}</span>", unsafe_allow_html=True)


if prompt := st.chat_input("Your response"):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(f"**You:** <span>{prompt}</span>", unsafe_allow_html=True)


    with st.spinner("Interview in progress..."):
        response = requests.post(backend_url, json={"message": prompt})
        reply = response.json()["response"]


    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(f"**Interviewer:** <span>{reply}</span>", unsafe_allow_html=True)
