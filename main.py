import streamlit as st

# Page setup
st.set_page_config(page_title="Digital Assistant", layout="wide")

# Custom CSS for mobile Safari styling
st.markdown(
    """
    <style>
    body {
        background-color: #0e1117; /* Dark background */
    }
    .app-header {
        text-align: center;
        font-size: 28px;  /* Smaller for mobile */
        font-weight: bold;
        color: #f5f5f5;
        margin-bottom: -10px;
    }
    .app-subheader {
        text-align: center;
        font-size: 18px;  /* Smaller for mobile */
        font-weight: 400;
        color: #d1d1d1;
        margin-bottom: 30px;
    }
    .stButton>button {
        background-color: #e6d5cc;
        color: black;
        border-radius: 14px;
        padding: 16px 20px;  /* Adjusted for mobile touch */
        font-size: 16px;     /* Smaller text for mobile */
        font-weight: 600;
        border: none;
        width: 280px;        /* Fixed width instead of 100% */
        display: block;      /* Changed from flex to block */
        margin: 10px auto;   /* Center the button horizontally */
        text-align: center;  /* Center the text */
        -webkit-appearance: none;  /* Remove Safari default styling */
        -webkit-tap-highlight-color: transparent;  /* Remove tap highlight */
    }
    .stButton>button:hover {
        background-color: #d1c0b7;
    }
    .stButton>button:active {
        background-color: #c4b3aa;  /* Mobile tap feedback */
        transform: scale(0.98);     /* Slight press effect */
    }
    
    /* Mobile-specific adjustments */
    @media (max-width: 768px) {
        .app-header {
            font-size: 24px;
        }
        .app-subheader {
            font-size: 16px;
        }
        .stButton>button {
            font-size: 14px;
            padding: 14px 18px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Header
st.markdown("<div class='app-header'>🤖 Digital Assistant</div>", unsafe_allow_html=True)
st.markdown("<div class='app-subheader'>HOME</div>", unsafe_allow_html=True)

# Center the buttons perfectly to align with "Digital Assistant" title
# Mic Button (Perfectly centered)
mic_btn = st.button("🎤  Record a Note")

# Add some spacing
st.markdown("<br>", unsafe_allow_html=True)

# Info Button (Perfectly centered)
info_btn = st.button("ℹ️  Chat with Notes")

# Actions
if mic_btn:
    st.success("Mic button clicked! (Recording feature will go here)")
if info_btn:
    st.info("Info button clicked! (Chatbot feature will go here)")