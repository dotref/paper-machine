from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from ..database.dependencies import get_db
from .models import TokenData
from .config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 setup
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password, hashed_password):
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Generate password hash"""
    return pwd_context.hash(password)

async def get_user(db, username: str):
    """Get user by username"""
    query = "SELECT * FROM users WHERE username = :username"
    return await db.fetch_one(query=query, values={"username": username})

async def authenticate_user(db, username: str, password: str):
    """Authenticate user by username and password"""
    user = await get_user(db, username)
    
    if not user:
        return False
    
    if not verify_password(password, user["password_hash"]):
        return False
    
    # Update last login timestamp
    update_query = "UPDATE users SET last_login = :last_login WHERE username = :username"
    await db.execute(
        query=update_query, 
        values={"last_login": datetime.now(), "username": username}
    )
    
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db = Depends(get_db)):
    """Verify token and return current user"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        
        token_exp = payload.get("exp")
        token_data = TokenData(username=username, exp=token_exp)
    except jwt.PyJWTError:
        raise credentials_exception
        
    # Fetch user from database
    user = await get_user(db, token_data.username)
    
    if user is None:
        raise credentials_exception
        
    return user
