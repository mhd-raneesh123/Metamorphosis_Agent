# design_agent.py

import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO

# Load environment variables (to get the API key)
load_dotenv()
# This is the "blueprint" Gemini must fill.

DESIGN_SCHEMA = {
    "type": "object",
    "properties": {
        "design_title": {
            "type": "string",
            "description": "A creative name for the upcycled project."
        },
        "design_type": {
            "type": "string",
            "enum": ["Art Piece", "Small Furniture", "Accessory", "Tool"],
            "description": "The category of the final upcycled object."
        },
        "material_breakdown": {
            "type": "array",
            "description": "A detailed list of the core materials and estimated quantities from the image.",
            "items": {
                "type": "object",
                "properties": {
                    "material_name": {"type": "string", "description": "e.g., Plastic Bottle Caps, Copper Wire"},
                    "estimated_quantity": {"type": "string", "description": "e.g., ~50 units, ~3 meters"},
                },
                "required": ["material_name", "estimated_quantity"],
            }
        },
        "assembly_steps_summary": {
            "type": "string",
            "description": "A concise, step-by-step summary of how to build the design."
        },
        "upcycle_score": {
            "type": "integer",
            "description": "A feasibility score (1-10) based on material quality and complexity. Higher is better.",
            "minimum": 1,
            "maximum": 10
        }
    },
    "required": ["design_title", "design_type", "material_breakdown", "assembly_steps_summary", "upcycle_score"]
}


# In design_agent.py

def analyze_waste_and_design(image_path: str, client: genai.Client):
    """
    Analyzes an image of waste material and generates a structured design blueprint.
    """
    try:
        # 1. Image Loading Check
        img = Image.open(image_path)
    except FileNotFoundError:
        print(f"ERROR: Image file not found at {image_path}. Please verify the path.")
        return
    except Exception as e:
        print(f"ERROR: Could not open image file: {e}")
        return

    # --- Configuration and Prompts (Keep these as they are) ---
    system_instruction = (
        "You are the 'Metamorphosis Agent,' an expert industrial designer specializing in "
        "sustainable upcycling and creative constraints. Your task is to analyze the "
        "waste material provided in the image and generate ONE unique design for a new, "
        "functional, or artistic object. "
        "Your design MUST strictly adhere to the structural JSON output provided. "
        "Do not include any text outside of the JSON object."
    )
    
    user_prompt = (
        "Analyze the following image of discarded materials. "
        "Determine the material type, estimated quantity, and dominant colors. "
        "Then, generate a creative and feasible blueprint for a new object that can be built "
        "using ONLY the materials seen in the image. Be innovative and focus on environmental sustainability."
    )

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=DESIGN_SCHEMA,
        temperature=0.8, # Use higher temp for creative results
    )
    
    # 2. Make the Multimodal API Call
    print("Sending request to Gemini API... (This may take a moment)")
    
    response = client.models.generate_content(
        model='gemini-2.5-flash', # Use Flash for high-speed multimodal reasoning
        contents=[user_prompt, img],
        config=config,
    )
    
    # Check for empty text (the primary symptom)
    if not response.text:
        print("\n--- TROUBLESHOOTING: EMPTY RESPONSE TEXT ---")
        
        # Check for candidates and finish reason (to find safety blocks)
        if response.candidates and response.candidates[0].finish_reason:
            reason = response.candidates[0].finish_reason
            
            if reason == types.FinishReason.SAFETY:
                print(f" ERROR: Request blocked by Safety Filter.")
                print("The image or prompt content was flagged. Try a different, less ambiguous image.")
            else:
                print(f"API returned no text (Finish Reason: {reason}). This often means a JSON generation failure or internal error. Try running with a simpler image/prompt.")
        else:
            print("API returned an empty response with no specific reason. This may be a service-side error or a complex JSON failure.")
        return

    # If text is present, proceed with JSON decoding
    try:
        design_blueprint = json.loads(response.text)
        print("\n --- AI GENERATED DESIGN BLUEPRINT (SUCCESS) ---")
        print(json.dumps(design_blueprint, indent=4))
        
        # Display the custom score
        print("\n--- Project Metrics ---")
        print(f"Design Title: {design_blueprint['design_title']}")
        print(f"Feasibility/Upcycle Score (1-10): {design_blueprint['upcycle_score']}")
        print(f"Material Type: {design_blueprint['design_type']}")
        
    except json.JSONDecodeError as e:
        print("\n--- ERROR: JSON DECODING FAILURE ---")
        print("Gemini returned text, but it was NOT valid JSON.")
        print("This usually means the prompt needs better structure/instruction.")
        print("Raw text response (look for extra text or markdown blocks):")
        print(response.text)
        print(f"Decoding Error: {e}")

# --- Main Execution Block ---

if __name__ == "__main__":
    # Initialize the client (it reads the API key from the .env file)
    try:
        gemini_client = genai.Client()
    except Exception:
        print("ERROR: Could not initialize Gemini client. Ensure GEMINI_API_KEY is set correctly in your .env file.")
        exit()
        
    # **REPLACE 'path/to/your/waste_image.jpg' with an actual path to a photo of trash/scraps.**
    # Example image idea: A photo of old computer keyboards, wine corks, or plastic toys.
    IMAGE_FILE = r"C:\Users\hp\Downloads\metamorphosis-agent\waste.jpg"
    # Run the agent
    analyze_waste_and_design(IMAGE_FILE, gemini_client)