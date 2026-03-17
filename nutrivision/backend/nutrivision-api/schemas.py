import os
from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    diet_goal: Optional[str] = None
    health_conditions: Optional[List[str]] = []

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    user_id: str
    email: EmailStr
    diet_goal: Optional[str] = None
    health_conditions: Optional[List[str]] = []

class Token(BaseModel):
    access_token: str
    token_type: str

class BarcodeScan(BaseModel):
    barcode: str

class ImageUpload(BaseModel):
    image_base64: str
