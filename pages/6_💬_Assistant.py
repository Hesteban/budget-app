"""
Page 6 — AI Chat Assistant: conversational interface over budget data.
"""
import streamlit as st

from budget.agents.ai_assistant import stream_response

if not st.session_state.get("authenticated"):
    st.warning("Please log in from the Home page.")
    st.stop()

st.title("💬 Budget Assistant")
st.caption("Ask anything about your expenses, settlements, or spending trends.")

st.session_state.setdefault("chat_messages", [])

for msg in st.session_state["chat_messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask about your budget…"):
    st.session_state["chat_messages"].append(
        {"role": "user", "content": prompt, "type": "message"}
    )
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            response = st.write_stream(
                stream_response(st.session_state["chat_messages"])
            )
        except Exception as e:
            st.error(f"Assistant error: {e}")
            response = None

    if response:
        st.session_state["chat_messages"].append(
            {"role": "assistant", "content": response, "type": "message"}
        )
