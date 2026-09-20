# NutriVision V2 - Serverless Architecture

NutriVision is an AI-powered nutrition analysis web application using a modern **AWS Serverless Architecture**. 

## Core Architecture
- **Frontend**: S3 Static Website Hosting (HTML/CSS/JS)
- **API Routing**: AWS API Gateway
- **Compute layer**: AWS Lambda (FastAPI wrapped with Mangum)
- **Database**: Amazon DynamoDB (User Profiles & Preferences)
- **AI Services**: 
  - Amazon Rekognition (Food image detection)
  - Amazon Textract (Ingredient label OCR)
  - Amazon Bedrock `amazon.nova-lite-v1:0` (Nutrition analysis & personalized recommendations)
- **External APIs**: OpenFoodFacts (Barcode scanning)

---

## Project Structure

```text
nutrivision/
│
├── backend/
│   ├── main.py              # FastAPI app wrapped with Mangum
│   ├── aws_services.py      # Boto3 clients for Rekognition, Textract, Bedrock
│   ├── auth_service.py      # JWT Auth and DynamoDB interactions
│   ├── schemas.py           # Pydantic models for API validation
│   ├── requirements.txt     # Python dependencies
│
├── frontend/
│   ├── index.html           # Landing Dashboard
│   ├── login.html           # JWT Auth login
│   ├── register.html        # Creates Dynamo profile with health conditions
│   ├── analyze.html         # Image upload -> Rekognition -> Bedrock
│   ├── barcode.html         # ID scanning & Textract OCR -> Bedrock
│   ├── styles.css           # Modern Dark UI
│
└── README.md
```

---

## Local Development Setup

### 1. Backend (FastAPI)

Ensure you have your AWS credentials configured locally (`aws configure`). You will need permissions to invoke Rekognition, Textract, Bedrock, and to access a DynamoDB table named `NutriVisionUsers`.

```bash
cd backend
pip install -r requirements.txt

# Start the uvicorn server locally
uvicorn main:app --reload
```

The server runs on `http://127.0.0.1:8000`.

### 2. Frontend

The frontend is vanilla HTML/CSS/JS and relies on the Fetch API.

```bash
cd frontend
# Start a simple Python web server
python -m http.server 3000
```
Open `http://localhost:3000` in your browser. Complete the flow by creating an account, logging in, and analyzing a food image or barcode!

---

## Serverless Deployment Instructions

To deploy to AWS Serverless architecture:

1. **DynamoDB**: Create a table named `NutriVisionUsers` with Partition Key `user_id` (String).
2. **Lambda & API Gateway**: package the `backend` folder contents (including dependencies installed locally via `pip install -t . -r requirements.txt`) into a `.zip` file. Upload this to AWS Lambda.
3. Configure **API Gateway** as an HTTP API triggering the Lambda function using the `{proxy+}` route integration.
4. Set Lambda Environment Variables:
   - `JWT_SECRET_KEY`: Random secure string
   - `AWS_REGION`: e.g. `us-east-1`
   - `DYNAMODB_TABLE`: `NutriVisionUsers` 
5. **Frontend Hosting**: Sync the `frontend/` directory to an AWS S3 bucket configured for Static Website Hosting. Update the `fetch()` URLs in the Javascript files to point to your new API Gateway URL instead of `localhost:8000`.
