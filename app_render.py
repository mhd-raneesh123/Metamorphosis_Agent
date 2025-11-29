import streamlit as st
import json
import os
import time
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

# Try importing the new Google GenAI SDK
try:
    from google import genai
    from google.genai import types
except ImportError:
    st.error("Google GenAI SDK not found. Please install: pip install google-genai")
    st.stop()

from huggingface_hub import InferenceClient

# ----------------------------------------------------
# 0. BASIC CONFIG
# ----------------------------------------------------
st.set_page_config(layout="wide", page_title="Metamorphosis Agent")

# Load environment variables (if .env exists)
load_dotenv()

# ----------------------------------------------------
# 1. CUSTOM CSS FOR DRAG & DROP
# ----------------------------------------------------
st.markdown("""
<style>
    /* Target the main file uploader container */
    [data-testid='stFileUploader'] {
        width: 100%;
        margin: 0 auto;
    }
    
    /* Style the dropzone area */
    [data-testid='stFileUploader'] section {
        padding: 4rem 2rem;
        background-color: transparent;
        border: 2px dashed #9ca3af;
        border-radius: 12px;
        text-align: center;
        transition: all 0.3s ease;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    /* Target the internal container of the uploader */
    [data-testid='stFileUploader'] section > div {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        width: 100%;
    }
    
    /* The SVG icon inside the uploader */
    [data-testid='stFileUploader'] section > div svg {
        margin-bottom: 10px;
    }

    /* Hover effect */
    [data-testid='stFileUploader'] section:hover {
        background-color: rgba(236, 253, 245, 0.1);
        border-color: #10b981;
        cursor: pointer;
    }

    /* HIDE the 'Browse files' button */
    [data-testid='stFileUploader'] button {
        display: none;
    }
    
    /* Center and style the small 'Limit 200MB' text */
    [data-testid='stFileUploader'] small {
        margin-top: 10px;
        color: #6b7280;
        font-size: 0.8rem;
        display: block;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------
# 2. SESSION RESET — ENSURES CLEAN START
# ----------------------------------------------------
if "app_initialized" not in st.session_state:
    st.session_state["uploaded_file_obj"] = None # Store the file object/bytes, not path
    st.session_state["unique_id"] = None
    st.session_state["blueprint_data"] = None
    st.session_state["vis_prompt"] = None
    st.session_state["generated_image_obj"] = None # Store result image in memory
    st.session_state["last_generation_status"] = None
    st.session_state["app_initialized"] = True

# ----------------------------------------------------
# 3. SIDEBAR & CLIENT INITIALIZATION
# ----------------------------------------------------
st.sidebar.header("Configuration")

# Allow API keys from .env OR Sidebar input
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    gemini_api_key = st.sidebar.text_input("Gemini API Key", type="password")

hf_token = os.getenv("HF_TOKEN")
if not hf_token:
    hf_token = st.sidebar.text_input("Hugging Face Token", type="password")

# Initialize Clients
gemini_client = None
hf_client = None

if gemini_api_key:
    try:
        gemini_client = genai.Client(api_key=gemini_api_key)
    except Exception as e:
        st.sidebar.error(f"Gemini Init Error: {e}")

if hf_token:
    try:
        hf_client = InferenceClient(token=hf_token)
    except Exception as e:
        st.sidebar.error(f"HF Init Error: {e}")

# ----------------------------------------------------
# 4. BLUEPRINT SCHEMA
# ----------------------------------------------------
DESIGN_SCHEMA = {
    "type": "object",
    "properties": {
        "design_title": {"type": "string"},
        "design_type": {"type": "string", "enum": ["Art Piece", "Small Furniture", "Accessory", "Tool"]},
        "material_breakdown": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "material_name": {"type": "string"},
                    "estimated_quantity": {"type": "string"},
                },
                "required": ["material_name", "estimated_quantity"],
            }
        },
        "assembly_steps_summary": {"type": "string"},
        "upcycle_score": {"type": "integer", "minimum": 1, "maximum": 10},
        "visualization_prompt": {"type": "string"},
    },
    "required": ["design_title", "design_type", "material_breakdown", "assembly_steps_summary", "upcycle_score", "visualization_prompt"]
}

# ----------------------------------------------------
# 5. GEMINI ANALYSIS (Memory Based)
# ----------------------------------------------------
@st.cache_data(show_spinner="Analyzing with Gemini...")
def run_gemini_analysis(_image_obj, client_api_key, unique_id): 
    if not gemini_client or not _image_obj:
        return None, None

    system_instruction = (
        "You are the 'Metamorphosis Agent'. Your goal is to help upcycle waste. "
        "1. ANALYZE the image and strictly identify the specific waste materials present (e.g., plastic bottles, cardboard, wood scrap). "
        "2. DESIGN a creative upcycling project using ONLY the materials found in the image (plus basic tools/adhesives). "
        "3. Do NOT hallucinate objects or materials that are not clearly visible in the input image. "
        "4. Generate a JSON blueprint strictly matching the provided schema."
    )

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=[system_instruction, _image_obj],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DESIGN_SCHEMA,
                temperature=0.7
            ),
        )
        
        blueprint = json.loads(response.text)
        vis_prompt = blueprint.pop("visualization_prompt", None)
        return blueprint, vis_prompt

    except Exception as e:
        st.error(f"Gemini API Error: {e}")
        return None, None

# ----------------------------------------------------
# 6. IMAGE GENERATION (Memory Based)
# ----------------------------------------------------
def generate_image_with_hf(prompt_text):
    if not hf_client:
        st.error("Hugging Face client not initialized.")
        return None

    try:
        with st.spinner("Dreaming up the design with Stable Diffusion..."):
            output = hf_client.text_to_image(
                prompt=f"Product design render, 4k photorealistic, cinematic lighting: {prompt_text}",
                model="stabilityai/stable-diffusion-xl-base-1.0",
                guidance_scale=7.5,
                num_inference_steps=30,
            )
            
            # If output is bytes, convert to PIL Image
            if not hasattr(output, "save"):
                image = Image.open(BytesIO(output))
            else:
                image = output
                
            return image
    except Exception as e:
        st.error(f"Image Generation Error: {e}")
        return None

# ----------------------------------------------------
# 7. CALLBACKS
# ----------------------------------------------------
def analyze_image_callback():
    uploaded_file = st.session_state.get("uploaded_file_obj")
    unique_id = st.session_state.get("unique_id", 0)

    if not uploaded_file:
        st.error("Upload an image first!")
        return

    # Convert uploaded file (BytesIO) to PIL Image for Gemini
    try:
        image_pil = Image.open(uploaded_file)
    except Exception as e:
        st.error(f"Error processing image: {e}")
        return

    blueprint, vis = run_gemini_analysis(image_pil, gemini_api_key, unique_id) 
    
    if blueprint:
        st.session_state["blueprint_data"] = blueprint
        st.session_state["vis_prompt"] = vis
        st.session_state["generated_image_obj"] = None
        st.session_state["last_generation_status"] = None

def generate_image_callback():
    vis_prompt = st.session_state.get("vis_prompt")
    if not vis_prompt:
        st.session_state["last_generation_status"] = "no_prompt"
        return

    gen_image = generate_image_with_hf(vis_prompt)
    if gen_image:
        st.session_state["generated_image_obj"] = gen_image
        st.session_state["last_generation_status"] = "success"
    else:
        st.session_state["last_generation_status"] = "failed"

def reset_app():
    st.session_state["uploaded_file_obj"] = None
    st.session_state["blueprint_data"] = None
    st.session_state["vis_prompt"] = None
    st.session_state["generated_image_obj"] = None
    st.session_state["last_generation_status"] = None
    st.session_state["unique_id"] = None
    st.rerun()

# ----------------------------------------------------
# 8. MAIN UI LOGIC
# ----------------------------------------------------
st.title("♻️ Metamorphosis Agent")

# IF NO IMAGE IS UPLOADED YET, SHOW THE LANDING PAGE
if not st.session_state["uploaded_file_obj"]:
    st.markdown("### Turn your discarded items into upcycled treasures.")
    st.write("Upload an image of waste/trash to get started.")
    
    uploaded_file = st.file_uploader(
        "Drag and drop the image", 
        type=["jpg", "jpeg", "png"], 
        label_visibility="collapsed"
    )

    if uploaded_file:
        # Store the file object in session state directly (Memory)
        st.session_state["uploaded_file_obj"] = uploaded_file
        st.session_state["unique_id"] = int(time.time())
        
        # Clear old data
        st.session_state["blueprint_data"] = None
        st.session_state["vis_prompt"] = None
        st.session_state["generated_image_obj"] = None
        
        st.rerun()

    st.markdown("---")
    st.info(" **Tip:** Try uploading plastic bottles, cardboard boxes, or old furniture.")

# IF IMAGE IS UPLOADED, SHOW THE WORKSPACE
else:
    if st.sidebar.button("📤 Upload New Image"):
        reset_app()
    
    # Display current item from memory
    st.sidebar.image(st.session_state["uploaded_file_obj"], caption="Current Item", use_container_width=True)
    
    if st.session_state["blueprint_data"] is None:
        col_img, col_act = st.columns([1, 1])
        with col_img:
            st.image(st.session_state["uploaded_file_obj"], caption="Uploaded Item", width=400)

        with col_act:
            st.subheader("Ready to analyze?")
            st.write("Our agent will identify materials and create a plan.")
            
            if gemini_client:
                if st.button(" Analyze Image", type="primary"):
                    analyze_image_callback()
                    st.rerun()
            else:
                st.warning("Please provide Gemini API Key in the sidebar.")

    else:
        blueprint = st.session_state["blueprint_data"]

        st.header(f" {blueprint.get('design_title', 'Untitled Design')}")
        st.caption(f"Category: {blueprint.get('design_type', 'General')}")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader(" The Plan")
            st.metric("Upcycle Score", f"{blueprint.get('upcycle_score')}/10")
            
            st.markdown("### Material Breakdown")
            for m in blueprint.get("material_breakdown", []):
                st.markdown(f"- **{m['material_name']}**: {m['estimated_quantity']}")

            st.markdown("### Assembly Steps")
            steps = blueprint.get("assembly_steps_summary", "")
            if isinstance(steps, str):
                st.write(steps)
            elif isinstance(steps, list):
                for i, step in enumerate(steps):
                    st.write(f"{i+1}. {step}")

        with col2:
            st.subheader(" Visualization")

            if hf_client:
                if st.button("Generate Concept Image", type="primary"):
                    generate_image_callback()
                    st.rerun()
            else:
                st.warning("Enter Hugging Face Token in sidebar to generate images.")

            gen_img = st.session_state["generated_image_obj"]
            status = st.session_state["last_generation_status"]

            if status == "failed":
                st.error("Generation failed. Check your Hugging Face token or internet.")
            elif gen_img:
                st.image(gen_img, caption="AI Generated Concept", use_container_width=True)