import streamlit as st
from openai import OpenAI
import json
import os
import urllib.parse
import uuid
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from supabase import create_client, Client
from streamlit_cookies_manager import EncryptedCookieManager

# --- 1. SETUP SECRETS, AI, & CLIENTS ---
try:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    COOKIE_SECRET = st.secrets.get("COOKIE_SECRET", "default_secret_123")
except Exception:
    st.error("⚠️ Missing secrets! Please check your .streamlit/secrets.toml file.")
    st.stop()

# Initialize Clients
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)
GROQ_MODELS = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize Cookie Manager
cookies = EncryptedCookieManager(prefix="kenyan_prep_", password=COOKIE_SECRET)
if not cookies.ready():
    st.stop()

# --- 2. PAGE CONFIG & PREMIUM UI ---
st.set_page_config(page_title="Kenyan Meal Prep Planner", page_icon="🥘", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;800&family=Outfit:wght@300;400;600&display=swap');
    
    /* Global Background */
    .stApp { background: radial-gradient(circle at top center, #0d1f15 0%, #050505 100%) !important; color: #ffffff; font-family: 'Outfit', sans-serif !important; }
    
    /* Typography */
    h1, h2, h3 { font-family: 'Syne', sans-serif !important; }
    h1 { color: #ffffff !important; text-align: center; font-weight: 800; text-transform: uppercase; letter-spacing: -1px; text-shadow: 0 0 20px rgba(163, 230, 53, 0.3); }
    p { font-weight: 300; color: #b3b3b3; }
    .neon-text { color: #a3e635; font-weight: 600; }
    
    /* Cards */
    .meal-card, .workout-card {
        background: rgba(20, 30, 25, 0.4); backdrop-filter: blur(12px);
        border: 1px solid rgba(163, 230, 53, 0.15); border-radius: 24px;
        padding: 0; margin-bottom: 20px; overflow: hidden; transition: all 0.4s ease; box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        display: flex; flex-direction: column; height: 100%;
    }
    .workout-card { padding: 25px; }
    .workout-card:hover, .meal-card:hover {
        transform: translateY(-8px); border-color: rgba(163, 230, 53, 0.5); box-shadow: 0 15px 40px rgba(163, 230, 53, 0.15);
    }
    
    /* Icon Headers for Meals */
    .meal-icon-container {
        width: 100%; height: 160px; display: flex; justify-content: center; align-items: center;
        font-size: 5rem; background: linear-gradient(135deg, rgba(163, 230, 53, 0.1), rgba(10, 15, 12, 0.8));
        border-bottom: 2px solid rgba(163, 230, 53, 0.3); flex-shrink: 0;
        text-shadow: 0 0 20px rgba(163, 230, 53, 0.4);
    }
    
    .meal-content { 
        padding: 20px; text-align: center; flex-grow: 1; 
        display: flex; flex-direction: column; justify-content: center; 
    }
    .meal-content h4 { margin: 0; color: #a3e635; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 2px; }
    .meal-content h3 { margin: 8px 0; font-size: 1.3rem; color: #fff; font-family: 'Syne'; font-weight: 600; }
    .meal-content p { margin: 0 auto; color: #ffffff; font-size: 1.1rem; font-weight: 600; background: rgba(163, 230, 53, 0.1); display: inline-block; padding: 4px 12px; border-radius: 20px;}
    
    /* Workout Content */
    .workout-content h3 { margin: 0 0 15px 0; color: #a3e635; font-family: 'Syne'; font-size: 1.4rem; }
    .workout-content ul { margin: 0; padding-left: 0; list-style-type: none; }
    .workout-content li { margin-bottom: 12px; font-size: 1rem; color: #e5e5e5; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 8px; }
    .yt-link { color: #a3e635 !important; text-decoration: none; font-weight: 600; font-size: 0.8rem; padding: 4px 10px; border-radius: 8px; background: rgba(163, 230, 53, 0.1); border: 1px solid rgba(163, 230, 53, 0.3); transition: all 0.2s ease; cursor: pointer;}
    .yt-link:hover { background: rgba(163, 230, 53, 0.3); color: #fff !important; }
    
    /* Stats */
    .stat-box { background: linear-gradient(145deg, rgba(20, 35, 25, 0.8), rgba(10, 15, 12, 0.8)); border: 1px solid rgba(163, 230, 53, 0.15); border-radius: 20px; padding: 20px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5); position: relative; }
    .stat-box h4 { margin: 0; color: #a3a3a3; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 2px; font-weight: 600;}
    .stat-box h2 { margin: 10px 0 0 0; color: #a3e635; font-family: 'Syne'; font-weight: 800; font-size: 2.2rem; text-shadow: 0 0 15px rgba(163, 230, 53, 0.3); }
    .stat-box p { margin: 5px 0 0 0; font-size: 0.8rem; color: #666; }
    
    /* Buttons - Forced Black Text */
    .stButton>button, .stFormSubmitButton>button { background: #a3e635 !important; color: #000000 !important; border: none !important; border-radius: 30px !important; font-weight: 800 !important; font-family: 'Syne' !important; text-transform: uppercase !important; letter-spacing: 1px !important; transition: all 0.3s ease !important; box-shadow: 0 0 15px rgba(163, 230, 53, 0.2); }
    .stButton>button p, .stButton>button span, .stButton>button div, .stFormSubmitButton>button p, .stFormSubmitButton>button span, .stFormSubmitButton>button div { color: #000000 !important; font-weight: 800 !important; }
    .stButton>button:hover, .stFormSubmitButton>button:hover { transform: scale(1.02) !important; box-shadow: 0 0 25px rgba(163, 230, 53, 0.6) !important; background: #bcf24f !important; }
    
    /* Sidebar & Inputs */
    [data-testid="stSidebar"] { background-color: #050505 !important; border-right: 1px solid rgba(163, 230, 53, 0.1); }
    [data-testid="stSidebar"] h1 { text-align: left; font-size: 2rem; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input, .stSelectbox>div>div>div { background-color: #111a15 !important; color: #fff !important; border: 1px solid rgba(163, 230, 53, 0.2) !important; }
</style>
""", unsafe_allow_html=True)

# --- 3. PERSISTENCE (COOKIE + SUPABASE) ---
def get_user_id():
    user_id = cookies.get("uid")
    if user_id is None:
        user_id = str(uuid.uuid4())
        cookies["uid"] = user_id
        cookies.save()
    return user_id

USER_ID = get_user_id()

def load_state_from_db():
    try:
        response = supabase.table("user_data").select("data").eq("user_id", USER_ID).single().execute()
        if response.data:
            return response.data['data']
    except Exception:
        pass 
    return {}

def save_state_to_db(state_dict):
    try:
        supabase.table("user_data").upsert({
            "user_id": USER_ID,
            "data": state_dict
        }).execute()
    except Exception as e:
        st.error(f"Failed to save data to database: {e}")

# --- 4. SESSION STATE INITIALIZATION ---
default_state = {
    "meal_plan": None, "workout_plan": None, "grocery_list": None,
    "budget": 3500, "calories": 2000, "diet": "No restrictions",
    "goal": "Build Muscle", "activity": "Moderately Active (3-4 days/wk)",
    "workout_style": "Gym (Weights)", "workouts": [],
    "weight": 70, "height": 170, "age": 25, "gender": "Male"
}

if "app_initialized" not in st.session_state:
    saved_data = load_state_from_db()
    for key, default_value in default_state.items():
        st.session_state[key] = saved_data.get(key, default_value)
    st.session_state.app_initialized = True

def persist_current_state():
    state_to_save = {key: st.session_state[key] for key in default_state.keys()}
    save_state_to_db(state_to_save)

# --- 5. HELPER FUNCTIONS ---
def calculate_daily_calories(weight, height, age, gender, activity, goal):
    if gender == "Male": bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else: bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
    activity_multipliers = {"Sedentary (Office job)": 1.2, "Lightly Active (1-2 days/wk)": 1.375, "Moderately Active (3-4 days/wk)": 1.55, "Very Active (6-7 days/wk)": 1.725}
    tdee = bmr * activity_multipliers[activity]
    if goal == "Build Muscle": return int(tdee + 400)
    elif goal == "Lose Weight": return int(tdee - 500)
    else: return int(tdee)

def get_ai_json(prompt, temp=0.7):
    for model_name in GROQ_MODELS:
        try:
            response = client.chat.completions.create(
                model=model_name, messages=[{"role": "user", "content": prompt}],
                temperature=temp, response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception: continue 
    st.error("🚨 AI Error. Check connection.")
    return None

def generate_meal_plan():
    protein_instruction = "Prioritize high-protein foods (Eggs, Ndengu, Beans, Chicken, Beef, Fish)." if st.session_state.goal == "Build Muscle" else "Keep meals balanced."
    prompt = f"""
    You are a Kenyan nutritionist. Create a 7-day meal plan (Monday to Sunday).
    Target: {st.session_state.calories} calories/day. Weekly Budget: {st.session_state.budget} KES.
    Dietary restrictions: {st.session_state.diet}. User Goal: {st.session_state.goal}. {protein_instruction}
    
    CRITICAL PRICING RULE: Use realistic 2024 Kenyan prices. 
    - A basic meal (e.g., Ugali, Sukuma, Eggs) costs between 80 and 150 KES. 
    - A meal with Beef/Chicken costs between 200 and 350 KES.
    - Do NOT output unrealistic prices like 30 KES. Make the total weekly cost accurately reflect the weekly budget.
    
    Use affordable Kenyan ingredients (Ugali, Sukuma Wiki, Managu, Githeri, Chapati, Ndengu, Rice, eggs, local fruits).
    Return ONLY a JSON object with this exact structure:
    {{ "Monday": {{ "Breakfast": {{"name": "...", "cost_kes": 100}}, "Lunch": {{"name": "...", "cost_kes": 150}}, "Dinner": {{"name": "...", "cost_kes": 200}} }}, "Tuesday": {{ ... }}, "Wednesday": {{ ... }}, "Thursday": {{ ... }}, "Friday": {{ ... }}, "Saturday": {{ ... }}, "Sunday": {{ ... }} }}
    """
    return get_ai_json(prompt)

def generate_workout_plan():
    meal_context = "No meals generated yet."
    if st.session_state.meal_plan:
        meal_context = f"User is eating a {st.session_state.calories} kcal diet with Kenyan foods to {st.session_state.goal}."
    prompt = f"""
    You are an expert personal trainer. Create a weekly plan based on these details:
    Goal: {st.session_state.goal}. Activity Level: {st.session_state.activity}. Preferred Style: {st.session_state.workout_style}.
    Nutrition Context: {meal_context}.
    Provide a 4-day active split and 3 rest days. Include the focus and exactly 4 exercises/activities with duration/reps.
    Return ONLY a JSON object with this exact structure:
    {{ "Monday": {{ "focus": "Push Day (Chest/Shoulders)", "exercises": ["Bench Press - 3x8-10", "Overhead Press - 3x10", "Tricep Pushdowns - 3x12", "Lateral Raises - 3x15"] }}, "Tuesday": {{ "focus": "Rest Day", "exercises": ["Light stretching"] }}, "Wednesday": {{ "focus": "Pull Day (Back/Biceps)", "exercises": ["Deadlift - 3x5", "Lat Pulldowns - 3x10", "Barbell Rows - 3x8", "Bicep Curls - 3x12"] }}, "Thursday": {{ "focus": "Rest Day", "exercises": ["Recovery"] }}, "Friday": {{ "focus": "Leg Day", "exercises": ["Squats - 4x8", "Leg Press - 3x10", "Romanian Deadlifts - 3x8", "Calf Raises - 4x15"] }}, "Saturday": {{ "focus": "Cardio / Core", "exercises": ["30 min Run", "Plank - 3x1min", "Russian Twists - 3x20", "Leg Raises - 3x15"] }}, "Sunday": {{ "focus": "Rest Day", "exercises": ["Recovery"] }} }}
    """
    return get_ai_json(prompt)

def swap_single_meal(day, meal_type, current_meal):
    prompt = f"""
    You are a Kenyan nutritionist. Replace {meal_type} on {day} which was currently "{current_meal}".
    Dietary restrictions: {st.session_state.diet}. Goal: {st.session_state.goal}.
    IMPORTANT: Use realistic Kenyan prices (80-250 KES).
    Return ONLY JSON: {{"name": "New Meal Name", "cost_kes": 150}}
    """
    return get_ai_json(prompt, temp=0.8)

def generate_grocery_list():
    plan_summary = [f"{details['name']}" for day, meals in st.session_state.meal_plan.items() for meal_type, details in meals.items()]
    prompt = f"""
    Here are the meals for the week: {', '.join(plan_summary)}
    Create a grocery list by extracting the RAW INGREDIENTS needed to cook these meals. 
    (e.g., for "Ugali", list "Maize Flour". Do NOT list "Ugali").
    Deduplicate the ingredients. Group them into exactly these 4 categories: "Produce", "Proteins & Meat", "Pantry Staples", "Spices & Oils".
    Return ONLY a valid JSON object with these 4 keys.
    """
    return get_ai_json(prompt, temp=0.2)

def get_meal_icon(meal_type):
    if meal_type.lower() == "breakfast": return "🌅"
    if meal_type.lower() == "lunch": return "☀️"
    if meal_type.lower() == "dinner": return "🌙"
    return "🍽️"

def get_ordered_days(plan_dict):
    standard_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    if not plan_dict: return []
    ordered = [day for day in standard_days if day in plan_dict]
    ordered += [day for day in plan_dict.keys() if day not in standard_days]
    return ordered

def create_grocery_pdf(grocery_dict):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    
    c.setFont("Helvetica-Bold", 22)
    c.drawString(50, height - 60, "Kenyan Meal Prep - Grocery List")
    
    y = height - 100
    c.setFont("Helvetica", 12)
    
    for category, items in grocery_dict.items():
        if y < 100:
            c.showPage()
            y = height - 60
            c.setFont("Helvetica", 12)
            
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, y, category.upper())
        y -= 25
        
        c.setFont("Helvetica", 12)
        for item in items:
            if y < 50:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 12)
            c.drawString(60, y, f"[  ]  {item}")
            y -= 20
        y -= 15 

    c.save()
    buffer.seek(0)
    return buffer

# --- 6. SIDEBAR NAVIGATION ---
st.sidebar.markdown("<h1 style='color: #fff; font-family: Syne; font-size: 2rem; margin-bottom: 0;'>KENYAN<span class='neon-text'>MEAL PREP</span></h1>", unsafe_allow_html=True)
st.sidebar.markdown("<p style='color: #666; font-size: 0.8rem; letter-spacing: 2px; margin-bottom: 30px;'>PLANNER</p>", unsafe_allow_html=True)

page = st.sidebar.radio("Navigation", ["⚙️ Profile & Goals", "🥘 Nutrition Plan", "🏋️ AI Trainer & Tracker"])

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Your Stats")
st.sidebar.markdown(f"**Goal:** <span class='neon-text'>{st.session_state.goal}</span>", unsafe_allow_html=True)
st.sidebar.markdown(f"**Target:** {st.session_state.calories} kcal/day")
burned = sum(w['cals'] for w in st.session_state.workouts)
st.sidebar.markdown(f"**Burned:** <span class='neon-text'>{burned}</span> kcal", unsafe_allow_html=True)

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Start Over (Clear All)"):
    for key in default_state.keys():
        st.session_state[key] = default_state[key]
    persist_current_state()
    st.rerun()

# --- 7. PAGE 1: PROFILE & PREFERENCES ---
if page == "⚙️ Profile & Goals":
    st.title("⚙️ Profile & Goals")
    st.markdown("<p style='text-align: center;'>Set your metrics. The AI will calculate your calories and tailor your workouts.</p>", unsafe_allow_html=True)

    with st.expander("🧬 Body Metrics & Calorie Calculator", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            weight = st.number_input("Weight (kg)", 40, 150, value=st.session_state.weight)
            st.session_state.weight = weight
            height = st.number_input("Height (cm)", 130, 220, value=st.session_state.height)
            st.session_state.height = height
        with c2:
            age = st.number_input("Age", 15, 90, value=st.session_state.age)
            st.session_state.age = age
            gender = st.selectbox("Gender", ["Male", "Female"], index=0 if st.session_state.gender=="Male" else 1)
            st.session_state.gender = gender
        with c3:
            activity_options = ["Sedentary (Office job)", "Lightly Active (1-2 days/wk)", "Moderately Active (3-4 days/wk)", "Very Active (6-7 days/wk)"]
            activity = st.selectbox("Activity Level", activity_options, index=activity_options.index(st.session_state.activity) if st.session_state.activity in activity_options else 2)
            
            goal_options = ["Maintain Weight", "Build Muscle", "Lose Weight"]
            goal = st.selectbox("Primary Goal", goal_options, index=goal_options.index(st.session_state.goal) if st.session_state.goal in goal_options else 1)

        if st.button("Calculate Daily Target", use_container_width=True):
            calculated_cals = calculate_daily_calories(weight, height, age, gender, activity, goal)
            st.session_state.calories = calculated_cals
            st.session_state.goal = goal
            st.session_state.activity = activity
            
            st.session_state.meal_plan = None
            st.session_state.workout_plan = None
            st.session_state.grocery_list = None
            
            persist_current_state()
            st.success(f"✅ Target updated to **{calculated_cals} Calories/day**. Old plans cleared so you can generate new ones!")

    with st.form("settings"):
        st.markdown("### 🎯 Targets")
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.calories = st.slider("Daily Calorie Goal", 1500, 4000, st.session_state.calories, 50)
        with col2:
            st.session_state.budget = st.number_input("Weekly Food Budget (KES)", 1000, 20000, st.session_state.budget, 500)
        
        st.markdown("### 🏋️ Workout Style")
        style_options = ["Gym (Weights)", "Home Workout (Bodyweight)", "Sports/Running", "Mixed"]
        st.session_state.workout_style = st.selectbox("How do you want to exercise?", style_options, index=style_options.index(st.session_state.workout_style) if st.session_state.workout_style in style_options else 0)
        
        diet_options = ["No restrictions", "Vegetarian", "No Beef", "No Dairy", "Low Carb"]
        st.session_state.diet = st.selectbox("Dietary Restrictions", diet_options, index=diet_options.index(st.session_state.diet) if st.session_state.diet in diet_options else 0)
        
        if st.form_submit_button("Save Preferences", use_container_width=True):
            st.session_state.meal_plan = None
            st.session_state.workout_plan = None
            st.session_state.grocery_list = None
            
            persist_current_state()
            st.success("Preferences saved! Old plans cleared. Please generate a new meal & workout plan.")

# --- 8. PAGE 2: MEAL PLAN ---
elif page == "🥘 Nutrition Plan":
    st.title("🥘 Kenyan Nutrition")
    
    if not st.session_state.meal_plan:
        st.info("You haven't generated a meal plan yet (or you recently changed your profile).")
        if st.button("Generate 7-Day Meal Plan", use_container_width=True):
            with st.spinner("Crafting your meals with realistic Kenyan prices..."):
                plan = generate_meal_plan()
                if plan:
                    st.session_state.meal_plan = plan
                    st.session_state.grocery_list = None
                    persist_current_state()
                    st.rerun()
    else:
        total_cost = sum(meal['cost_kes'] for day in st.session_state.meal_plan.values() for meal in day.values())
        remaining = st.session_state.budget - total_cost
        
        col_a, col_b, col_c = st.columns(3)
        col_a.markdown(f"<div class='stat-box'><h4>Budget</h4><h2>{st.session_state.budget}</h2><p>KES</p></div>", unsafe_allow_html=True)
        color = "#a3e635" if total_cost <= st.session_state.budget else "#ef4444"
        col_b.markdown(f"<div class='stat-box'><h4>Plan Cost</h4><h2 style='color: {color};'>{total_cost}</h2><p>KES</p></div>", unsafe_allow_html=True)
        status = "Left" if remaining >= 0 else "Over"
        col_c.markdown(f"<div class='stat-box'><h4>{status}</h4><h2 style='color: {color};'>{abs(remaining)}</h2><p>KES</p></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🍽️ Weekly Meals")
        
        days = get_ordered_days(st.session_state.meal_plan)
        tabs = st.tabs(days)
        
        for i, day in enumerate(days):
            with tabs[i]:
                col_b, col_l, col_d = st.columns(3)
                def render_meal(col, meal_type, meal_data):
                    with col:
                        icon = get_meal_icon(meal_type)
                        
                        st.markdown(f'''
                        <div class="meal-card">
                            <div class="meal-icon-container">{icon}</div>
                            <div class="meal-content">
                                <h4>{meal_type}</h4>
                                <h3>{meal_data["name"]}</h3>
                                <p>{meal_data["cost_kes"]} KES</p>
                            </div>
                        </div>
                        ''', unsafe_allow_html=True)
                        
                        if st.button(f"🔄 Swap", key=f"swap_{day}_{meal_type}", use_container_width=True):
                            with st.spinner("Swapping..."):
                                new_meal = swap_single_meal(day, meal_type, meal_data['name'])
                                if new_meal:
                                    st.session_state.meal_plan[day][meal_type] = new_meal
                                    persist_current_state()
                                    st.rerun()
                                    
                render_meal(col_b, "Breakfast", st.session_state.meal_plan[day]['Breakfast'])
                render_meal(col_l, "Lunch", st.session_state.meal_plan[day]['Lunch'])
                render_meal(col_d, "Dinner", st.session_state.meal_plan[day]['Dinner'])

        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### 🛒 Grocery List")
        if not st.session_state.grocery_list:
            if st.button("Generate Grocery List", use_container_width=True):
                with st.spinner("Extracting ingredients..."):
                    glist = generate_grocery_list()
                    if glist:
                        st.session_state.grocery_list = glist
                        persist_current_state()
                        st.rerun()
        else:
            col1, col2 = st.columns(2)
            categories = list(st.session_state.grocery_list.keys())
            with col1:
                for cat in categories[:2]:
                    st.markdown(f"#### <span class='neon-text'>{cat}</span>", unsafe_allow_html=True)
                    for item in st.session_state.grocery_list[cat]: st.checkbox(item, key=f"chk_{cat}_{item}")
            with col2:
                for cat in categories[2:]:
                    st.markdown(f"#### <span class='neon-text'>{cat}</span>", unsafe_allow_html=True)
                    for item in st.session_state.grocery_list[cat]: st.checkbox(item, key=f"chk_{cat}_{item}")
            
            grocery_text = "GROCERY LIST\n\n" + "\n".join([f"--- {cat.upper()} ---\n" + "\n".join([f"[ ] {i}" for i in items]) for cat, items in st.session_state.grocery_list.items()])
            pdf_buffer = create_grocery_pdf(st.session_state.grocery_list)
            
            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button("📥 Download as Text (.txt)", data=grocery_text, file_name="grocery_list.txt", use_container_width=True)
            with col_dl2:
                st.download_button("📄 Download as PDF", data=pdf_buffer, file_name="kenyan_grocery_list.pdf", mime="application/pdf", use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Generate New Meal Plan (Overwrite Current)", use_container_width=True):
            st.session_state.meal_plan = None
            st.session_state.grocery_list = None
            persist_current_state()
            st.rerun()

# --- 9. PAGE 3: AI TRAINER & TRACKER ---
elif page == "🏋️ AI Trainer & Tracker":
    st.title("🏋️ AI Personal Trainer")
    
    if not st.session_state.workout_plan:
        st.info("Generate a plan based on your goals and current nutrition.")
        if st.button("Generate Weekly Workout Plan", use_container_width=True):
            with st.spinner("Analyzing your diet and building a split..."):
                w_plan = generate_workout_plan()
                if w_plan:
                    st.session_state.workout_plan = w_plan
                    persist_current_state()
                    st.rerun()
    else:
        st.markdown("### 📅 Your Weekly Split")
        
        days = get_ordered_days(st.session_state.workout_plan)
        tabs = st.tabs(days)
        
        for i, day in enumerate(days):
            with tabs[i]:
                day_data = st.session_state.workout_plan[day]
                
                exercises_html = ""
                for ex in day_data['exercises']:
                    search_query = urllib.parse.quote(f"How to do {ex}")
                    web_link = f"https://www.youtube.com/results?search_query={search_query}"
                    
                    link_html = f'<a href="{web_link}" target="_blank" rel="noopener noreferrer" class="yt-link">▶ TUTORIAL</a>'
                    exercises_html += f'<li><span>{ex}</span> {link_html}</li>'
                
                st.markdown(f'<div class="workout-card"><div class="workout-content"><h3>{day_data["focus"]}</h3><ul>{exercises_html}</ul></div></div>', unsafe_allow_html=True)
                
                if day_data['focus'] != "Rest Day":
                    if st.button(f"✅ Mark {day} as Completed", key=f"log_{day}", use_container_width=True):
                        est_cals = 400 if st.session_state.goal == "Build Muscle" else 300
                        st.session_state.workouts.append({
                            "name": f"{day_data['focus']} ({day})",
                            "duration": 60,
                            "cals": est_cals
                        })
                        persist_current_state()
                        st.success(f"Logged! {est_cals} Kcal burned added to tracker.")
        
        if st.button("🔄 Regenerate Workout Plan", use_container_width=True):
            st.session_state.workout_plan = None
            persist_current_state()
            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("### 🔥 Tracker & Net Calories")
    
    total_burned = sum(w['cals'] for w in st.session_state.workouts)
    food_cals = st.session_state.calories
    
    f1, f2, f3 = st.columns(3)
    f1.markdown(f"<div class='stat-box'><h4>Food Target</h4><h2>{food_cals}</h2><p>KCAL / DAY</p></div>", unsafe_allow_html=True)
    f2.markdown(f"<div class='stat-box'><h4>Burned</h4><h2 style='color: #fff;'>{total_burned}</h2><p>KCAL / WEEK</p></div>", unsafe_allow_html=True)
    net_cals = food_cals + total_burned 
    f3.markdown(f"<div class='stat-box'><h4>Net Intake</h4><h2>{net_cals}</h2><p>KCAL</p></div>", unsafe_allow_html=True)

    with st.expander("➕ Log a Custom Workout Manually"):
        with st.form("workout_form", clear_on_submit=True):
            w1, w2, w3 = st.columns(3)
            with w1: ex_name = st.text_input("Exercise Name", "Running")
            with w2: ex_duration = st.number_input("Duration (mins)", 10, 180, 30)
            with w3: ex_cals = st.number_input("Calories Burned", 20, 2000, 200)
            if st.form_submit_button("Add to Tracker", use_container_width=True):
                st.session_state.workouts.append({"name": ex_name, "duration": ex_duration, "cals": ex_cals})
                persist_current_state()
                st.rerun()

    if st.session_state.workouts:
        st.markdown("#### ✅ Logged Workouts")
        for i, w in enumerate(st.session_state.workouts):
            col_ex, col_del = st.columns([5, 1])
            col_ex.markdown(f"**{w['name']}** - {w['duration']} mins (<span class='neon-text'>{w['cals']} Kcal</span>)", unsafe_allow_html=True)
            if col_del.button("❌", key=f"del_{i}"):
                st.session_state.workouts.pop(i)
                persist_current_state()
                st.rerun()
    else:
        st.info("No workouts logged yet. Generate a plan above or add one manually!")