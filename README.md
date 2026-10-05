# 📚 Lore — *Institutional knowledge, on demand.*

A powerful, full-stack application that allows you to upload multiple PDFs, chat with their content using AI, and generate lightning-fast comprehensive summaries. 

Built with **FastAPI** (Backend), **Streamlit** (Frontend), **FAISS** (Vector Search), and powered by the **Groq AI Engine** for incredibly fast responses.

---

## ✨ Key Features

- **🔐 Secure Authentication**: Create an account and log in securely.
- **📁 Multi-PDF Upload**: Upload and process multiple PDF documents with automatic deduplication.
- **💬 Conversational Memory**: The AI remembers your chat history, allowing you to ask follow-up questions seamlessly.
- **🔍 Accurate Retrieval**: High-precision RAG implementation using SentenceTransformers and FAISS.
- **📝 High-Speed AI Summaries**: Generate comprehensive summaries of your documents in seconds using optimized batch-processing.
- **🎯 Precise Source Citation**: The AI explicitly tells you exactly which PDF document(s) it used to answer your question.

---

## 🚀 Setup & Run Instructions

### 1. Prerequisites
- Python 3.10+
- An API Key from [Groq](https://console.groq.com/keys)

### 2. Installation
Clone the repository and run the setup script to install all dependencies and set up the virtual environment:

```bash
./setup.sh
```

### 3. Configure API Key
Open the `api_config.env` file in the root directory and add your Groq API key:

```env
GROQ_API_KEY=gsk_your_groq_api_key_here
```

### 4. Run the Application
Start the application using the master run script. This will automatically boot up both the **FastAPI Backend Server** and the **Streamlit Frontend App**:

```bash
./run_app.sh
```

The application will open automatically in your browser at `http://localhost:8501`.

---

## 🛠️ How to Use

1. **Create an Account**: Upon opening the app, use the "Sign Up" tab to create a secure local account.
2. **Upload Documents**: Use the left sidebar to upload one or more PDFs. Click "Process Documents" to build the Vector Database.
3. **Chat**: Head to the Chat tab and ask questions. You can click on the `📚 Sources` dropdown under the AI's response to see which PDF it extracted the answer from.
4. **Summarize**: Head to the Summaries tab to generate lightning-fast summaries of any uploaded PDF.

---

## 🔧 Technical Architecture

- **Frontend**: Streamlit (`frontend/app.py`)
- **Backend API**: FastAPI (`backend/main.py`)
- **Database**: SQLite (User Auth) + FAISS (Vector Store)
- **Embeddings**: `all-MiniLM-L6-v2` via SentenceTransformers
- **LLM**: `qwen/qwen3.8-27b` via Groq
- **Document Processing**: LangChain & PyPDF2

---

## 📋 Configuration

You can tweak system behavior by editing `backend/config.py`:
- `CHUNK_SIZE`: Size of text chunks for the Vector DB (Default: 1000)
- `SUMMARY_BATCH_SIZE`: Number of chunks processed simultaneously for lightning-fast summaries (Default: 15)
- `MAX_WORDS_FOR_DIRECT_SUMMARY`: Bypass chunking entirely for standard-sized documents (Default: 4000)

---

## 📄 License
This project is open source and available under the MIT License.
