import streamlit as st
import requests
import uuid
import json
from datetime import datetime
import os

# ------------------------------
# Configuration
# ------------------------------
API_URL = os.getenv('API_URL')

# ------------------------------
# Helper Functions
# ------------------------------
def call_bedrock_agent(user_input, session_id):
    """
    Sends user input to the API Gateway endpoint and returns the agent's response.
    This version handles potential nested JSON responses from API Gateway/Lambda.
    """
    headers = {"Content-Type": "application/json"}
    payload = {"user_input": user_input, "session_id": session_id}

    try:
        response = requests.post(API_URL, json=payload, headers=headers, timeout=45)
        response.raise_for_status()
        data = response.json()

        # API Gateway/Lambda can sometimes wrap the actual response in a 'body' field.
        # This logic checks for that and parses the inner JSON string if it exists.
        if "body" in data:
            try:
                inner_data = json.loads(data["body"])
            except json.JSONDecodeError:
                st.error("Failed to decode the nested JSON response from API Gateway.")
                return "Error: Invalid response format.", session_id
        else:
            inner_data = data
            
        return inner_data.get("response", "No response content received."), inner_data.get("session_id", session_id)

    except requests.exceptions.RequestException as e:
        st.error(f"API Call Error: {e}")
        return "Sorry, I'm having trouble connecting to the service.", session_id

def make_friendly_name():
    """Generate a human-readable name for a new session using the current timestamp."""
    timestamp = datetime.now().strftime("%b %d, %H:%M")
    return f"Chat {len(st.session_state.get('previous_sessions', [])) + 1} – {timestamp}"

# ------------------------------
# Streamlit UI
# ------------------------------
def main():
    st.set_page_config(
        page_title="Product Search",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # --- Custom CSS for a light, minimal chat look ---
    st.markdown("""
        <style>
        /* General Body Styling - Light Theme */
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background-color: #ffffff;
            color: #333333;
        }
        
        /* Title smaller with San Francisco font */
        h1 {
            font-size: 2.5em !important;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "San Francisco", "Segoe UI", Roboto, sans-serif !important;
        }
        
        /* Main chat container - reduce top padding to move title up */
        .main .block-container {
            padding-top: 0.5rem;
            padding-bottom: 5rem; /* Space for chat input */
        }
        
        /* Ensure main app area has light background */
        [data-testid="stAppViewContainer"] > .main {
            background-color: #ffffff;
        }

        /* Sidebar Styling - Black */
        [data-testid="stSidebar"] {
            background-color: #000000; /* Black sidebar */
            border-right: 1px solid #333333;
            padding: 1.5rem;
        }
        
        /* Sidebar text color - Grey */
        [data-testid="stSidebar"] * {
            color: #cccccc !important;
        }
        
        /* Sidebar headings */
        [data-testid="stSidebar"] h1, 
        [data-testid="stSidebar"] h2, 
        [data-testid="stSidebar"] h3 {
            color: #e0e0e0 !important;
        }
        
        /* Sidebar markdown text */
        [data-testid="stSidebar"] .stMarkdown {
            color: #cccccc !important;
        }
        
        /* Chat bubble styling - rounded for user messages only */
        [data-testid="stChatMessage"][data-testid*="user"] {
            background-color: #f8f9fa; /* Light gray chat bubbles */
            border: 1px solid #e9ecef;
            border-radius: 30px;
            box-shadow: none;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem;
            margin-left: auto;
            max-width: 80%;
        }
        
        /* User messages right aligned */
        [data-testid="stChatMessage"]:has([data-testid*="user"]) {
            display: flex;
            justify-content: flex-end;
        }
        
        /* Assistant messages: no bubble */
        [data-testid="stChatMessage"]:has([role="assistant"]) {
            background-color: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            padding: 0 !important;
            margin-bottom: 1rem !important;
        }
        
        /* Avatar styling - circular black */
        .stAvatar {
            border-radius: 50% !important;
            background-color: rgba(0,0,0,0.1) !important;
        }
        
        /* Style for messages */
        [data-testid="stChatMessage"] p {
             margin: 0;
             color: #333333;
             line-height: 1.5;
        }

        /* Sample queries bubble styling */
        .sample-queries-bubble {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 30px;
            padding: 1.5rem;
            font-size: 0.9em;
            opacity: 0.8;
            text-align: left;
            max-width: 600px;
            margin: 0 auto 2rem auto;
        }
        
        /* Hide avatar for sample queries */
        .hide-avatar .stAvatar {
            display: none !important;
        }
        
        .hide-avatar [data-testid="stChatMessage"] {
            padding-left: 0 !important;
        }
        
        /* Sidebar title smaller */
        [data-testid="stSidebar"] h1 {
            font-size: 1.5em !important;
        }
        
        /* Sidebar headings - reduce size */
        [data-testid="stSidebar"] h2 {
            font-size: 1.2em !important;
            margin-bottom: 0.5rem !important;
        }
        
        [data-testid="stSidebar"] h3 {
            font-size: 1em !important;
            margin-bottom: 0.5rem !important;
        }
        
        /* Sidebar paragraphs - smaller font */
        [data-testid="stSidebar"] p {
            font-size: 0.85em !important;
        }
        
        /* Add spacing between sections */
        [data-testid="stSidebar"] .section-gap {
            margin-top: 2.5rem !important;
            margin-bottom: 1rem !important;
        }

        /* Button Styling - Grey */
        div.stButton > button {
            background-color: #e9ecef; /* Grey */
            color: #333333 !important;
            border: none;
            border-radius: 30px;
            padding: 0.5rem 1rem;
            font-weight: 500;
            transition: all 0.2s ease-in-out;
        }
        div.stButton > button:hover {
            background-color: #d3d6d9; /* Darker grey */
            color: #333333 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Sidebar buttons - Grey with no red hover */
        [data-testid="stSidebar"] div.stButton > button {
            background-color: #333333; /* Dark grey */
            color: #cccccc !important;
            border: 1px solid #555555;
        }
        [data-testid="stSidebar"] div.stButton > button:hover {
            background-color: #444444; /* Lighter grey */
            color: #cccccc !important;
        }

        /* Title color */
        h1, h2, h3, h4, h5, h6 {
            color: #333333 !important;
        }

        /* Input text color and rounded borders */
         .stTextInput, .stTextArea, .stChatInput {
            color: #333333;
        }
        .stTextInput input, .stTextArea textarea, .stChatInput input {
            color: #333333;
            background-color: #ffffff;
            border-radius: 30px !important;
        }
        
        /* Selectbox rounded */
        .stSelectbox > div > div {
            border-radius: 30px !important;
        }
        
        /* Sidebar selectbox styling */
        [data-testid="stSidebar"] .stSelectbox > div > div {
            background-color: #333333 !important;
            color: #cccccc !important;
            border-color: #555555 !important;
        }
        
        [data-testid="stSidebar"] .stSelectbox label {
            color: #cccccc !important;
        }
        
        /* Info box rounded */
        .stInfo {
            border-radius: 30px !important;
        }
        
        /* Sidebar info box styling */
        [data-testid="stSidebar"] .stInfo {
            background-color: #1a1a1a !important;
            border-color: #555555 !important;
            color: #cccccc !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Session State Initialization ---
    if "session" not in st.session_state:
        st.session_state.session = {"id": str(uuid.uuid4()), "name": "Current Chat"}
    if "previous_sessions" not in st.session_state:
        st.session_state.previous_sessions = []
    if "chat_memory" not in st.session_state:
        st.session_state.chat_memory = {}

    # --- Sidebar for Session Management ---
    with st.sidebar:
        st.markdown("### About")
        st.markdown("You can search for products that are active, their cost and the stock information.")
        
        st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
        
        st.markdown("### Chat Sessions")

        if st.button("New Chat", use_container_width=True):
            if st.session_state.session not in st.session_state.previous_sessions:
                st.session_state.previous_sessions.append(st.session_state.session)
                if len(st.session_state.previous_sessions) > 10: # Limit history
                    st.session_state.previous_sessions.pop(0)
            
            st.session_state.session = {"id": str(uuid.uuid4()), "name": make_friendly_name()}
            st.success("New chat started!")
            st.rerun()

        st.markdown("---")

        if st.session_state.previous_sessions:
            session_names = [s["name"] for s in st.session_state.previous_sessions]
            current_session_name = st.session_state.session["name"]
            
            # Add current session to list if not already there, for selection
            if current_session_name not in session_names:
                session_names.append(current_session_name)

            try:
                # Find the index of the current session to set as default in selectbox
                default_index = session_names.index(current_session_name)
            except ValueError:
                default_index = 0

            chosen_name = st.selectbox("Previous Chats", options=session_names, index=default_index)

            # Logic to switch session if a different one is chosen
            if chosen_name != current_session_name:
                # Find the full session object from the list of previous sessions
                chosen_session = next((s for s in st.session_state.previous_sessions if s["name"] == chosen_name), st.session_state.session)
                st.session_state.session = chosen_session
                st.rerun()
        
        st.info(f"Current: **{st.session_state.session['name']}**")

    # --- Main Chat UI ---
    st.title("Product Search")
    
    # Ensure chat memory exists for the current session
    session_id = st.session_state.session["id"]
    if session_id not in st.session_state.chat_memory:
        st.session_state.chat_memory[session_id] = []

    # Display past chat messages from memory
    for message in st.session_state.chat_memory[session_id]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Show sample queries if new session
    if len(st.session_state.chat_memory[session_id]) == 0:
        st.markdown("""
        <div class="sample-queries-bubble">
        <strong>Here are some sample queries to get started:</strong><br><br>
        • Are there emergency lights available in stock?<br>
        • What is the price of IC sensors and how many units are available?
        </div>
        """, unsafe_allow_html=True)

    # Chat input field at the bottom of the page
    if prompt := st.chat_input("What would you like to ask?"):
        # Add user message to session memory
        st.session_state.chat_memory[session_id].append({"role": "user", "content": prompt})
        
        # Display user message in the chat
        with st.chat_message("user"):
            st.markdown(prompt)

        # Call the agent and get the response
        with st.chat_message("assistant"):
            with st.spinner("Searching for products..."):
                response_text, _ = call_bedrock_agent(prompt, session_id)
                # Replace escaped \n with actual line breaks in HTML
                formatted_response = response_text.replace('\\n', '<br>')
                st.markdown(formatted_response, unsafe_allow_html=True)
        
        # Add assistant response to session memory
        st.session_state.chat_memory[session_id].append({"role": "assistant", "content": response_text})
        
        # Rerun to hide sample queries and refresh the chat display
        st.rerun()

if __name__ == "__main__":
    main()


