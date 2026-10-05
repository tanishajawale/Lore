from pydantic import BaseModel
from typing import List, Optional, Dict

class Message(BaseModel):
    role: str
    content: str

class Source(BaseModel):
    document: str
    chunk: Optional[int] = None
    relevance_score: Optional[float] = None

class ChatRequest(BaseModel):
    question: str
    k: int = 10
    history: List[Message] = []

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source] = []
    error: bool = False

class SummaryResponse(BaseModel):
    summary: str
    error: bool = False

class AllSummariesResponse(BaseModel):
    summaries: Dict[str, str]

class ProcessDocsResponse(BaseModel):
    processed_count: int
    documents: List[str]
    error: bool = False

class UserSignupRequest(BaseModel):
    name: str
    email: str
    password: str
