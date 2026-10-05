from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import List
import uvicorn
import io
import logging

from .schemas import ChatRequest, ChatResponse, SummaryResponse, AllSummariesResponse, ProcessDocsResponse, UserSignupRequest
from .vector_store import VectorStore
from .rag_system import RAGSystem
from .pdf_processor import PDFProcessor
from .auth import get_current_user, create_access_token, verify_password, ACCESS_TOKEN_EXPIRE_MINUTES, create_user, get_user_by_email, save_chat_message, get_chat_history

app = FastAPI(title="Lore API", version="1.0.0")

# Setup logging
logging.basicConfig(level=logging.INFO)

# Global instances (simulating single user backend for now)
vector_store = VectorStore()
rag_system = RAGSystem(vector_store)

@app.get("/")
async def root():
    return {"message": "AI RAG API is running"}

@app.post("/api/v1/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_email(form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/v1/signup")
def signup(request: UserSignupRequest):
    success = create_user(request.email, request.name, request.password)
    if not success:
        raise HTTPException(status_code=400, detail="Email already registered")
    return {"message": "User created successfully"}

@app.get("/api/v1/chat_history")
def get_history(current_user: dict = Depends(get_current_user)):
    history = get_chat_history(current_user["username"])
    return {"history": history}

@app.post("/api/v1/upload", response_model=ProcessDocsResponse)
def upload_documents(files: List[UploadFile] = File(...), current_user: dict = Depends(get_current_user)):
    processor = PDFProcessor()
    processed_docs = processor.process_pdfs(files)
    
    if not processed_docs:
        raise HTTPException(status_code=400, detail="No documents were processed")
        
    vector_store.add_documents(processed_docs)
    
    return ProcessDocsResponse(
        processed_count=len(processed_docs),
        documents=list(processed_docs.keys())
    )

@app.post("/api/v1/chat", response_model=ChatResponse)
def chat(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    # Save the user's question
    save_chat_message(current_user["username"], "user", request.question)
    
    # Convert Pydantic models to dicts for the RAG system
    history = [{"role": msg.role, "content": msg.content} for msg in request.history]
    response = rag_system.answer_question(request.question, history=history, k=request.k)
    
    # Save the assistant's answer and sources
    if not response.get("error"):
        save_chat_message(current_user["username"], "assistant", response["answer"], response.get("sources", []))
    
    return ChatResponse(**response)

@app.get("/api/v1/summarize/{document_name}", response_model=SummaryResponse)
def summarize_document(document_name: str, current_user: dict = Depends(get_current_user)):
    summary = rag_system.summarize_document(document_name)
    if summary.startswith("Error") or summary.startswith("No content"):
        return SummaryResponse(summary=summary, error=True)
    return SummaryResponse(summary=summary)

@app.get("/api/v1/summarize", response_model=AllSummariesResponse)
def summarize_all(current_user: dict = Depends(get_current_user)):
    summaries = rag_system.summarize_all_documents()
    return AllSummariesResponse(summaries=summaries)

@app.post("/api/v1/clear")
def clear_documents(current_user: dict = Depends(get_current_user)):
    vector_store.clear()
    return {"message": "Vector store cleared"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
