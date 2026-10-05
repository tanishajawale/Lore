from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import os
import hashlib

# Secret key for JWT hashing - in production this should be in .env!
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-jwt-key-assignment-3")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token")

def get_password_hash(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password, hashed_password):
    return get_password_hash(plain_password) == hashed_password

from .database import SessionLocal, User, ChatMessage
import json

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_user(email: str, name: str, password: str):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            return False
        
        db_user = User(
            email=email,
            name=name,
            hashed_password=get_password_hash(password)
        )
        db.add(db_user)
        db.commit()
        return True
    finally:
        db.close()

def get_user_by_email(email: str):
    db = SessionLocal()
    try:
        return db.query(User).filter(User.email == email).first()
    finally:
        db.close()

def save_chat_message(email: str, role: str, content: str, sources: list = None):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return False
        
        msg = ChatMessage(
            user_id=user.id,
            role=role,
            content=content,
            sources=json.dumps(sources) if sources else None
        )
        db.add(msg)
        db.commit()
        return True
    finally:
        db.close()

def get_chat_history(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return []
        
        messages = db.query(ChatMessage).filter(ChatMessage.user_id == user.id).order_by(ChatMessage.timestamp.asc()).all()
        
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.content,
                "sources": json.loads(msg.sources) if msg.sources else []
            })
        return history
    finally:
        db.close()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = get_user_by_email(username)
    if user is None:
        raise credentials_exception
    
    # Convert SQLAlchemy object to dictionary for compatibility with current routes
    return {
        "username": user.email,
        "name": user.name,
        "is_admin": user.is_admin
    }
