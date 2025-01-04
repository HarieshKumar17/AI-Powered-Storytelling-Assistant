import streamlit as st
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import io
from docx import Document
from reportlab.pdfgen import canvas
import random
import json

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Database configuration
DB_NAME = "storytelling_assistant.db"

# Create db directory if it doesn't exist
if not os.path.exists('db'):
    os.makedirs('db')

# Initialize Groq client
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# Database functions
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            profession TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    # Check if the 'parameters' column exists in the stories table
    cursor.execute("PRAGMA table_info(stories)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'parameters' not in columns:
        # Add the 'parameters' column to the stories table
        cursor.execute('''
            ALTER TABLE stories
            ADD COLUMN parameters TEXT
        ''')
    else:
        # If the table doesn't exist, create it with all columns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                parameters TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS professionals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            bio TEXT NOT NULL,
            experience INTEGER NOT NULL,
            rating FLOAT NOT NULL,
            price FLOAT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            professional_id INTEGER NOT NULL,
            slot TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (professional_id) REFERENCES professionals (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_professionals():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT * FROM professionals')
        professionals = cursor.fetchall()
        
        print("Debug - Raw professionals data:", professionals)  # Add this line
    
        conn.close()

        # Get column names
        column_names = [description[0] for description in cursor.description]
        
        result = []
        for pro in professionals:
            pro_dict = {}
            for i, col in enumerate(column_names):
                if i < len(pro):
                    pro_dict[col] = pro[i]
                else:
                    pro_dict[col] = None  # Set to None if the column doesn't exist
            result.append(pro_dict)
        
        return result
    except sqlite3.Error as e:
        logging.error(f"Database error in get_professionals: {str(e)}")
        return []
    finally:
        conn.close()

def add_booking(user_id, professional_id, slot):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO bookings (user_id, professional_id, slot)
            VALUES (?, ?, ?)
        ''', (user_id, professional_id, slot))
        conn.commit()
        booking_id = cursor.lastrowid
        logging.info(f"Booking added successfully. ID: {booking_id}")
        return booking_id
    except sqlite3.Error as e:
        logging.error(f"Database error while adding booking: {str(e)}")
        conn.rollback()
        raise Exception(f"Error adding booking: {str(e)}")
    finally:
        conn.close()

def add_user(user_data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    hashed_password = generate_password_hash(user_data['password'])
    
    try:
        cursor.execute('''
            INSERT INTO users (first_name, last_name, email, profession, username, phone, password)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_data['first_name'], user_data['last_name'], user_data['email'], user_data['profession'],
              user_data['username'], user_data['phone'], hashed_password))
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError as e:
        logging.error(f"Database integrity error: {str(e)}")
        raise Exception("Username or email already exists")
    finally:
        conn.close()
    
    return user_id

def get_user(username, password):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    
    conn.close()
    
    if user and check_password_hash(user[7], password):
        return {
            'id': user[0],
            'first_name': user[1],
            'last_name': user[2],
            'email': user[3],
            'profession': user[4],
            'username': user[5],
            'phone': user[6]
        }
    return None

def save_story(user_id, title, content, parameters):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO stories (user_id, title, content, parameters)
            VALUES (?, ?, ?, ?)
        ''', (user_id, title, content, parameters))
        conn.commit()
        story_id = cursor.lastrowid
        logging.info(f"Story saved successfully. ID: {story_id}")
        return story_id
    except sqlite3.Error as e:
        logging.error(f"Database error while saving story: {str(e)}")
        conn.rollback()
        raise Exception(f"Error saving story: {str(e)}")
    finally:
        conn.close()

def delete_story(story_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM stories WHERE id = ?', (story_id,))
        conn.commit()
        logging.info(f"Story deleted successfully. ID: {story_id}")
    except sqlite3.Error as e:
        logging.error(f"Database error while deleting story: {str(e)}")
        conn.rollback()
        raise Exception(f"Error deleting story: {str(e)}")
    finally:
        conn.close()

def get_stories(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, title, content, parameters, created_at FROM stories WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    stories = cursor.fetchall()
    
    conn.close()
    
    return [
        {
            'id': story[0],
            'title': story[1],
            'content': story[2],
            'parameters': story[3],
            'created_at': story[4]
        } for story in stories
    ]

def get_well_known_tales():
    try:
        df = pd.read_excel('db/well_known_tales.xlsx')
        return df[['Story Title', 'Story Text']].to_dict('records')
    except FileNotFoundError:
        logging.error("well_known_tales.xlsx not found in the 'db' directory")
        return []
    except Exception as e:
        logging.error(f"Error reading well-known tales: {str(e)}")
        return []

def generate_story(data, selected_tale_text=None):
    prompt = f"Generate a {data['length']} story with the following parameters:\n"
    prompt += f"Story Origin: {data['story_origin']}\n"
    prompt += f"Use Case: {data['use_case']}\n"
    prompt += f"Time Frame: {data['time_frame']}\n"
    if data['age']:
        prompt += f"Age: {data['age']}\n"
    prompt += f"Focus: {', '.join(data['focus'])}\n"
    prompt += f"Story Type: {data['story_type']}\n"
    prompt += f"Narrative Structure: {data['narrative_structure']}\n"
    prompt += f"Simplified Structure: {data['simplified_structure']}\n"
    prompt += f"Creative Enhancements: {', '.join(data['creative_enhancements'])}\n"
    
    if selected_tale_text:
        prompt += f"Based on the following well-known tale, create a similar story:\n{selected_tale_text}\n"
    
    if data['user_story_start']:
        prompt += f"Start with the following user-provided story beginning:\n{data['user_story_start']}\n"
    
    try:
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an AI storytelling assistant."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-70b-versatile",
        )
        story = response.choices[0].message.content
        return story
    except Exception as e:
        logging.error(f"Story generation error: {str(e)}")
        raise Exception("Error generating story")

def create_download_file(content, format):
    if format == 'txt':
        return content.encode()
    elif format == 'docx':
        doc = Document()
        doc.add_paragraph(content)
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)
        return file_stream
    elif format == 'pdf':
        file_stream = io.BytesIO()
        p = canvas.Canvas(file_stream)
        p.drawString(100, 750, content)
        p.showPage()
        p.save()
        file_stream.seek(0)
        return file_stream

def main():
    st.set_page_config(page_title="AI-Powered Storytelling Assistant", layout="wide")

    st.title("AI-Powered Storytelling Assistant")
    st.write("Craft compelling stories with the help of AI")

    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    
    if 'page' not in st.session_state:
        st.session_state.page = 'main'

    if st.session_state.user_id is None:
        show_login_signup()
    else:
        show_sidebar()
        if st.session_state.page == 'main':
            show_main_page()
        elif st.session_state.page == 'professionals':
            show_professionals_page()
        elif st.session_state.page == 'about':
            show_about_page()

def show_about_page():
    st.title("About AI-Powered Storytelling Assistant")
    
    st.write("""
    ## Project Overview
    This AI-powered storytelling assistant helps users craft compelling personal and professional stories using AI-based narrative structures and creative enhancements. The assistant guides users through various stages of story creation, allowing them to choose story origins, use cases, timeframes, focus areas, and narrative structures. The system offers an intuitive interface, customization options, professional storyteller booking, and the ability to save and retrieve stories.
    ## Key Features
    - **Story Origins**: Choose between personal anecdotes or well-known tales.
    - **Story Use Cases**: Select from various use cases like personal branding, company origin, product launch, and more.
    - **Time Frame and Focus**: Specify the period of life and focus on specific leadership behaviors or qualities.
    - **Customizable Length**: Options for short, medium, or long stories.
    - **Diverse Story Types**: Choose from founding stories, vision stories, personal stories, and more.
    - **Narrative Structures**: Use different storytelling frameworks like Story-Spine, Hero's Journey, or In Media Res.
    - **Creative Enhancements**: AI-powered suggestions for metaphors, quotes, and comparisons.
    - **Story Management**: Save, retrieve, and edit your stories.
    - **Professional Storyteller Booking**: Book live sessions with experienced storytellers.
    ## How It Works
    1. **Log in** or create an account.
    2. Choose your **story parameters** on the main page.
    3. Generate your story using AI assistance.
    4. Edit and refine your story as needed.
    5. Save or download your completed story.
    6. Optionally, book a session with a professional storyteller for further enhancement.
    This storytelling assistant simplifies the process of crafting stories with AI-driven guidance, creative options, and professional enhancement tools. It's ideal for both personal and professional storytelling needs.
    """)

    if st.button("Back to Main Menu"):
        st.session_state.page = 'main'
        st.rerun()

def show_sidebar():
    with st.sidebar:
        st.title("Menu")
        if st.button("Main Page", key="sidebar_main"):
            st.session_state.page = 'main'
            st.rerun()
        if st.button("Book a Professional", key="sidebar_book"):
            st.session_state.page = 'professionals'
            st.rerun()
        if st.button("About", key="sidebar_about"):
            st.session_state.page = 'about'
            st.rerun()
        
        st.title("Saved Stories")
        saved_stories = get_stories(st.session_state.user_id)
        for i, story in enumerate(saved_stories):
            col1, col2= st.columns([3, 1])
            with col1:
                if st.button(story['title'], key=f"story_{i}"):
                    st.session_state.current_story = story['content']
                    st.session_state.current_story_id = story['id']
                    st.session_state.current_story_title = story['title']
            with col2:
                if st.button("🗑️", key=f"delete_{i}", help="Delete story"):
                    delete_story(story['id'])
                    st.rerun()
        
        st.title("User Actions")
        if st.button("Logout", key="sidebar_logout"):
            st.session_state.user_id = None
            st.rerun()

def show_login_signup():
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.header("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            user = get_user(username, password)
            if user:
                st.session_state.user_id = user['id']
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        st.header("Sign Up")
        first_name = st.text_input("First Name")
        last_name = st.text_input("Last Name")
        email = st.text_input("Email")
        profession = st.selectbox("Profession", ["Student", "Professional", "Other"])
        username = st.text_input("Username", key="signup_username")
        phone = st.text_input("Phone Number")
        password = st.text_input("Password", type="password", key="signup_password")
        if st.button("Create Account"):
            try:
                user_id = add_user({
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "profession": profession,
                    "username": username,
                    "phone": phone,
                    "password": password
                })
                st.success("Account created successfully! Please log in.")
            except Exception as e:
                st.error(str(e))

def show_main_page():
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("Story Generator")
        
        story_origin = st.radio("Story Origin", ["Personal Anecdote", "Well-known Tale"], key="main_story_origin")
        
        selected_tale_text = None
        user_story_start = None
        
        if story_origin == "Well-known Tale":
            tale_data = get_well_known_tales()
            tale_titles = [tale['Story Title'] for tale in tale_data]
            selected_tale = st.selectbox("Select a Well-known Tale", tale_titles, key="main_selected_tale")
            selected_tale_text = next((tale['Story Text'] for tale in tale_data if tale['Story Title'] == selected_tale), None)
            if selected_tale_text:
                st.text_area("Selected Tale", value=selected_tale_text, height=200, key="selected_tale_text", disabled=True)
        else:  # Personal Anecdote
            user_story_start = st.text_area("Start your own story (optional):", height=100, key="main_user_story_start")
        
        use_case = st.selectbox("Story Use Case", ["Personal Branding", "Company Origin", "Product Launch", "Customer Success", "Team Building"], key="main_use_case")
        time_frame = st.selectbox("Story Time Frame", ["Childhood", "Mid-career", "Recent Experience", "Custom Age"], key="main_time_frame")
        age = None
        if time_frame == "Custom Age":
            age = st.number_input("Enter Age", min_value=1, max_value=120, key="main_age")
        
        focus = st.multiselect("Story Focus (Select up to 5)", [
            "Generosity", "Integrity", "Loyalty", "Devotion", "Kindness", "Sincerity", "Self-control",
            "Confidence", "Persuasiveness", "Ambition", "Resourcefulness", "Decisiveness", "Faithfulness",
            "Patience", "Determination", "Persistence", "Fairness", "Cooperation", "Optimism", "Proactive",
            "Charisma", "Ethics", "Relentlessness", "Authority", "Enthusiasm", "Boldness"
        ], max_selections=5, key="main_focus")

    with col2:
        length = st.selectbox("Story Length", ["Short (250-500 words)", "Medium (500-1000 words)", "Long (1000-1500 words)"], key="main_length")
        story_type = st.selectbox("Story Type", [
            "Where we came from: A founding Story",
            "Why we can't stay here: A case-for-change story",
            "Where we're going: A vision story",
            "How we're going to get there: A strategy story",
            "Why I lead the way I do: Leadership philosophy story",
            "Why you should want to work here: A rallying story",
            "Personal stories: Who you are, what you do, how you do it, and who you do it for",
            "What we believe: A story about values",
            "Who we serve: A customer story",
            "What we do for our customers: A sales story",
            "How we're different: A marketing story"
        ], key="main_story_type")
        
        narrative_structure = st.selectbox("Narrative Structure", [
            "Story-Spine (Default)",
            "The Story Hanger",
            "Hero's Journey",
            "Beginning to End",
            "In Media Res",
            "Nested Loops",
            "The Cliffhanger"
        ], key="main_narrative_structure")
        
        simplified_structure = st.selectbox("Simplified Narrative Structure", [
            "Overcoming the Monster",
            "Rags to Riches",
            "The Quest",
            "Voyage and Return",
            "Rebirth",
            "Comedy",
            "Tragedy"
        ], key="main_simplified_structure")
        
        creative_enhancements = st.multiselect("Creative Enhancements", [
            "Quotes",
            "Metaphors",
            "Comparisons",
            "Sensory Details",
            "Dialogue"
        ], key="main_creative_enhancements")

    params = {
        "story_origin": story_origin,
        "use_case": use_case,
        "time_frame": time_frame,
        "age": age,
        "focus": focus,
        "length": length,
        "story_type": story_type,
        "narrative_structure": narrative_structure,
        "simplified_structure": simplified_structure,
        "creative_enhancements": creative_enhancements,
        "user_story_start": user_story_start
    }

    if st.button("Generate Story", key="main_generate"):
        with st.spinner("Generating your story..."):
            try:
                generated_story = generate_story(params, selected_tale_text)
                if user_story_start:
                    st.session_state.current_story = user_story_start + "\n\n" + generated_story
                else:
                    st.session_state.current_story = generated_story
                st.session_state.current_story_title = f"Story_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                st.session_state.current_story_params = params  # Store the parameters
            except Exception as e:
                st.error(str(e))

    if 'current_story' in st.session_state:
        st.subheader("Generated Story")
        story = st.text_area("Edit your story here:", value=st.session_state.current_story, height=300, key="main_edit_story")
        
        download_format = st.selectbox("Download Format", ["txt", "docx", "pdf"], index=1, key="main_download_format")
        
        if st.button("Save Story", key="main_save"):
            try:
                save_story(st.session_state.user_id, st.session_state.current_story_title, story, json.dumps(st.session_state.current_story_params))
                st.success("Story saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(str(e))
        
        file_content = create_download_file(story, download_format)
        st.download_button(
            label=f"Download Story as {download_format.upper()}",
            data=file_content,
            file_name=f"story_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{download_format}",
            mime=f"application/{download_format}",
            key="main_download"
        )

def show_professionals_page():
    st.title("Professional Storytellers")
    
    professionals = get_professionals()
    
    if not professionals:
        # Add some dummy data if the table is empty
        dummy_data = [
            ("John Doe", "Expert storyteller with 10 years of experience in corporate narratives.", 10, 4.8, 150),
            ("Jane Smith", "Specializes in personal branding stories with a touch of humor.", 8, 4.7, 120),
            ("Mike Johnson", "Master of fantasy tales and creative writing workshops.", 15, 4.9, 200),
            ("Sarah Brown", "Focuses on inspirational stories for motivational speaking.", 12, 4.6, 180),
            ("David Lee", "Experienced in crafting compelling product launch stories.", 7, 4.5, 100),
        ]
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        for pro in dummy_data:
            cursor.execute('''
                INSERT INTO professionals (name, bio, experience, rating, price)
                VALUES (?, ?, ?, ?, ?)
            ''', pro)
        
        conn.commit()
        conn.close()
        
        professionals = get_professionals()
    
    for pro in professionals:
        st.write("---")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.subheader(pro.get('name', 'Unknown'))
            st.write(pro.get('bio', 'No bio available'))
        
        with col2:
            st.write(f"Experience: {pro.get('experience', 'Unknown')} years")
            st.write(f"Rating: {pro.get('rating', 'Unknown')}/5.0")
            st.write(f"Price: ${pro.get('price', 'Unknown')}/session")
        
        with col3:
            available_slots = [f"{random.randint(9, 17)}:00" for _ in range(3)]
            selected_slot = st.selectbox(f"Available slots for {pro.get('name', 'Unknown')}", available_slots, key=f"slot_{pro.get('id', 'unknown')}")
            if st.button("Book Session", key=f"book_{pro.get('id', 'unknown')}"):
                try:
                    booking_id = add_booking(st.session_state.user_id, pro.get('id'), selected_slot)
                    st.success(f"Booked a session with {pro.get('name', 'Unknown')} at {selected_slot}")
                except Exception as e:
                    st.error(str(e))
    
    if st.button("Back to Main Page"):
        st.session_state.page = 'main'
        st.rerun()

if __name__ == "__main__":
    init_db()
    main()
