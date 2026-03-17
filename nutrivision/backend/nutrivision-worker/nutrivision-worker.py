import json
import base64
import logging
import boto3
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError


# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize AWS clients
rekognition_client = boto3.client('rekognition')
textract_client = boto3.client('textract')
bedrock_client = boto3.client('bedrock-runtime')

# Constants
BEDROCK_MODEL_ID = "amazon.nova-lite-v1:0"
MAX_TOKENS = 512
TEMPERATURE = 0.7

IGNORE_LABELS = {
    "Food",
    "Fruit",
    "Plant",
    "Produce",
    "Meal",
    "Dish",
    "Cuisine",
    "Vegetation"
}

def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler that routes requests based on action type.
    
    Args:
        event: Lambda event containing action and payload
        context: Lambda context object
        
    Returns:
        Dict containing ingredients and nutrition analysis
    """
    try:
        logger.info(f"Processing request with event: {json.dumps(event, default=str)}")
        
        action = event.get("action")
        
        if not action:
            logger.error("Missing 'action' parameter in event")
            return create_error_response("Missing 'action' parameter", 400)
        
        # Route to appropriate handler based on action
        if action == "analyze_food":
            return handle_food_analysis(event)
        elif action == "scan_ingredients":
            return handle_ingredient_scan(event)
        elif action == "analyze_ingredients":
            return handle_ingredient_analysis(event)
        else:
            logger.error(f"Unknown action: {action}")
            return create_error_response(f"Unknown action: {action}", 400)
            
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {str(e)}", exc_info=True)
        return create_error_response("Internal server error", 500)

def handle_food_analysis(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle food analysis using Rekognition for label detection.
    
    Args:
        event: Event containing image_base64 and user_profile
        
    Returns:
        Dict containing ingredients and nutrition analysis
    """
    try:
        logger.info("Starting food analysis")
        
        # Validate required parameters
        image_base64 = event.get("image_base64")
        user_profile = event.get("user_profile", {})
        
        if not image_base64:
            return create_error_response("Missing 'image_base64' parameter", 400)
        
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(image_base64)
            logger.info(f"Decoded image size: {len(image_bytes)} bytes")
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {str(e)}")
            return create_error_response("Invalid base64 image data", 400)
        
        # Call Rekognition for label detection
        try:
            rekognition_response = rekognition_client.detect_labels(
                Image={"Bytes": image_bytes},
                MaxLabels=20,
                MinConfidence=70.0
            )
            # Extract food-related labels
            labels = rekognition_response.get('Labels', [])

            food_labels = []

            for label in labels:
                name = label['Name']
                confidence = label['Confidence']

                if confidence > 70.0 and name not in IGNORE_LABELS:
                    food_labels.append((name, confidence))

            # Sort by confidence
            food_labels.sort(key=lambda x: x[1], reverse=True)

            # Keep top 3 labels only
            food_labels = [label[0] for label in food_labels[:3]]

            logger.info(f"Filtered food labels: {food_labels}")

            if not food_labels:
                return create_error_response("No specific food items detected", 400)

            # Convert labels to ingredient text
            ingredient_text = ", ".join(food_labels)
            
        except ClientError as e:
            logger.error(f"Rekognition API error: {str(e)}")
            return create_error_response("Failed to analyze image", 500)
        
        # Call Bedrock for nutrition analysis
        nutrition_analysis = call_bedrock_for_nutrition(ingredient_text, user_profile)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "food": food_labels[0] if food_labels else "Unknown",
                "ingredients": food_labels,
                "nutrition": nutrition_analysis
            })
        }
        
    except Exception as e:
        logger.error(f"Error in handle_food_analysis: {str(e)}", exc_info=True)
        return create_error_response("Failed to analyze food", 500)

def handle_ingredient_scan(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle ingredient scanning using Textract for text detection.
    
    Args:
        event: Event containing image_base64 and user_profile
        
    Returns:
        Dict containing ingredients and nutrition analysis
    """
    try:
        logger.info("Starting ingredient scan")
        
        # Validate required parameters
        image_base64 = event.get("image_base64")
        user_profile = event.get("user_profile", {})
        
        if not image_base64:
            return create_error_response("Missing 'image_base64' parameter", 400)
        
        # Decode base64 image
        try:
            image_bytes = base64.b64decode(image_base64)
            logger.info(f"Decoded image size: {len(image_bytes)} bytes")
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {str(e)}")
            return create_error_response("Invalid base64 image data", 400)
        
        # Call Textract for text detection
        try:
            textract_response = textract_client.detect_document_text(
                Document={"Bytes": image_bytes}
            )
            
            # Extract text blocks
            blocks = textract_response.get('Blocks', [])
            detected_text = []
            
            for block in blocks:
                if block['BlockType'] == 'LINE' and block.get('Text'):
                    detected_text.append(block['Text'].strip())
            
            # Join all detected text
            full_text = " ".join(detected_text).lower()
            logger.info(f"OCR full text: {full_text}")
            ingredient_section = ""

            if "ingredients" in full_text:
                ingredient_section = full_text.split("ingredients")[1]

            elif "ingredient" in full_text:
                ingredient_section = full_text.split("ingredient")[1]

            else:
                ingredient_section = full_text
            logger.info(f"Detected text: {ingredient_section}")
            
            if not ingredient_section.strip():
                return create_error_response("No text detected in image", 400)
            
            # Parse ingredients from text (simple comma/newline separation)
            ingredients = [
                ingredient.strip() 
                for ingredient in ingredient_section.replace('\n', ',').split(',')
                if ingredient.strip()
            ]
            
        except ClientError as e:
            logger.error(f"Textract API error: {str(e)}")
            return create_error_response("Failed to scan ingredients", 500)
        
        # Call Bedrock for nutrition analysis
        nutrition_analysis = call_bedrock_for_nutrition(ingredient_section, user_profile)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "ingredients": ingredients,
                "nutrition": nutrition_analysis
            })
        }
        
    except Exception as e:
        logger.error(f"Error in handle_ingredient_scan: {str(e)}", exc_info=True)
        return create_error_response("Failed to scan ingredients", 500)

def handle_ingredient_analysis(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle direct ingredient analysis without image processing.
    
    Args:
        event: Event containing ingredients text and user_profile
        
    Returns:
        Dict containing ingredients and nutrition analysis
    """
    try:
        logger.info("Starting ingredient analysis")
        
        # Validate required parameters
        ingredients_text = event.get("ingredients")
        user_profile = event.get("user_profile", {})
        
        if not ingredients_text:
            return create_error_response("Missing 'ingredients' parameter", 400)
        
        logger.info(f"Analyzing ingredients: {ingredients_text}")
        
        # Parse ingredients list
        # ingredients = [
        #     ingredient.strip() 
        #     for ingredient in ingredients_text.split(',')
        #     if ingredient.strip()
        # ]
        
        raw_ingredients = ingredients_text.replace(":", "").split(",")

        ingredients = []

        for item in raw_ingredients:
            cleaned = item.strip()

            if len(cleaned) > 2 and len(cleaned) < 60:
                ingredients.append(cleaned)

                # Call Bedrock for nutrition analysis
                nutrition_analysis = call_bedrock_for_nutrition(ingredients_text, user_profile)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "ingredients": ingredients,
                "nutrition": nutrition_analysis
            })
        }
        
    except Exception as e:
        logger.error(f"Error in handle_ingredient_analysis: {str(e)}", exc_info=True)
        return create_error_response("Failed to analyze ingredients", 500)

def call_bedrock_for_nutrition(ingredient_text: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call Amazon Bedrock Nova Lite model for nutrition analysis.
    
    Args:
        ingredient_text: String containing ingredients to analyze
        user_profile: User profile information for personalized analysis
        
    Returns:
        Dict containing nutrition analysis results
    """
    try:
        logger.info("Calling Bedrock for nutrition analysis")
        # Build personalized prompt
        prompt = build_nutrition_prompt(ingredient_text, user_profile)
        
        # Prepare Bedrock request using messages API
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            "inferenceConfig": {
                "maxTokens": MAX_TOKENS,
                "temperature": TEMPERATURE
            }
        }
        
        # Call Bedrock
        response = bedrock_client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=json.dumps(request_body),
            contentType="application/json"
        )
        
        #Parse response
        response_body = json.loads(response['body'].read())
        
        # Extract the generated text
        if 'output' in response_body and 'message' in response_body['output']:
            nutrition_text = response_body['output']['message']['content'][0]['text']
        else:
            logger.warning("Unexpected Bedrock response format")
            nutrition_text = "Unable to generate nutrition analysis"
        
        logger.info("Bedrock nutrition analysis completed")
        logger.info("Raw Bedrock response:")
        logger.info(nutrition_text)

        # Remove markdown formatting if present
        nutrition_text = nutrition_text.replace("```json", "")
        nutrition_text = nutrition_text.replace("```", "")
        nutrition_text = nutrition_text.strip()
        
        try:
            nutrition_data = json.loads(nutrition_text)
            logger.info("Nutrition JSON parsed successfully")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {str(e)}")
            nutrition_data = {"analysis": nutrition_text}

        return nutrition_data

    except ClientError as e:
        logger.error(f"Bedrock API error: {str(e)}")
        return {"error": "Failed to generate nutrition analysis"}
    except Exception as e:
        logger.error(f"Error in call_bedrock_for_nutrition: {str(e)}", exc_info=True)
        return {"error": "Failed to generate nutrition analysis"}

def build_nutrition_prompt(ingredient_text: str, user_profile: Dict[str, Any]) -> str:
    if user_profile is None:
        user_profile = {}
    
    health_goals = user_profile.get("health_goals", [])
    dietary_restrictions = user_profile.get("dietary_restrictions", [])
    allergies = user_profile.get("allergies", [])
    
    prompt = f"""
You are a professional nutritionist AI.

Analyze the following food ingredients and produce a clean nutrition summary for a mobile application.

Food detected:
{ingredient_text}

User profile:
Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
Health goals: {', '.join(health_goals) if health_goals else 'None'}
Allergies: {', '.join(allergies) if allergies else 'None'}

Return ONLY valid JSON.

Structure:
{{
    "food_name": "detected food",
    "nutritional_breakdown": {{
        "calories_per_serving": number,
        "macronutrients": {{
            "carbohydrates": "g",
            "protein": "g",
            "fat": "g"
        }},
        "key_nutrients": ["..."]
    }},
    "ingredient_analysis": [
        {{
            "name": "ingredient name",
            "category": "good or bad",
            "reason": "why it is good or bad for health"
        }}
    ],
    "health_assessment": {{
        "benefits": ["..."],
        "concerns": ["..."],
        "overall_score": number
    }},
    "personalized_recommendations": ["..."]
}}

DO NOT include markdown.
DO NOT include explanations outside JSON.
"""
    
    return prompt.strip()


def create_error_response(message: str, status_code: int = 500) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        message: Error message
        status_code: HTTP status code
        
    Returns:
        Dict containing error response
    """
    return {
        "statusCode": status_code,
        "body": json.dumps({
            "error": message
        })
    }
