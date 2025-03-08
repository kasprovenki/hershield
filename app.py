import streamlit as st
import pandas as pd
import folium
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut  # For handling geocoding errors
from twilio.rest import Client  # Twilio for SMS
from twilio.base.exceptions import TwilioRestException  # For handling Twilio errors
import openai
import os
from gtts import gTTS
from io import BytesIO
import base64
import matplotlib.pyplot as plt
from pandasai import SmartDataframe
from pandasai.llm.openai import OpenAI

# Load OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.error("❌ OpenAI API key is missing! Please set the OPENAI_API_KEY environment variable.")
    st.stop()

# Set page config
st.set_page_config(
    page_title="HerShield - Women Safety App",
    page_icon="🛡",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #2d2d2d 0%, #1a1a1a 100%);
    color: white;
}
</style>
""", unsafe_allow_html=True)

# Crime Data (Mock Data)
crime_data = pd.DataFrame({
    'lat': [28.6129, 28.6100, 28.6155],
    'lon': [77.2295, 77.2300, 77.2340],
    'safety_score': [3, 8, 5]
})

# Generate Safety Heatmap
def generate_heatmap():
    m = folium.Map(location=[28.6129, 77.2295], zoom_start=14)
    folium.plugins.HeatMap(data=crime_data[['lat', 'lon', 'safety_score']].values.tolist()).add_to(m)
    return m

def trigger_sos():
    st.success("🚨 SOS Alert Sent! Authorities notified with your location.")

# Function to share live location via SMS using Twilio
def share_live_location_sms(recipient_phone_number):
    # Twilio credentials (replace with your own)
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")

    try:
        # Get live location
        geolocator = Nominatim(user_agent="hershield", timeout=10)  # Increase timeout to 10 seconds
        location = geolocator.geocode("Delhi, India")
        
        if location:
            lat, lon = location.latitude, location.longitude
            # Google Maps link
            google_maps_link = f"https://www.google.com/maps?q={lat},{lon}"

            # Send SMS
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                body=f"🚨 Emergency! My live location: {google_maps_link}",
                from_=twilio_phone_number,
                to=recipient_phone_number
            )
            st.success(f"📍 Live location shared via SMS to {recipient_phone_number}.")
        else:
            st.error("❌ Unable to fetch live location. Please try again later.")
    except (GeocoderUnavailable, GeocoderTimedOut) as e:
        st.error("❌ Geocoding service is unavailable or timed out. Please check your internet connection or try again later.")
    except TwilioRestException as e:
        if e.code == 21614:  # Error code for unverified numbers
            st.error("❌ The recipient's phone number is unverified. Please verify the number in your Twilio account.")
        else:
            st.error(f"❌ Failed to send SMS. Error: {e.msg}")

# Function to generate safe route details using OpenAI
def generate_safe_route_details(start, end):
    # System prompt for OpenAI
    system_prompt = """
    You are an AI-powered safe route planner. Your task is to provide a safe route between two locations, including:
    - A safety score out of 10.
    - High-risk zones to avoid.
    - Well-lit areas along the route.
    - CCTV surveillance availability.

    Respond in the following format:
    🟢 Safest Path (Safety Score: X/10)
    - 🚫 Avoids [number] high-risk zones: [list of high-risk zones].
    - 💡 Well-lit areas: [list of well-lit areas].
    - 🎥 CCTV surveillance available: [list of areas with CCTV].

    Example:
    🟢 Safest Path (Safety Score: 9/10)
    - 🚫 Avoids 3 high-risk zones: XYZ Street, ABC Road, DEF Lane.
    - 💡 Well-lit areas: Main Road, Central Avenue.
    - 🎥 CCTV surveillance available: City Center, Bus Stand.
    """

    # User input for the route
    user_input = f"Plan the safest route from {start} to {end}."

    try:
        openai.api_key = OPENAI_API_KEY

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"⚠ Error: {str(e)}"

# Function to generate safety score and details using OpenAI
def generate_safety_score(location):
    # System prompt for OpenAI
    system_prompt = """
    You are an AI-powered safety assistant. Your task is to provide a safety score (out of 10) and additional safety details for a given location. Include:
    - A safety score out of 10.
    - Safety tips for the area.
    - Nearby safe zones or landmarks.

    Respond in the following format:
    ✅ Safety Score: X/10
    - 🛡 Safety Tips: [list of safety tips].
    - 🏙 Nearby Safe Zones: [list of nearby safe zones].

    Example:
    ✅ Safety Score: 8/10
    - 🛡 Safety Tips: Avoid walking alone at night, stay in well-lit areas, be aware of your surroundings.
    - 🏙 Nearby Safe Zones: Central Park, Police Station, Bus Stand.
    """

    # User input for the location
    user_input = f"Provide a safety score and safety details for {location}."

    try:
        openai.api_key = OPENAI_API_KEY

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"⚠ Error: {str(e)}"

# Function to generate responses using GPT-4
def get_gpt_response(user_input):
    system_prompt = """
    You are Sarah – Women Protection Bot, a compassionate and empowering AI assistant dedicated to protecting, supporting, and uplifting women in matters of safety, health, and legal rights.

    Your Focus Areas:

    Women’s Health (Menstrual health, pregnancy, mental health, sexual health, self-care).
    Women’s Safety (Workplace harassment, sexual harassment, self-defense, legal rights, helplines).
    Support & Helplines (Emergency contacts, counseling services, abuse reporting, trauma support).
    Empathetic & Emotionally Aware Responses:

    Recognize and acknowledge the user's emotions before providing guidance.
    Respond in a warm, empowering, and reassuring tone.
    Use encouraging and uplifting language to make the user feel strong and supported.
    If a user expresses distress, give them hope, courage, and motivation before offering resources.
    Remind them they are not alone and that they have the strength to overcome challenges.
    Handling Distress & Crisis Situations:
    If a user expresses hopelessness, fear, or distress (e.g., "I feel like giving up," "I’m going to die"):
    Do NOT respond passively or just redirect them to helplines.
    Instead, empower and uplift them:
    "You are a brave and strong woman. I know things may feel overwhelming right now, but you have incredible strength within you. Please don’t give up. There are people who care about you and want to help. You are not alone, and you deserve support and kindness."
    Offer affirmations of courage: "You have faced challenges before, and you can overcome this too. I believe in you."
    THEN gently encourage them to reach out for support: "Talking to a trusted friend, family member, or professional can really help. You are important, and your feelings matter."
    Guidelines for Responses:
    ✅ Use uplifting and empowering language, especially in difficult moments.
    ✅ Remind the user of their inner strength and resilience.
    ✅ Provide actionable support without making the user feel dismissed.
    ✅ If needed, gently encourage seeking trusted people or professional help, but in a compassionate way.

    Handling Off-Topic Queries:
    If a user asks something unrelated, redirect them gently:
    "I’m here to support you with women's health, safety, and legal rights. Let me know how I can help."
    If the query is completely irrelevant, respond:
    "I don't know, but I’m here to assist with women's safety, health, and legal rights. Let me know how I can support you."
    """

    try:
        openai.api_key = OPENAI_API_KEY

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ]
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"⚠ Error: {str(e)}"

# Function to generate audio from text using gTTS
def generate_audio_response(text, filename="response.mp3"):
    # Add a personalized audio introduction
    introduction = "I am Sarah, your companion in your safety journey. "
    full_text = introduction + text
    
    # Generate the audio
    tts = gTTS(full_text, lang='en')
    audio_file = BytesIO()
    tts.write_to_fp(audio_file)
    audio_file.seek(0)
    
    # Create a download link for the audio
    b64 = base64.b64encode(audio_file.read()).decode()
    audio_html = f'<audio controls autoplay><source src="data:audio/mpeg;base64,{b64}" type="audio/mpeg"></audio>'
    return audio_html

# Sidebar
with st.sidebar:
    st.title("🛡 HerShield Guide")
    
    with st.expander("🚀 Getting Started"):
        st.markdown("""
        - *Emergency SOS:* Use the red SOS button to instantly alert authorities
        - *Sarah AI:* Chat with our AI assistant for safety advice
        - *Safety Check:* Get real-time safety scores for any location
        """, unsafe_allow_html=True)

    with st.expander("🏠 Home Page Features"):
        st.markdown("""
        - *Safety Heatmap:* Visualize safe/unsafe zones
        - *Quick Actions:* One-click emergency services access
        - *Live Updates:* Real-time crime data integration
        """, unsafe_allow_html=True)

    with st.expander("🚨 Emergency SOS System"):
        st.markdown("""
        - *Instant Alerts:* SMS alerts to 3 contacts with GPS
        - *Location Sharing:* Auto-updates every 2 minutes
        - *Discreet Activation:* Shake phone or press power 3x
        """, unsafe_allow_html=True)

    with st.expander("💬 Sarah AI Assistant"):
        st.markdown("""
        - *24/7 Support:* Harassment, health, and legal advice
        - *Crisis Management:* Trauma-informed responses
        - *Voice Features:* Audio safety instructions
        """, unsafe_allow_html=True)

    with st.expander("🗺 Safe Route Planner"):
        st.markdown("""
        - *AI Navigation:* Crime data-optimized routes
        - *Safety Metrics:* CCTV and lighting information
        - *Travel Companion:* Virtual escort mode
        """, unsafe_allow_html=True)

    with st.expander("📊 ML-Based Analysis"):
        st.markdown("""
        - *Crime Prediction:* Risk area forecasting
        - *Data Insights:* Harassment pattern analysis
        - *Safety Audits:* Institutional safety reports
        """, unsafe_allow_html=True)

    st.title("💬 Your Voice Matters")
    rating = st.selectbox("Rate your experience", ("⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"))
    if st.button("Submit Feedback"):
        st.success("Thank you for making women safer!")
        st.markdown("""
        Need immediate help? Contact our partners:
        - [National Commission for Women](https://ncwapps.nic.in/)
        - [RAINN Helpline](https://www.rainn.org)
        """)
        
    st.header("Emergency Contacts")
    st.write("📞 Local Police: 100")
    st.write("📞 Women Helpline: 1091")
    st.write("📞 Medical Emergency: 108")
    
    
    

# Main App
st.title("🛡 HerShield - AI-Powered Women Safety")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Home", "🚨 SOS", "💬 Sarah AI", "📊 ML-Based Analysis", "🗺 Safe Route"])

with tab1:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.header("Real-time Safety Status")
        folium_static(generate_heatmap())
        
    with col2:
        st.header("Quick Actions")
        if st.button("🚨 Trigger Emergency SOS", on_click=trigger_sos):
            pass
            
        st.subheader("Safety Check-In")
        location = st.text_input("Enter your current location")
        if st.button("Check Safety"):
            with st.spinner("Analyzing safety..."):
                # Get safety score and details from OpenAI
                safety_details = generate_safety_score(location)
                
                # Display the safety details
                st.markdown(safety_details)

with tab2:
    st.header("Emergency SOS System")
    
    st.subheader("Live Location Sharing")
    # Ask user to input recipient's phone number
    st.write("The verified Phone numbers in Twilio are +919865826118,+919360593132")
    recipient_phone_number = st.text_input("Enter recipient's phone number (with country code, e.g., +919876543210)")
    if st.button("📍 Share Live Location via SMS"):
        if recipient_phone_number:
            share_live_location_sms(recipient_phone_number)
        else:
            st.error("Please enter a valid phone number.")


with tab3:
    st.title("🤖 Sarah – Women Protection Bot")
    st.write("Ask me about women's safety, harassment, mental health, or legal rights.")

    # Initialize chat history and response
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    response = ""  # Initialize response as an empty string to avoid NoneType issues

    # User input
    user_input = st.chat_input("Type your message here...")

    # Handle user input
    if user_input:
        # Append the user message and display it immediately
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Generate and display the assistant's response
        response = get_gpt_response(user_input) or ""  # Ensure response is not None
        st.session_state.messages.append({"role": "assistant", "content": response})

    # Display chat history in chronological order
    if st.session_state.messages:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Generate and play audio only for valid assistant messages
                if message["role"] == "assistant" and response and response != "I don't know":
                    audio_html = generate_audio_response(response)
                    st.markdown(audio_html, unsafe_allow_html=True)


with tab4:
    st.title("📊 ML-Based Analysis")
    st.markdown("""
    Gain insights into women's safety and health trends using data-driven analysis.
    
    Analytics Dashboard:
    - Safety Trends: Visualize data on harassment reports and safety queries.
    - Predictive Models: Anticipate health and safety needs.
    - Resource Utilization: Analyze how often resources are accessed.
    """)

    # File uploader
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("### Preview of Uploaded Dataset", df.head())

        # Drop unnecessary column if it exists
        if "Unnamed: 0" in df.columns:
            df = df.drop(columns=["Unnamed: 0"])

        # Initialize PandasAI with OpenAI
        llm = OpenAI(os.getenv("OPENAI_API_KEY"))
        sdf = SmartDataframe(df, config={"llm": llm})

        # User input for query
        user_query = st.text_input("Ask a question about the dataset:")

        if st.button("Analyze"):
            with st.spinner("Generating insights..."):
                try:
                    # Get AI-generated response
                    response = sdf.chat(user_query)
                    st.write("### AI Response:", response)

                    # Visualization generation
                    graph_prompt = f"Generate a visualization code using matplotlib or seaborn for: {user_query}"
                    graph_response = sdf.chat(graph_prompt)

                    # Check if the response is a valid file path to an image
                    image_path = graph_response.strip()
                    if os.path.isfile(image_path) and image_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                        st.image(image_path, caption="Generated Graph")
                    
                    else:
                        # Execute the AI-generated visualization code if it's actual code
                        st.write("### AI-Generated Visualization Code:")
                        st.code(graph_response, language="python")
                        
                        with st.container():
                            fig, ax = plt.subplots()
                            exec(graph_response, {'plt': plt, 'df': df, 'ax': ax})
                            st.pyplot(fig)

                except Exception as e:
                    st.error(f"Error executing AI-generated code: {e}")

with tab5:
    st.header("AI-Powered Safe Route Planner")
    start = st.text_input("Start Location", "Connaught Place, Delhi")
    end = st.text_input("Destination", "India Gate, Delhi")
    
    if st.button("Plan Safest Route"):
        with st.spinner("Generating the safest route..."):
            # Get safe route details from OpenAI
            route_details = generate_safe_route_details(start, end)
            
            # Display the route details
            st.subheader("Recommended Route")
            st.markdown(route_details)
            
            # Display a map (mock data for now)
            st.map(pd.DataFrame({'lat': [28.6329, 28.6200], 'lon': [77.2195, 77.2400]}))