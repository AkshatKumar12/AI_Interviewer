
import streamlit as st
import requests
import uuid


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

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "candidate_name" not in st.session_state:
    st.session_state.candidate_name = "Candidate"

if "messages" not in st.session_state:
    st.session_state.messages = []
if "final_score" not in st.session_state:
    st.session_state.final_score = None

backend_url = "http://127.0.0.1:8000/chat"

with st.sidebar:
    st.session_state.candidate_name = st.text_input(
        "Candidate name",
        value=st.session_state.candidate_name,
        max_chars=64,
    ).strip() or "Candidate"
    st.caption(f"Session ID: {st.session_state.session_id}")


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
        response = requests.post(backend_url, json={
            "message": prompt,
            "session_id": st.session_state.session_id,
            "candidate_name": st.session_state.candidate_name,
        })
        payload = None
        reply = "No response."
        if response.headers.get("content-type", "").lower().startswith("application/json"):
            try:
                payload = response.json()
            except ValueError:
                payload = None
        if payload:
            reply = payload.get("response", "No response.")
            st.session_state.session_id = payload.get("session_id", st.session_state.session_id)
            if payload.get("final_score"):
                st.session_state.final_score = payload["final_score"]
            if payload.get("manager_response"):
                st.session_state.messages.append({"role": "manager", "content": payload["manager_response"]})
        else:
            st.error("Backend did not return JSON. Check backend logs.")
            st.code(response.text or f"HTTP {response.status_code}")


    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.markdown(f"**Interviewer:** <span>{reply}</span>", unsafe_allow_html=True)

if st.session_state.final_score:
    st.divider()
    st.subheader("Scorecard")
    st.info(st.session_state.final_score.get("summary", "Interview completed."))
    score = st.session_state.final_score
    st.json(st.session_state.final_score)
