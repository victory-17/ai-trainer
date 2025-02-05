import streamlit as st
from PIL import Image
import io
import base64
import requests
#import tiktoken  # For token size validation

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# Initialize welcome message if it's not in chat history
if not st.session_state["chat_history"]:
    welcome_message = """Hello! 👋 I'm your AI Fitness Trainer and Nutritionist. 
I'm here to help you with:
• Nutrition advice and meal analysis 🍎
• Exercise recommendations 💪
• Fitness equipment guidance 🏋️‍♂️
• General health and wellness questions ❤️

Feel free to ask me anything or upload images of food/equipment for analysis!"""
    
    st.session_state["chat_history"].append({
        "role": "assistant",
        "content": welcome_message
    })

# Add this at the top with other session state initializations
if "processing_image" not in st.session_state:
    st.session_state.processing_image = False

# Add these to the session state initializations at the top
if "current_image_id" not in st.session_state:
    st.session_state.current_image_id = None

# Custom CSS for the interface
st.markdown("""
    <style>
    .main {
        background-color: #f0f2f6;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .chat-message {
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        color: #000000;
        font-size: 0.9em;
    }
    .user-message {
        background-color: #e8f5e9;
        margin-left: 10%;
        margin-right: 2%;
    }
    .bot-message {
        background-color: #f5f5f5;
        margin-right: 10%;
        margin-left: 2%;
    }
    .stTextInput {
        position: fixed;
        bottom: 20px;
        width: 80%;
    }
    .stButton button {
        width: 100%;
        border-radius: 20px;
    }
    .stTextInput input {
        border-radius: 20px;
    }
    div[data-testid="stVerticalBlock"] > div:has(div.stButton) {
        margin-top: -20px;
    }
    </style>
""", unsafe_allow_html=True)

def encode_image_to_base64(image):
    """Convert PIL Image to base64 string."""
    # Convert RGBA to RGB if necessary
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        background.paste(image, mask=image.split()[-1])
        image = background
    elif image.mode != 'RGB':
        image = image.convert('RGB')

    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

def get_image_analysis_gemini(image, image_type):
    """Get AI analysis for uploaded image using Gemini API."""
    try:
        # Optimize image before encoding
        img_base64 = encode_image_to_base64(image)

        # Define the prompt based on the image type
        if image_type == "food":
            user_prompt = """Analyze this meal photo and provide:
            1. List of visible food items
            2. Estimated total calories
            3. Macronutrient breakdown (protein, carbs, fats)
            4. Nutritional advice
            Keep the response concise and focused.
            """
        else:  # gym equipment
            user_prompt = """Analyze this gym equipment photo and provide:
            1. Equipment name and type
            2. Primary purpose
            3. Target muscle groups
            4. Usage instructions
            5. Alternative exercises
            Keep the response concise and focused.
            """

        # API call with timeout
        gemini_api_url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": "AIzaSyDniam4TLId5RAR8eDcglYwk4zaBYmsRo8"
        }
        
        payload = {
            "contents": [{
                "parts": [
                    {"text": user_prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": img_base64
                        }
                    }
                ]
            }],
            "generation_config": {
                "temperature": 0.4,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 800  # Limit response length
            }
        }

        # Make API call with timeout
        response = requests.post(gemini_api_url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No analysis available.")
        else:
            return f"Error analyzing image (Status: {response.status_code}). Please try again."

    except requests.Timeout:
        return "Request timed out. Please try again."
    except Exception as e:
        return f"Error analyzing image: {str(e)}"


def process_uploaded_image(image_file, image_type):
    """Process uploaded images with AI analysis using Gemini."""
    # Generate a unique ID for this image
    image_id = f"{image_type}_{hash(image_file.getvalue())}"
    
    # Check if this exact image has already been processed
    if st.session_state.current_image_id == image_id:
        return
    
    st.session_state.current_image_id = image_id
    
    try:
        # Open and display the image
        image = Image.open(image_file)
        
        # Resize image if too large (optimize for API)
        max_size = (800, 800)
        if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Display image immediately to show progress
        st.image(image, caption=f"Uploaded {image_type}", use_container_width=True)
        
        # Show spinner while processing
        with st.spinner(f"Analyzing {image_type}..."):
            analysis = get_image_analysis_gemini(image, image_type)
            if analysis:
                st.success("Analysis complete!")
                
                # Create an expander for the analysis
                with st.expander("View Analysis", expanded=True):
                    st.write(analysis)
        
                # Convert image to base64 for chat history
                buffered = io.BytesIO()
                image.save(buffered, format="JPEG", quality=85, optimize=True)
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                # Add to chat history
                st.session_state["chat_history"].append({
                    "role": "user",
                    "content": f"[Uploaded {image_type} image]",
                    "image": img_str
                })
                
                st.session_state["chat_history"].append({
                    "role": "assistant",
                    "content": analysis
                })
            else:
                st.error("Failed to analyze image. Please try again.")
        
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")

def process_text_input(user_input):
    """Process text input and get AI response using Gemini."""
    try:
        # Change to use gemini-1.5-flash model instead of pro
        gemini_api_url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": "AIzaSyDniam4TLId5RAR8eDcglYwk4zaBYmsRo8"
        }
        
        payload = {
            "contents": [{
                "parts": [{"text": f"""As an AI fitness trainer and nutritionist, please respond to: {user_input}
                         Provide specific, actionable advice related to fitness, nutrition, or health."""}]
            }],
            "generation_config": {
                "temperature": 0.4,
                "top_p": 0.8,
                "top_k": 40,
            },
            "safety_settings": [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                }
            ]
        }

        # Make API call with timeout
        response = requests.post(gemini_api_url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            result = response.json()
            generated_text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return generated_text if generated_text else "I couldn't generate a response. Please try again."
        elif response.status_code == 503:
            return "The service is temporarily unavailable. Please wait a moment and try again."
        elif response.status_code == 429:
            return "I'm receiving too many requests. Please wait a moment and try again."
        else:
            return "I'm having trouble understanding that. Could you please rephrase your question?"

    except requests.Timeout:
        return "The request timed out. Please try again with a simpler question."
    except requests.RequestException as e:
        return "Network error occurred. Please check your connection and try again."
    except Exception as e:
        return "I encountered an unexpected error. Please try again with a different question."

# Main app layout
st.title("🏋️‍♂️ AI Fitness Trainer")

# Create tabs for different sections
tab1, tab2 = st.tabs(["💬 Chat & Analysis", "📸 Upload Images"])

with tab1:
    # Chat container for history
    chat_container = st.container()
    
    # Display chat history in main window
    with chat_container:
        for message in st.session_state["chat_history"]:
            if message["role"] == "user":
                st.markdown(f'<div class="chat-message user-message">🧑‍💼 You: {message["content"]}</div>', 
                           unsafe_allow_html=True)
                # Display image if it exists in the message
                if "image" in message:
                    st.image(f"data:image/jpeg;base64,{message['image']}", 
                            caption="Uploaded Image",
                            use_container_width=True)
            else:
                st.markdown(f'<div class="chat-message bot-message">🤖 Trainer: {message["content"]}</div>', 
                           unsafe_allow_html=True)
    
    # Chat input area
    st.markdown("<br>" * 2, unsafe_allow_html=True)  # Add some space
    
    # Initialize the session state for input if it doesn't exist
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""

    # Create a form for the chat input
    with st.form(key="chat_form"):
        user_input = st.text_input("Ask me anything about fitness or nutrition...", 
                                  key="user_input")
        
        # Put the send button right after the input in the same form
        send_button = st.form_submit_button("Send 📤")

        if send_button and user_input:
            # Add user message to chat history
            st.session_state["chat_history"].append({
                "role": "user",
                "content": user_input
            })
            
            # Get AI response
            ai_response = process_text_input(user_input)
            
            # Add AI response to chat history
            st.session_state["chat_history"].append({
                "role": "assistant",
                "content": ai_response
            })
            
            # Force a rerun to update the chat
            st.rerun()

with tab2:
    # Food Analysis Section
    st.markdown("### 🍽️ Analyze Food")
    food_image = st.file_uploader("Upload meal photo", type=["jpg", "png", "jpeg"], key="food")
    if food_image:
        process_uploaded_image(food_image, "food")

    st.markdown("<br>", unsafe_allow_html=True)

    # Equipment Analysis Section
    st.markdown("### 💪 Identify Equipment")
    equipment_image = st.file_uploader("Upload gym equipment photo", type=["jpg", "png", "jpeg"], key="equipment")
    if equipment_image:
        process_uploaded_image(equipment_image, "equipment")

# Sidebar for chat history labels
with st.sidebar:
    st.header("💬 Chat History")
    
    # Display only labels/summaries of chat history
    for idx, message in enumerate(st.session_state["chat_history"]):
        if message["role"] == "user":
            content = message["content"]
            # Check if it's an image upload
            if "[Uploaded" in content:
                st.markdown(f"**Message {idx + 1}:** {content}")
            else:
                # Truncate long messages
                if len(content) > 30:
                    content = content[:27] + "..."
                st.markdown(f"**Message {idx + 1}:** {content}")
    
    # Clear chat button
    if st.button("Clear Chat"):
        st.session_state["chat_history"] = []
        st.session_state.current_image_id = None
        st.rerun()
