import streamlit as st
import os
import requests
from typing import List

# Use a default configuration for the frontend or load from config if available.
# We'll just define the basic Streamlit config here to keep it independent.
STREAMLIT_CONFIG = {
    "page_title": "Lore",
    "page_icon": "📚",
    "layout": "wide",
}

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1")

# Page configuration
st.set_page_config(**STREAMLIT_CONFIG)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_docs" not in st.session_state:
    st.session_state.uploaded_docs = []
if "access_token" not in st.session_state:
    st.session_state.access_token = None

def get_auth_headers():
    if st.session_state.access_token:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}

def login_form():
    st.markdown("<h1 style='text-align: center; color: #4A90E2;'>Welcome to Lore</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Please sign in or create an account to continue.</p>", unsafe_allow_html=True)
    st.write("")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            st.subheader("Login")
            username = st.text_input("Email Address", placeholder="admin@example.com", key="login_username")
            password = st.text_input("Password", type="password", placeholder="password123", key="login_password")
            
            submit_login = st.button("Sign In", use_container_width=True, type="primary")
            
            if submit_login:
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/token",
                        data={"username": username, "password": password}
                    )
                    if response.status_code == 200:
                        st.session_state.access_token = response.json()["access_token"]
                        st.success("Login successful!")
                        
                        # Load chat history
                        try:
                            hist_resp = requests.get(
                                f"{API_BASE_URL}/chat_history",
                                headers={"Authorization": f"Bearer {st.session_state.access_token}"}
                            )
                            if hist_resp.status_code == 200:
                                st.session_state.messages = hist_resp.json().get("history", [])
                        except Exception as e:
                            st.warning(f"Could not load history: {e}")
                            
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")

        with tab2:
            st.subheader("Create an Account")
            name = st.text_input("Full Name", placeholder="John Doe", key="signup_name")
            email = st.text_input("Email Address", placeholder="john@example.com", key="signup_email")
            new_password = st.text_input("Create Password", type="password", key="signup_password")
            
            submit_signup = st.button("Sign Up", use_container_width=True, type="primary")
            
            if submit_signup:
                if not name or not email or not new_password:
                    st.error("Please fill in all fields.")
                else:
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/signup",
                            json={"name": name, "email": email, "password": new_password}
                        )
                        if response.status_code == 200:
                            st.success("Account created successfully! You can now login.")
                        else:
                            st.error(response.json().get("detail", "Error creating account."))
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")

def main():
    if not st.session_state.access_token:
        login_form()
        return

    st.title("📚 Lore")
    st.markdown("### *Institutional knowledge, on demand.*")
    
    # Sidebar for file upload and controls
    with st.sidebar:
        st.header("📁 Document Management")
        
        # File upload
        uploaded_files = st.file_uploader(
            "Upload PDF files",
            type=['pdf'],
            accept_multiple_files=True,
            help="Upload one or more PDF files to chat with"
        )
        
        # Process uploaded files
        if uploaded_files:
            if st.button("🔄 Process Documents", type="primary"):
                with st.spinner("Processing documents via Backend..."):
                    files_payload = []
                    for uf in uploaded_files:
                        files_payload.append(
                            ("files", (uf.name, uf.getvalue(), uf.type))
                        )
                        
                    try:
                        response = requests.post(
                            f"{API_BASE_URL}/upload", 
                            files=files_payload,
                            headers=get_auth_headers()
                        )
                        if response.status_code == 200:
                            data = response.json()
                            st.session_state.uploaded_docs = data["documents"]
                            st.success(f"✅ Processed {data['processed_count']} documents")
                        else:
                            st.error(f"❌ Error: {response.text}")
                    except Exception as e:
                        st.error(f"❌ Connection error: {str(e)}")
        
        # Show uploaded documents
        if st.session_state.uploaded_docs:
            st.subheader("📋 Uploaded Documents")
            for doc in st.session_state.uploaded_docs:
                st.write(f"• {doc}")
        
        # Clear documents
        if st.session_state.uploaded_docs and st.button("🗑️ Clear All Documents"):
            try:
                requests.post(f"{API_BASE_URL}/clear", headers=get_auth_headers())
                st.session_state.uploaded_docs = []
                st.session_state.messages = []
                st.rerun()
            except Exception as e:
                st.error(f"❌ Connection error: {str(e)}")
        
        st.divider()
        
        
    # Main content area
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📝 Summaries", "ℹ️ About"])
    
    with tab1:
        st.header("💬 Chat with Your Documents")
        
        if not st.session_state.uploaded_docs:
            st.info("👆 Please upload some PDF files using the sidebar to start chatting!")
        else:
            # Chat input at the top
            with st.form(key="chat_form", clear_on_submit=True):
                col1, col2 = st.columns([5, 1])
                with col1:
                    prompt = st.text_input("Ask a question about your documents...", placeholder="Type your question here...", label_visibility="collapsed")
                with col2:
                    submit_button = st.form_submit_button("Ask")
            
            if submit_button and prompt:
                # Add user message
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # We need to process the request before re-rendering the full chat history
                with st.spinner("Thinking..."):
                    try:
                        # Send only previous messages as history (exclude the current prompt just added)
                        history_payload = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages[:-1]
                        ]
                        
                        response = requests.post(
                            f"{API_BASE_URL}/chat", 
                            json={"question": prompt, "k": 10, "history": history_payload},
                            headers=get_auth_headers()
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("error"):
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": data.get("answer", "Unknown error")
                                })
                            else:
                                st.session_state.messages.append({
                                    "role": "assistant", 
                                    "content": data["answer"],
                                    "sources": data.get("sources", [])
                                })
                        else:
                            st.error(f"❌ API Error: {response.text}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Connection error: {str(e)}")
            
            st.divider()
            
            # Chat interface - Render messages in reverse order (newest pairs first)
            # We group the messages into (Question, Answer) pairs so the question stays above the answer
            messages = st.session_state.messages
            pairs = []
            for i in range(0, len(messages), 2):
                pair = messages[i:i+2]
                pairs.append(pair)
                
            for pair in reversed(pairs):
                for message in pair:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                        
                        # Show sources for assistant messages
                        if message["role"] == "assistant" and "sources" in message:
                            with st.expander("📚 Sources"):
                                unique_docs = set(source["document"] for source in message["sources"])
                                for doc in unique_docs:
                                    st.markdown(f"• **{doc}**")
    
    with tab2:
        st.header("📝 Document Summaries")
        
        if not st.session_state.uploaded_docs:
            st.info("👆 Please upload some PDF files to generate summaries!")
        else:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                if st.button("📄 Summarize All Documents", type="primary"):
                    with st.spinner("Generating summaries via Backend..."):
                        try:
                            response = requests.get(
                                f"{API_BASE_URL}/summarize",
                                headers=get_auth_headers()
                            )
                            if response.status_code == 200:
                                summaries = response.json().get("summaries", {})
                                for doc_name, summary in summaries.items():
                                    st.subheader(f"📄 {doc_name}")
                                    if summary.startswith("Error") or "failed" in summary.lower():
                                        st.error(summary)
                                    else:
                                        st.markdown(summary, unsafe_allow_html=True)
                                    st.divider()
                            else:
                                st.error(f"❌ API Error: {response.text}")
                        except Exception as e:
                            st.error(f"❌ Connection error: {str(e)}")
            
            with col2:
                selected_doc = st.selectbox(
                    "Select a document to summarize:",
                    st.session_state.uploaded_docs
                )
                
                if st.button("📄 Summarize Selected Document"):
                    with st.spinner("Generating summary..."):
                        try:
                            response = requests.get(
                                f"{API_BASE_URL}/summarize/{selected_doc}",
                                headers=get_auth_headers()
                            )
                            if response.status_code == 200:
                                data = response.json()
                                st.subheader(f"📄 {selected_doc}")
                                if data.get("error"):
                                    st.error(data.get("summary", "Unknown error"))
                                else:
                                    st.markdown(data.get("summary"), unsafe_allow_html=True)
                            else:
                                st.error(f"❌ API Error: {response.text}")
                        except Exception as e:
                            st.error(f"❌ Connection error: {str(e)}")
    
    with tab3:
        st.header("ℹ️ About This App")
        
        st.markdown("""
        ### 🚀 Features
        
        - **📁 Multi-PDF Upload**: Upload and process multiple PDF documents
        - **💬 Intelligent Chat**: Ask questions about your documents using AI
        - **📝 AI Summaries**: Generate comprehensive summaries of your documents
        - **🎯 Vector Search**: Uses advanced vector embeddings for better document retrieval
        - **🔄 Client-Server Architecture**: Fast processing backed by a FastAPI microservice
        
        ### 🛠️ How It Works
        
        1. **Upload PDFs**: Use the sidebar to upload your PDF documents
        2. **Process Documents**: Sent to the FastAPI backend for text extraction and vector embedding
        3. **Chat**: Ask questions which are processed securely via the backend RAG
        4. **Summarize**: Generate summaries powered by LangChain and OpenAI
        """)
        
if __name__ == "__main__":
    main()
