import jwt
import sys

def decode_jwt(token):
    """Decode a JWT token without verification."""
    try:
        # This does not verify the token, just decodes it
        decoded = jwt.decode(token, options={"verify_signature": False})
        print("JWT Token Contents:")
        for key, value in decoded.items():
            print(f"{key}: {value}")
    except Exception as e:
        print(f"Error decoding token: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python decode_jwt.py <jwt_token>")
        sys.exit(1)
        
    token = sys.argv[1]
    decode_jwt(token)
