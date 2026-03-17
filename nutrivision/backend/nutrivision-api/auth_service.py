import boto3
import os
import uuid
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from schemas import UserRegister, UserLogin

# Ensure these match whatever you use in production
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-long-super-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

REGION_NAME = os.getenv("AWS_REGION", "us-east-1")
DYNAMODB_TABLE = os.getenv("DYNAMODB_TABLE", "nutrition-users")

# Set up DynamoDB resource
dynamodb = boto3.resource('dynamodb', region_name=REGION_NAME)
table = dynamodb.Table(DYNAMODB_TABLE)

# Password hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def register_user(user: UserRegister):
    # Quick check if user exists (Secondary index on email recommended for prod)
    # This is a naive scan for MVP purposes
    response = table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr('email').eq(user.email)
    )
    if response['Items']:
        raise ValueError("Email already registered")

    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user.password)

    item = {
        'id': user_id,  # This matches your partition key
        'email': user.email,
        'password_hash': hashed_password,
        'diet_goal': user.diet_goal,
        'health_conditions': user.health_conditions,
        'created_at': datetime.utcnow().isoformat()
    }

    table.put_item(Item=item)
    return {"id": user_id, "email": user.email}

def login_user(user: UserLogin):
    # Naive scan for MVP
    response = table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr('email').eq(user.email)
    )
    items = response.get('Items', [])
    if not items:
        return None
    
    db_user = items[0]
    if not verify_password(user.password, db_user['password_hash']):
        return None
    
    # Create token - Fixed: use 'id' instead of 'user_id'
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": db_user['id']}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

def get_user_profile(user_id: str):
    # Fixed: use 'id' as the key name to match your partition key
    response = table.get_item(Key={'id': user_id})
    return response.get('Item')
