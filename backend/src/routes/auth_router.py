from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from ..database.database import get_db
from ..models.user import UserCreate, User, Token
from ..auth.auth_utils import (
    authenticate_user, 
    create_access_token, 
    get_password_hash, 
    get_user_by_username,
    get_current_user, 
    oauth2_scheme,
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


@router.get("/auth-debug")
async def auth_debug(
    request: Request, 
    token: str = Depends(oauth2_scheme)
):
    """Debug endpoint for authentication issues"""
    auth_header = request.headers.get("Authorization", "")
    
    result = {
        "has_auth_header": bool(auth_header),
        "header_value": auth_header if auth_header else None,
        "token_from_dependency": token[:10] + "..." if token else None,  # Add this to confirm token received
    }
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        
        try:
            # Import here to avoid circular imports
            from ..auth.auth_utils import SECRET_KEY, ALGORITHM
            import jwt
            
            # Try to decode without verification
            unverified = jwt.decode(token, options={"verify_signature": False})
            result["token_unverified"] = unverified
            
            # Try to decode with verification
            try:
                verified = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                result["token_verified"] = verified
                result["verification"] = "Success"
            except Exception as e:
                result["verification_error"] = str(e)
                
            # Check type of subject claim
            if "sub" in unverified:
                result["sub_type"] = type(unverified["sub"]).__name__
                
        except Exception as e:
            result["decode_error"] = str(e)
    
    return result


@router.get("/debug-headers")
async def debug_headers(request: Request):
    """Debug endpoint that returns all headers"""
    # This will help us see if the Authorization header is being sent correctly
    headers = {key: value for key, value in request.headers.items()}
    
    # Special handling for Authorization to avoid leaking full token
    if "authorization" in headers:
        auth = headers["authorization"]
        if auth.startswith("Bearer "):
            token_part = auth[7:20] + "..." if len(auth) > 27 else auth[7:]
            headers["authorization"] = f"Bearer {token_part}"
    
    return {
        "headers": headers,
        "auth_header_present": "authorization" in [h.lower() for h in headers],
        "server_time": datetime.now().isoformat()
    }