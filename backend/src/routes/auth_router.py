from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from ..database.database import get_db
from ..models.user import UserCreate, User, Token
from ..auth.auth_utils import (
    authenticate_user, 
    create_access_token, 
    get_password_hash, 
    get_user_by_username,
    get_current_user, 
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..storage.minio_client import create_user_bucket

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db = Depends(get_db)):
    """Register a new user and return an access token"""
    # Check if username exists
    existing_user = await get_user_by_username(db, user_data.username)
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Hash the password
    hashed_password = get_password_hash(user_data.password)
    
    # Insert user into database
    query = """
    INSERT INTO users (username, password_hash) 
    VALUES (:username, :password_hash) 
    RETURNING id, username, created_at, last_login
    """
    
    values = {
        "username": user_data.username,
        "password_hash": hashed_password
    }
    
    user = await db.fetch_one(query=query, values=values)
    
    # Create user storage in MinIO
    user_id = user["id"]
    create_user_bucket(f"user-{user_id}")
    
    # Generate access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(get_db)):
    """Authenticate user and return access token"""
    user = await authenticate_user(db, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def get_current_user_info(current_user = Depends(get_current_user)):
    """Get current authenticated user information"""
    return current_user
