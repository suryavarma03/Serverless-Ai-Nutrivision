import base64
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from schemas import UserRegister, UserLogin, UserProfile, BarcodeScan, ImageUpload
from auth_service import register_user, login_user, get_user_profile
from aws_services import lookup_openfoodfacts, invoke_worker_lambda

app = FastAPI(title="NutriVision API V2 (Serverless API Gateway Layer)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication Endpoints
@app.post("/register")
async def register(user: UserRegister):
    try:
        return register_user(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/login")
async def login(user: UserLogin):
    token = login_user(user)
    if not token:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return token

# Note: We take user_id as optional to allow guest analysis
# @app.post("/analyze-food")
# async def analyze_food(upload: ImageUpload, user_id: str = None):
#     """Passes Base64 image to the existing Worker Lambda for Rekognition & Bedrock."""
#     try:
#         user_profile = None
#         if user_id:
#             user_profile = get_user_profile(user_id)
            
#         # Instead of doing AI processing here, invoke the Worker Lambda
#         payload = {
#             "action": "analyze_food",
#             "image_base64": upload.image_base64,
#             "user_profile": user_profile
#         }
        
#         result = invoke_worker_lambda(payload)
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-food")
async def analyze_food(upload: ImageUpload, user_id: str = None):
    """Passes Base64 image to the existing Worker Lambda for Rekognition & Bedrock."""
    try:
        user_profile = None
        if user_id:
            user_profile = get_user_profile(user_id)
        
        # Use the original action name that works
        payload = {
            "action": "analyze_food",  
            "image_base64": upload.image_base64,            # Keep this - it's correct!
            "user_profile": user_profile or {     # Ensure it's never None
                "dietary_restrictions": []
            }
        }
        
        result = invoke_worker_lambda(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/scan-barcode")
async def scan_barcode(scan: BarcodeScan, user_id: str = None):
    """Analyses food from OpenFoodFacts via barcode -> Bedrock via Worker Lambda."""
    try:
        data = lookup_openfoodfacts(scan.barcode)
        if not data:
            raise HTTPException(status_code=404, detail="Barcode not found in database.")
            
        user_profile = None
        if user_id:
            user_profile = get_user_profile(user_id)
            
        # Delegate AI reasoning to the worker
        payload = {
            "action": "analyze_ingredients",
            "ingredients": data['ingredients'],
            "user_profile": user_profile
        }
        
        nutrition = invoke_worker_lambda(payload)
        
        return {
            "status": "success",
            "product_name": data['product_name'],
            "database_nutrition": data['nutrition_data'],
            "ai_nutrition": nutrition
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.post("/scan-ingredients")
async def scan_ingredients_label(upload: ImageUpload, user_id: str = None):
    """Passes Base64 image to existing Worker Lambda for Textract & Bedrock."""
    try:
        user_profile = None
        if user_id:
            user_profile = get_user_profile(user_id)
            
        # Delegate OCR and AI reasoning to the worker
        payload = {
            "action": "scan_ingredients",
            "image_base64": upload.image_base64,
            "user_profile": user_profile
        }
        
        result = invoke_worker_lambda(payload)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Wrap the FastAPI app with Mangum to convert AWS Lambda/API Gateway events into HTTP requests
handler = Mangum(app)
