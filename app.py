import sys
import os
import pandas as pd
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    jsonify, session, send_file
)
# *** Import Session ***
from flask_session import Session
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine, text, exc
import secrets
import io
import uuid
from datetime import datetime, timedelta, date, timezone # For session expiration
import re
import numpy as np
import json
from collections import Counter # For counting dtypes
import math
import plotly.express as px
import plotly.io as pio
import plotly.figure_factory as ff
import webbrowser
import threading
import requests
from packaging import version
import signal
import subprocess
import logging


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- Environment and Supabase ---
from dotenv import load_dotenv
dotenv_path = resource_path('.env')
load_dotenv(dotenv_path=dotenv_path)

from supabase import create_client, Client, PostgrestAPIError, AuthApiError
from functools import wraps

try:
    from scipy.cluster import hierarchy
    from scipy.spatial import distance
    from scipy import stats as scipy_stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False

# Attempt to import statsmodels for Lilliefors test
try:
    from statsmodels.stats.diagnostic import lilliefors
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

# Attempt to import statsmodels.stats.diagnostic for Lilliefors test
try:
    from statsmodels.stats.diagnostic import lilliefors
    STATSMODELS_DIAG_AVAILABLE = True # Define it here
except ImportError:
    STATSMODELS_DIAG_AVAILABLE = False
# ***************************

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.impute import SimpleImputer # To handle NaNs before PCA
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

__version__ = "1.1.1"

# IMPORTANT: Set this to your GitHub repository in the format "username/reponame"
GITHUB_REPO = "PriyanujBoruah/DataWarpApp" 

# Global variable to hold update status information
UPDATE_INFO = {
    "available": False,
    "new_version": None,
    "download_url": None,
    "error": None
}

def check_for_updates():
    """Checks GitHub for the latest release and compares versions."""
    global UPDATE_INFO
    try:
        # Use standard logging, which works in any thread
        logging.info(f"Checking for updates... Current version: {__version__}")
        
        # Use the GITHUB_REPO variable defined earlier
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        
        response = requests.get(api_url, timeout=10)
        
        # Check for rate limiting or other API errors
        if response.status_code != 200:
            logging.warning(f"GitHub API returned status {response.status_code}. Response: {response.text[:200]}")
            UPDATE_INFO["error"] = f"GitHub API error (Status: {response.status_code})"
            return

        latest_release = response.json()
        latest_version_str = latest_release.get("tag_name", "").lstrip('v')

        if not latest_version_str:
            logging.warning("Could not find tag_name in latest release from GitHub.")
            UPDATE_INFO["error"] = "Could not parse release version."
            return

        logging.info(f"Latest version on GitHub: {latest_version_str}")

        if version.parse(latest_version_str) > version.parse(__version__):
            logging.info(f"New version {latest_version_str} is available!")
            
            assets = latest_release.get("assets", [])
            if not assets:
                logging.warning("New version found, but the release has no assets (no .exe file).")
                UPDATE_INFO["error"] = "Release contains no downloadable files."
                return

            for asset in assets:
                if asset.get('name') == 'DataWarpApp.exe':
                    UPDATE_INFO["available"] = True
                    UPDATE_INFO["new_version"] = latest_version_str
                    UPDATE_INFO["download_url"] = asset['browser_download_url']
                    UPDATE_INFO["error"] = None # Clear any previous error
                    logging.info("Update information successfully parsed.")
                    return # Exit after finding the correct asset
            
            # This code runs if the loop finishes without finding the .exe
            logging.warning("New version found, but 'DataWarpApp.exe' asset is missing from the release.")
            UPDATE_INFO["error"] = "Required release asset not found."

    except requests.exceptions.RequestException as e:
        logging.error(f"Network error while checking for updates: {e}")
        UPDATE_INFO["error"] = "Network error. Please check your internet connection."
    except Exception as e:
        logging.error(f"An unexpected error occurred in check_for_updates: {e}", exc_info=True)
        UPDATE_INFO["error"] = "An unexpected error occurred during update check."

def shutdown_server():
    """Function to be called in a thread to shut down the server."""
    app.logger.info("Server is shutting down...")
    os.kill(os.getpid(), signal.SIGINT)


# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
SAVED_SESSIONS_FOLDER = 'saved_sessions'
ALLOWED_EXTENSIONS = {'csv', 'tsv', 'xlsx'}

template_folder = resource_path('templates')
static_folder = resource_path('static')
app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SAVED_SESSIONS_FOLDER'] = SAVED_SESSIONS_FOLDER
# IMPORTANT: Change this to a strong, persistent secret key in production!
# Keep it outside version control.

SECRET_KEY_ENV = os.environ.get("FLASK_SECRET_KEY")
if SECRET_KEY_ENV:
    app.config['SECRET_KEY'] = SECRET_KEY_ENV
    app.logger.info("Loaded FLASK_SECRET_KEY from environment.")
else:
    # Fallback for development ONLY - NOT FOR PRODUCTION
    # Generate one for yourself (e.g., using python -c "import secrets; print(secrets.token_hex(32))")
    # and set it as an environment variable or use a .env file.
    # If you absolutely must hardcode for local dev and want persistence, use a fixed string:
    app.config['SECRET_KEY'] = "your-very-strong-and-static-secret-key-for-dev" # REPLACE THIS
    app.logger.warning(
        "FLASK_SECRET_KEY environment variable not set. Using a hardcoded key for development. "
        "Ensure FLASK_SECRET_KEY is set for production with a strong, unique value."
    )
    if app.config['SECRET_KEY'] == "your-very-strong-and-static-secret-key-for-dev": # Remind to change default
         app.logger.warning("CRITICAL: Replace the default hardcoded SECRET_KEY if you haven't!")

app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions in files
app.config['SESSION_FILE_DIR'] = './.flask_session' # Directory to store session files
# --- MODIFICATIONS FOR PERSISTENT SESSIONS ---
app.config['SESSION_PERMANENT'] = True # <<< MODIFICATION: Set to True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30) # <<< MODIFICATION: Example: 30 days. Adjust as needed.
# --- END MODIFICATIONS ---
app.config['SESSION_USE_SIGNER'] = True # Encrypt session cookie

# Supabase Configuration
app.config['SUPABASE_URL'] = os.environ.get("SUPABASE_URL")
app.config['SUPABASE_KEY'] = os.environ.get("SUPABASE_KEY")

# --- Initialize Flask-Session ---
# IMPORTANT: Do this *after* setting app.config values
server_session = Session(app)

# --- Initialize Supabase Client ---
supabase: Client = None
if app.config['SUPABASE_URL'] and app.config['SUPABASE_KEY']:
    try:
        supabase = create_client(app.config['SUPABASE_URL'], app.config['SUPABASE_KEY'])
        app.logger.info("Supabase client initialized.")
    except Exception as e:
        app.logger.error(f"Failed to initialize Supabase client: {e}")
else:
    app.logger.warning("SUPABASE_URL or SUPABASE_KEY not set in .env. Supabase features will be unavailable.")

# --- Create session directory if it doesn't exist ---
if not os.path.exists(app.config['SESSION_FILE_DIR']):
    os.makedirs(app.config['SESSION_FILE_DIR'])


# Create directories if they don't exist
for folder in [UPLOAD_FOLDER, SAVED_SESSIONS_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)



# --- Subscription Tiers & Information ---

SUBSCRIPTION_PLANS_DATA = {
    "pro": {
        "name": "DataWarp Pro",
        "id": "pro",
        "monthly_price_usd": 19,
        "yearly_price_usd": 179, # Approx $14.92/mo
        "currency_symbol": "$",
        "features": [
            "All Plus features",
            "Advanced AI-driven cleaning suggestions",
            "Automated data pipeline configurations",
            "Team collaboration (up to 5 users)",
            "Priority email & chat support",
            "1TB project storage allowance",
            "Access to beta features"
        ],
        "buttons": {"learn_more_link": "#pro-details", "choose_link": "#subscribe-pro"} # Placeholder links
    },
    
    "basic": {
        "name": "DataWarp Basic",
        "id": "basic",
        "price_display": "Free", # For free tier
        "monthly_price_usd": 0, # Add for logic if needed
        "yearly_price_usd": 0,  # Add for logic if needed
        "currency_symbol": "$", # Keep for consistency, though price is 0
        "features": [
            "Core data cleaning operations (duplicates, missing, type conversion)",
            "Upload CSV, TSV, XLSX files",
            "Basic data profiling & column statistics",
            "Undo/Redo functionality",
            "Download cleaned data (CSV, XLSX)",
            "1GB project storage allowance",
            "Community forum support"
        ],
        "buttons": {"learn_more_link": "#basic-details", "choose_link": "#subscribe-basic"}
    }
}


# --- Authentication Helper Functions & Decorator ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or not session.get('sb_access_token'):
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': 'Authentication required.', 'redirect_to': url_for('login', next=request.url)}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        # Optional: Add token refresh logic here if Supabase tokens are used for RLS or long sessions
        return f(*args, **kwargs)
    return decorated_function

def check_premium_status(user_data):
    """
    Authoritative function to check if a user has an active premium subscription.
    Returns True if the user is on a 'pro' tier and the subscription is not expired.
    Otherwise, returns False.
    """
    if not user_data or 'user_metadata' not in user_data:
        return False

    PREMIUM_TIERS = ['pro']  # A list of all tiers considered premium.
    
    tier = user_data['user_metadata'].get('subscription_tier', 'basic')

    # If the user's tier is not in our list of premium tiers, they are not premium.
    # This correctly handles 'basic', 'free', or any other non-premium tier names.
    if tier not in PREMIUM_TIERS:
        return False
    
    # If the tier IS in the premium list, we must also check if the subscription is still valid.
    valid_till_str = user_data['user_metadata'].get('subscription_valid_till')
    if not valid_till_str:
        # A premium user MUST have a validity date. If not, they are not considered premium.
        app.logger.warning(f"User with premium tier '{tier}' has no subscription_valid_till date. Access denied.")
        return False

    try:
        valid_till_date = date.fromisoformat(valid_till_str)
        # The subscription is active if its end date is today or in the future.
        if valid_till_date >= date.today():
            return True
        else:
            # The subscription has expired.
            return False
    except (ValueError, TypeError):
        # The date string is invalid or malformed.
        app.logger.warning(f"Could not parse subscription_valid_till '{valid_till_str}' for user. Access denied.")
        return False

def premium_required(f):
    """
    Ensures the user has a valid, active premium subscription.
    This decorator should be placed *after* @login_required.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # --- REPLACE THE OLD LOGIC BLOCK WITH THIS ---
        is_premium_user = check_premium_status(get_current_user_from_session())
        # --- END OF REPLACEMENT ---
        
        if not is_premium_user:
            message = 'This is a premium feature. Please upgrade your plan to access it.'
            # Handle AJAX requests with a JSON error
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': message, 'upgrade_required': True}), 403 # 403 Forbidden
            
            # For regular page loads, flash a message and redirect
            flash(message, 'info')
            return redirect(url_for('subscription_plans'))
            
        return f(*args, **kwargs)
    return decorated_function

def get_current_user_from_session():
    if 'user' in session and 'sb_access_token' in session:
        return session['user']
    return None

def get_referral_data(user_id_to_check: str):
    app.logger.error(f"--- GET_REFERRAL_DATA CALLED with user_id: {user_id_to_check} ---")
    """
    Fetches referral count and a list of referred usernames for a given user ID.
    Returns a dictionary {'count': int, 'list': list_of_usernames}.
    """
    # === INTENSE DEBUGGING START ===
    app.logger.error(f"--- [get_referral_data CALLED] ---")
    app.logger.error(f"[get_referral_data] Input user_id_to_check: '{user_id_to_check}' (Type: {type(user_id_to_check)})")
    # === INTENSE DEBUGGING END ===

    if not user_id_to_check or not supabase:
        app.logger.error(f"[get_referral_data] Invalid input: user_id_to_check='{user_id_to_check}' or supabase client missing.")
        return {'count': 0, 'list': []}

    referral_count = 0
    referred_usernames = []
    max_referrals_list_preview = 5

    try:
        # === INTENSE DEBUGGING START ===
        query_user_id_str = str(user_id_to_check)
        app.logger.error(f"[get_referral_data] ID being used for query: '{query_user_id_str}' (Type: {type(query_user_id_str)})")
        app.logger.error(f"[get_referral_data] EXACT Supabase query for count: supabase.table('profiles').select('id', count='exact').eq('referred_by_user_id', '{query_user_id_str}')")
        # === INTENSE DEBUGGING END ===

        count_response = supabase.table('profiles').select('id', count='exact').eq('referred_by_user_id', query_user_id_str).execute()
        
        # === INTENSE DEBUGGING START ===
        app.logger.error(f"[get_referral_data] Supabase count_response object: {count_response}")
        app.logger.error(f"[get_referral_data] Count query for user '{query_user_id_str}': Response count attr = {getattr(count_response, 'count', 'N/A')}, Response data = {getattr(count_response, 'data', 'N/A')}")
        # === INTENSE DEBUGGING END ===

        if hasattr(count_response, 'count') and count_response.count is not None:
            referral_count = count_response.count
        else:
            app.logger.error(f"[get_referral_data] Could not get referral count for user ID '{query_user_id_str}'. Raw Response: {count_response}")

        if referral_count > 0:
            # ... (list fetching logic - let's focus on count first) ...
            pass # For now, skip list fetching to isolate count issue

    except PostgrestAPIError as e:
        app.logger.error(f"[get_referral_data] PostgrestAPIError for user ID '{user_id_to_check}': {e.message} (Code: {e.code}, Details: {e.details}, Hint: {getattr(e, 'hint', 'N/A')})")
    except Exception as e_gen:
        app.logger.error(f"[get_referral_data] General error for user ID '{user_id_to_check}': {e_gen}", exc_info=True)

    app.logger.error(f"[get_referral_data] Returning: {{'count': {referral_count}, 'list': {referred_usernames}}}")
    return {'count': referral_count, 'list': referred_usernames}

@app.context_processor
def inject_user():
    app.logger.error("--- INJECT_USER CALLED ---")
    # === Log entry into inject_user ===
    app.logger.info(f"--- [inject_user CALLED] ---")

    user_data_from_session = get_current_user_from_session()
    display_name = "Guest"
    user_for_template = None # This will hold all data for the 'current_user' template variable
    
    # Default referral info structure
    default_referral_info = {
        'count': 0,
        'list_preview': [],
        'max_display': 10,
        'needed_for_reward': 10,
        'reward_target': 10
    }
    max_referrals_for_reward = 10 # Target for the 6-month Pro reward

    if user_data_from_session:
        user_for_template = user_data_from_session.copy() # Start with a copy of session data

        # Determine display name
        if 'user_metadata' in user_data_from_session and user_data_from_session['user_metadata'].get('username'):
            display_name = user_data_from_session['user_metadata']['username']
        elif user_data_from_session.get('email'):
            display_name = user_data_from_session['email']
        else:
            display_name = "User" # Fallback display name
        
        app.logger.info(f"[inject_user] User identified: {display_name}")

        current_auth_user_id = user_data_from_session.get('id')
        app.logger.info(f"[inject_user] current_auth_user_id from session: '{current_auth_user_id}' (Type: {type(current_auth_user_id)})")

        # Initialize referral_info in user_for_template
        user_for_template['referral_info'] = default_referral_info.copy()

        if current_auth_user_id:
            # Call the helper function to get referral count and list
            # The get_referral_data function itself has detailed logging
            referral_data_from_helper = get_referral_data(str(current_auth_user_id))
            
            fetched_referral_count = referral_data_from_helper.get('count', 0)
            fetched_referral_list = referral_data_from_helper.get('list', [])

            app.logger.info(f"[inject_user] Data from get_referral_data for user '{current_auth_user_id}': count={fetched_referral_count}, list_preview_count={len(fetched_referral_list)}")

            user_for_template['referral_info']['count'] = fetched_referral_count
            user_for_template['referral_info']['list_preview'] = fetched_referral_list
            
            # Calculate referrals needed for the reward based on fetched count
            if fetched_referral_count < max_referrals_for_reward:
                user_for_template['referral_info']['needed_for_reward'] = max_referrals_for_reward - fetched_referral_count
            else:
                user_for_template['referral_info']['needed_for_reward'] = 0 # Achieved or surpassed
        else:
            app.logger.warning(f"[inject_user] No current_auth_user_id found in session data. Referral count will be 0.")
            # referral_info remains as default (0 count, etc.)

        # Ensure all referral_info keys are present even if no user_id was found (already handled by default_referral_info)
        app.logger.info(f"[inject_user] Final user_for_template['referral_info'] being prepared: {user_for_template.get('referral_info')}")

    else: # No user_data_from_session (user not logged in)
        app.logger.info(f"[inject_user] No user_data_from_session. Guest user.")
        # user_for_template remains None, display_name remains "Guest"
        # No referral_info will be added to user_for_template in this case.

    # Log what's being returned to the template context
    if user_for_template:
        log_referral_count_in_template = user_for_template.get('referral_info', {}).get('count', 'N/A (no referral_info)')
        app.logger.info(f"[inject_user] Returning to template: current_user set (referral count: {log_referral_count_in_template}), display_name: {display_name}")
    else:
        app.logger.info(f"[inject_user] Returning to template: current_user is None, display_name: {display_name}")

    return dict(current_user=user_for_template, current_user_display_name=display_name)


# --- Helper Functions ---

def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_dataframe_from_session():
    """Safely retrieve the current DataFrame from session."""
    df_json = session.get('current_df_json')
    if df_json:
        try:
            # Read JSON string back into DataFrame
            # orient='split' is often efficient for round-tripping
            return pd.read_json(io.StringIO(df_json), orient='split')
        except Exception as e:
            flash(f"Error loading data from session: {e}", "error")
            clear_session_data() # Clear corrupted data
            return None
    return None

def store_dataframe_in_session(df):
    """Store DataFrame in session as JSON string."""
    if df is None:
        session.pop('current_df_json', None)
        return
    try:
        # Convert DataFrame to JSON string using 'split' orientation
        # Handle potential date issues during serialization
        df_json = df.to_json(orient='split', date_format='iso', default_handler=str)
        session['current_df_json'] = df_json
    except Exception as e:
        flash(f"Error storing data in session: {e}. Data might be too large or contain unserializable types.", "error")
        # Decide how to handle: maybe clear session or keep old data?
        # session.pop('current_df_json', None) # Option: clear if storing fails

def add_to_undo(current_df_json):
    """Add current state to undo history (limited size)."""
    if not current_df_json: return
    undo_history = session.get('undo_history', [])
    undo_history.append(current_df_json)
    # Limit history size to prevent huge sessions
    max_history = 10
    session['undo_history'] = undo_history[-max_history:]
    session['redo_history'] = [] # Clear redo on new action

def get_undo_redo_status():
    """Return boolean status for undo/redo availability."""
    return {
        'undo_enabled': bool(session.get('undo_history')),
        'redo_enabled': bool(session.get('redo_history'))
    }

# Modified: render_table_html now optionally returns counts too
def render_table_html(df, max_rows=999):
    """Generates HTML for the table preview and returns dimensions."""
    if df is None or df.empty:
        table_html = "<p class='text-center text-muted p-4'>No data to display or data is empty.</p>"
        total_rows = 0
        total_columns = 0
    else:
        # Create a display version, limiting rows
        display_df = df.head(max_rows).copy() # Use .copy() to avoid SettingWithCopyWarning

        # Add a 1-based row number column at the beginning
        # This column is purely for display in this HTML table
        # Ensure the column name '#' doesn't already exist in a conflicting way,
        # though for a simple display '#' is standard.
        # If df could legitimately have a '#' column that needs preserving,
        # a more robust unique name generation for the row number column would be needed.
        # For typical use, this is fine.
        display_df.insert(0, '#', range(1, len(display_df) + 1))

        table_html = display_df.to_html(
            classes='table table-bordered table-hover table-sm', # smaller table
            index=False, # Crucial: we've manually added our row number column
            border=0,
            escape=True, # Default and good for security
            na_rep='' # Custom NaN representation
        )
        total_rows = len(df) # Get total rows from the full DataFrame
        total_columns = len(df.columns) # Get total data columns from the full DataFrame (excludes the display-only '#')

    return table_html, total_rows, total_columns

def clear_session_data():
    """Clears all data related to the current cleaning session."""
    session.pop('current_df_json', None)
    session.pop('undo_history', None)
    session.pop('redo_history', None)
    session.pop('source_info', None)
    session.pop('saved_filename', None) # Also clear saved file link



@app.route('/update-status')
def update_status():
    """An endpoint for the frontend to poll for update info."""
    return jsonify(UPDATE_INFO)

@app.route('/apply-update', methods=['POST'])
def apply_update():
    """Downloads the new executable and runs the updater script."""
    if not UPDATE_INFO.get("available") or not UPDATE_INFO.get("download_url"):
        return jsonify({"error": "No update available or download URL is missing."}), 400

    download_url = UPDATE_INFO.get("download_url")
    new_version = UPDATE_INFO.get("new_version")
    
    try:
        # Define path for the new executable in a temporary location
        # Using os.environ.get('TEMP', ...) is a robust way to find the temp dir
        temp_dir = os.environ.get('TEMP', os.path.dirname(sys.executable))
        new_exe_path = os.path.join(temp_dir, f"DataWarpApp-v{new_version}.exe")
        
        app.logger.info(f"Downloading update from {download_url} to {new_exe_path}")
        response = requests.get(download_url, stream=True, timeout=300) # 5-min timeout
        response.raise_for_status()
        with open(new_exe_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        app.logger.info("Download complete.")

        current_exe_path = sys.executable
        updater_script_path = resource_path('updater.py')

        # Launch the updater script in a new detached process
        subprocess.Popen([sys.executable, updater_script_path, str(os.getpid()), current_exe_path, new_exe_path])

        # Immediately start the shutdown process for the current app
        shutdown_server()
        
        # This response may or may not reach the client, which is fine.
        return jsonify({"message": "Update process initiated. Application is restarting."})

    except Exception as e:
        app.logger.error(f"Failed to apply update: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/shutdown', methods=['POST'])
def shutdown():
    """Shuts down the application server."""
    shutdown_thread = threading.Timer(0.5, shutdown_server)
    shutdown_thread.start()
    return jsonify({ "message": "Server is shutting down..." }), 200


# --- Authentication Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    # If a user is already logged in, redirect them away from the login page.
    if get_current_user_from_session():
        return redirect(url_for('clean_data_interface'))

    # Handle the form submission on POST request
    if request.method == 'POST':
        # Gracefully handle if Supabase is not configured
        if not supabase:
            flash('Authentication service is currently unavailable.', 'danger')
            return render_template('login.html')

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        next_url = request.form.get('next') # To redirect to the page the user was trying to access

        # Basic form validation
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return render_template('login.html', email=email) # Pass email back to form

        try:
            # Step 1: Authenticate with Supabase Auth. This verifies email and password.
            auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
            
            # If successful, store the primary auth data in the Flask session
            user_auth_data = auth_response.user.dict()
            session['user'] = user_auth_data
            session['sb_access_token'] = auth_response.session.access_token
            session['sb_refresh_token'] = auth_response.session.refresh_token
            app.logger.info(f"User {email} authenticated successfully. Auth User ID: {user_auth_data.get('id')}")

            # Step 2: Fetch the user's full profile from the `profiles` table.
            # This is our "source of truth" for subscription status and other custom data.
            auth_user_id = user_auth_data.get('id')
            if auth_user_id:
                try:
                    profile_res = supabase.table('profiles').select('*').eq('id', str(auth_user_id)).maybe_single().execute()
                    
                    if profile_res.data:
                        # Profile was found in the database.
                        app.logger.info(f"Profile data fetched from DB for {email}: {profile_res.data}")
                        
                        # Store the full database profile for reference if needed elsewhere.
                        session['user']['db_profile'] = profile_res.data
                        
                        # ================================================================= #
                        # --- CRITICAL FIX: SYNCHRONIZE SESSION METADATA ---
                        # Overwrite the potentially stale `user_metadata` in the session 
                        # with the fresh, authoritative data from our `profiles` table.
                        # ================================================================= #
                        fresh_profile_data = profile_res.data
                        
                        app.logger.debug(f"Session metadata BEFORE sync: {session['user'].get('user_metadata')}")

                        # Ensure 'user_metadata' key exists, then update it.
                        session['user'].setdefault('user_metadata', {}).update({
                            'subscription_tier': fresh_profile_data.get('subscription_tier', 'basic'),
                            'subscription_valid_till': fresh_profile_data.get('subscription_valid_till'),
                            'username': fresh_profile_data.get('username')
                        })
                        
                        # Explicitly mark the session as modified to ensure changes are saved.
                        session.modified = True 
                        
                        app.logger.debug(f"Session metadata AFTER sync: {session['user']['user_metadata']}")

                    else:
                        # This case is rare but could happen if the trigger to create a profile fails.
                        app.logger.warning(f"No profile found in DB for user {email}. Using default auth metadata.")
                        session['user']['db_profile'] = None
                
                except PostgrestAPIError as e:
                    app.logger.error(f"Error fetching DB profile for {email} on login: {e.message}")
                    session['user']['db_profile'] = None # Indicate profile fetch failed
                except Exception as e_profile:
                    app.logger.error(f"General error fetching DB profile for {email}: {e_profile}", exc_info=True)
                    session['user']['db_profile'] = None

            # Finalize the login process
            flash('Logged in successfully!', 'success')
            app.logger.info(f"User {email} full login process complete. Redirecting.")
            
            # Redirect to the originally requested page or a default dashboard page
            return redirect(next_url or url_for('clean_data_interface'))

        except AuthApiError as e:
            # Handle specific authentication errors from Supabase
            error_message_detail = e.message
            if "Invalid login credentials" in e.message:
                error_message_detail = "Invalid email or password. Please try again."
            elif "Email not confirmed" in e.message:
                error_message_detail = "Your email address has not been confirmed. Please check your inbox."
            
            flash(f'Login failed: {error_message_detail}', 'danger')
            app.logger.warning(f"Login AuthApiError for {email}: {e.message}")
            return render_template('login.html', email=email)
        
        except Exception as e:
            # Handle any other unexpected errors (e.g., network issues)
            app.logger.error(f"Login general error for {email}: {e}", exc_info=True)
            flash('An unexpected error occurred during login. Please try again.', 'danger')
            return render_template('login.html', email=email)

    # For GET request, just show the login page
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password_request():
    if get_current_user_from_session(): # If already logged in, no need to reset
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if not email:
            flash('Email address is required.', 'danger')
            return render_template('forgot_password_request.html')

        if not supabase:
            flash('Authentication service is currently unavailable.', 'danger')
            return render_template('forgot_password_request.html', email=email)

        try:
            # IMPORTANT: Configure Redirect URL in Supabase Auth settings
            # The link sent will be like: YOUR_SITE_URL/#access_token=...&refresh_token=...&type=recovery
            # You might need to specify a `redirect_to` parameter if you have a specific page
            # for handling the password reset form, e.g., redirect_to=f"{request.url_root}set-new-password"
            # For this example, we'll assume client-side JS on a main page handles the hash.
            
            # Ensure your Supabase project's "Site URL" is correctly set.
            # e.g. http://127.0.0.1:5000 or your production URL
            # The reset link in the email will use this Site URL.
            
            # If you want the reset link to go to a specific page *on your server* to then show the form,
            # you need to ensure that page can handle the hash fragments, or use a client-side router.
            # A simpler approach if you don't have heavy client-side routing is to let it go to your
            # main app page, and have JS there detect the #recovery hash.
            
            # Let's assume the default behavior where Supabase sends user to SITE_URL/#...
            # We will handle this hash on a client-side page later (e.g. a dedicated reset page or login page)
            supabase.auth.reset_password_for_email(
                email=email
                # redirect_to="OPTIONAL_URL_IF_NOT_SITE_URL" # e.g., request.url_root + 'new-password-form'
            )
            flash('If an account exists for this email, a password reset link has been sent. Please check your inbox (and spam folder).', 'success')
            app.logger.info(f"Password reset email requested for: {email}")
            return redirect(url_for('login')) # Redirect to login page after request

        except AuthApiError as e:
            flash(f'Error requesting password reset: {e.message}', 'danger')
            app.logger.error(f"AuthApiError on password reset request for {email}: {e.message}")
        except Exception as e:
            flash('An unexpected error occurred. Please try again.', 'danger')
            app.logger.error(f"General error on password reset request for {email}: {e}", exc_info=True)
        
        return render_template('forgot_password_request.html', email=email)

    return render_template('forgot_password_request.html')

@app.route('/set-new-password', methods=['GET', 'POST'])
def set_new_password_form():
    app.logger.debug(f"--- /set-new-password route hit. Method: {request.method} ---")

    recovery_token_from_query = request.args.get('token')
    refresh_token_from_query = request.args.get('refresh_token')
    app.logger.debug(f"GET Query Params: token='{str(recovery_token_from_query)[:10] if recovery_token_from_query else 'None'}...', refresh_token='{str(refresh_token_from_query)[:10] if refresh_token_from_query else 'None'}...'")

    if request.method == 'GET':
        if recovery_token_from_query:
            session['recovery_access_token'] = recovery_token_from_query
            if refresh_token_from_query:
                session['recovery_refresh_token'] = refresh_token_from_query
            app.logger.info(f"Password reset form GET (initial with query token). Recovery token stored in session. Redirecting to hide token from URL.")
            app.logger.debug(f"Session after storing tokens: {session}")
            return redirect(url_for('set_new_password_form', _external=True, _scheme=request.scheme))
        
        if 'recovery_access_token' not in session:
            flash('Invalid or expired password reset session. Please request a new reset link.', 'danger')
            app.logger.warning("GET /set-new-password without recovery_access_token in query or session.")
            return redirect(url_for('forgot_password_request'))
        
        app.logger.debug("GET /set-new-password (after redirect or direct access with session token). Rendering form.")
        return render_template('reset_password_form.html')

    # POST: User has submitted the new password
    if request.method == 'POST':
        app.logger.info(f"--- POST to /set-new-password ---")
        app.logger.debug(f"Raw form data received: {request.form}") # DEBUG: Log all form data

        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        app.logger.debug(f"Value of 'new_password' from form: '{new_password}' (Type: {type(new_password)})")
        app.logger.debug(f"Value of 'confirm_password' from form: '{confirm_password}' (Type: {type(confirm_password)})")
        
        session_recovery_access_token = session.pop('recovery_access_token', None)
        session_recovery_refresh_token = session.pop('recovery_refresh_token', None)
        app.logger.debug(f"Popped recovery_access_token from session: {'SET' if session_recovery_access_token else 'NOT SET'}")
        app.logger.debug(f"Popped recovery_refresh_token from session: {'SET' if session_recovery_refresh_token else 'NOT SET'}")


        if not session_recovery_access_token:
            flash('Password reset session expired or token is missing. Please request a new reset link.', 'danger')
            app.logger.warning("Recovery token missing from session during POST to set_new_password_form.")
            return redirect(url_for('forgot_password_request'))

        # --- Validations ---
        if not new_password or not confirm_password:
            flash('Both password fields are required.', 'danger')
            app.logger.warning(f"Validation failed: new_password or confirm_password is empty. new_password='{new_password}', confirm_password='{confirm_password}'")
            session['recovery_access_token'] = session_recovery_access_token # Put token back for retry
            if session_recovery_refresh_token: session['recovery_refresh_token'] = session_recovery_refresh_token
            return render_template('reset_password_form.html') 
        if new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
            app.logger.warning("Validation failed: Passwords do not match.")
            session['recovery_access_token'] = session_recovery_access_token
            if session_recovery_refresh_token: session['recovery_refresh_token'] = session_recovery_refresh_token
            return render_template('reset_password_form.html')
        if len(new_password) < 6: 
            flash('Password must be at least 6 characters long.', 'danger')
            app.logger.warning("Validation failed: Password too short.")
            session['recovery_access_token'] = session_recovery_access_token
            if session_recovery_refresh_token: session['recovery_refresh_token'] = session_recovery_refresh_token
            return render_template('reset_password_form.html')

        if not supabase:
            flash('Authentication service is currently unavailable. Please try again later.', 'danger')
            app.logger.error("Supabase client not initialized during password reset POST.")
            session['recovery_access_token'] = session_recovery_access_token
            if session_recovery_refresh_token: session['recovery_refresh_token'] = session_recovery_refresh_token
            return render_template('reset_password_form.html')

        try:
            app.logger.info(f"Attempting to set Supabase session with recovery_access_token: {session_recovery_access_token[:10]}...")
            supabase.auth.set_session(
                access_token=session_recovery_access_token, 
                refresh_token=session_recovery_refresh_token
            )
            app.logger.info(f"Supabase session set successfully for password update.")

            app.logger.info(f"Attempting to update password for user associated with token.")
            update_response = supabase.auth.update_user(attributes={'password': new_password})
            app.logger.debug(f"Supabase auth update_user response: {update_response}")
            
            if update_response.user:
                flash('Your password has been successfully updated! You can now log in with your new password.', 'success')
                app.logger.info(f"Password successfully reset for user (ID: {update_response.user.id}) using recovery token.")
                try:
                    supabase.auth.sign_out() 
                    app.logger.info("Supabase client session cleared after password reset.")
                except Exception as e_signout:
                    app.logger.warning(f"Minor error during sign_out after password reset: {e_signout}")
                return redirect(url_for('login'))
            else:
                # This case is unusual if no AuthApiError was raised but user object is missing.
                flash('Password update request sent, but server confirmation was incomplete. Please try logging in with your new password.', 'warning')
                app.logger.warning(f"Password reset for token {session_recovery_access_token[:10]}... processed by update_user but no user object returned in response.")
                return redirect(url_for('login'))

        except AuthApiError as e:
            flash_msg = f'Error resetting password: {e.message}'
            if "token" in e.message.lower() or "invalid" in e.message.lower() or "jwt" in e.message.lower() or "expired" in e.message.lower():
                flash_msg = "Invalid or expired password reset token/session. Please request a new reset link."
            elif "User not found" in e.message: # Should not happen if set_session succeeded, but as a safeguard
                flash_msg = "User associated with this reset link not found. Please request a new reset link."

            flash(flash_msg, 'danger')
            app.logger.error(f"AuthApiError on password reset for token {session_recovery_access_token[:10]}...: {e.message} (Status: {getattr(e, 'status', 'N/A')}, Details: {getattr(e, '__dict__', {})})")
            return redirect(url_for('forgot_password_request'))
        except Exception as e:
            flash('An unexpected error occurred while resetting your password. Please try again.', 'danger')
            app.logger.error(f"General error on password reset for token {session_recovery_access_token[:10]}...: {e}", exc_info=True)
            return redirect(url_for('forgot_password_request'))

    # Fallback for GET if token was not in query and not in session (should ideally be caught by checks above)
    # This part of the GET logic is after the initial redirect, so query token won't be there.
    app.logger.debug("Reached end of set_new_password_form function (should be GET after redirect).")
    if request.method == 'GET' and 'recovery_access_token' not in session:
        flash('No valid password reset session found. Please request a reset link first.', 'info')
        app.logger.warning("GET /set-new-password (after potential redirect) but recovery_access_token still not in session.")
        return redirect(url_for('forgot_password_request'))
        
    # This will only be reached on GET if 'recovery_access_token' is in session
    return render_template('reset_password_form.html')

# app.py

# Make sure these are at the top of your file if not already
from datetime import datetime, timedelta
# import uuid # No longer needed here if trigger sets referral_code to user's ID

# ... (rest of your imports and app setup) ...

# Ensure this function is defined or imported correctly
def get_current_user_from_session():
    if 'user' in session and 'sb_access_token' in session:
        return session['user']
    return None

# ... (rest of your Flask app setup and other routes) ...

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if get_current_user_from_session():
        return redirect(url_for('index'))

    if request.method == 'POST':
        if not supabase:
            flash('Supabase client not initialized. Signup is unavailable.', 'danger')
            return render_template('signup.html')

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        username = request.form.get('username', '').strip()
        # REMOVED: full_name, occupation, workplace from form GET
        referral_code_used_by_new_user = request.form.get('referral_code_used', '').strip()

        # --- Server-side validation ---
        form_data_for_retry = {
            "email": email, "username": username,
            "referral_code_used": referral_code_used_by_new_user
            # REMOVED: full_name, occupation, workplace from here
        }
        if not email or not password or not username:
            flash('Email, password, and username are required.', 'danger')
            return render_template('signup.html', **form_data_for_retry)
        if not re.match(r"^[a-zA-Z0-9_.-]{3,20}$", username):
            flash('Invalid username. It must be 3-20 characters long and can contain letters, numbers, underscores, dots, or hyphens.', 'danger')
            return render_template('signup.html', **form_data_for_retry)
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('signup.html', **form_data_for_retry)

        try:
            initial_subscription_tier = "pro"
            valid_till_date = datetime.utcnow().date() + timedelta(days=30)
            valid_till_iso = valid_till_date.isoformat()

            user_metadata_payload = {
                'username': username,
                # 'full_name': username, # Set by trigger based on username, or leave for user to set later
                                        # The trigger I provided sets full_name from metadata if present,
                                        # otherwise it might be null.
                                        # For simplicity, let's ensure the trigger handles this or sets it to username.
                # REMOVED: occupation, workplace from metadata payload
                'subscription_tier': initial_subscription_tier,
                'subscription_valid_till': valid_till_iso,
                'referral_code_used': referral_code_used_by_new_user if referral_code_used_by_new_user else None
            }
            # If your trigger relies on full_name, occupation, workplace being in metadata,
            # you might pass empty strings or ensure the trigger defaults them to NULL.
            # The trigger from previous response expects 'full_name', 'occupation', 'workplace'
            # Let's explicitly pass them as potentially empty for the trigger.
            user_metadata_payload['full_name'] = username # Default full_name to username for trigger
            user_metadata_payload['occupation'] = ""     # Send empty string, trigger will handle as NULL or empty
            user_metadata_payload['workplace'] = ""      # Send empty string


            app.logger.info(f"Attempting signup for {email} with metadata for trigger: {user_metadata_payload}")

            res = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": user_metadata_payload
                }
            })
            
            # ... (rest of your existing logging and success/error handling for res) ...
            if res.user and res.user.id:
                app.logger.info(f"User {email} (Username: {username}) auth record created. User ID: {res.user.id}. Profile row will be auto-created.")
            # ...

            flash_message = 'Signup successful! You have received a 1-month free trial of DataWarp Pro. '
            if referral_code_used_by_new_user:
                flash_message += "Thank you for using a referral code! "
            flash_message += 'Please check your email to confirm your account (if email confirmations are enabled by Supabase).'
            flash(flash_message, 'success')
            return redirect(url_for('login'))

        except AuthApiError as e:
            # ... (your existing AuthApiError handling, pass **form_data_for_retry to render_template) ...
            error_message_detail = e.message # ... (rest of your error handling)
            flash(f'Signup failed: {error_message_detail}', 'danger')
            return render_template('signup.html', **form_data_for_retry)
        except Exception as e:
            # ... (your existing general Exception handling, pass **form_data_for_retry to render_template) ...
            flash('An unexpected error occurred during signup.', 'danger')
            return render_template('signup.html', **form_data_for_retry)

    # For GET request
    return render_template('signup.html')

@app.route('/logout')
@login_required
def logout():
    user_email = session.get('user', {}).get('email', 'Unknown user')
    if supabase and session.get('sb_access_token'):
        try:
            # supabase.auth.sign_out() # This invalidates the token on Supabase side
            # For supabase-py, sign_out invalidates the current session for the client instance.
            # If the client instance is request-scoped or re-created, this might not be enough.
            # The key is to remove the token from the Flask session.
            # If RLS depends heavily on live token validation for every request,
            # Supabase might have an endpoint to explicitly revoke a token.
            # For now, clearing Flask session is the primary goal.
            # supabase.auth.admin.sign_out(session['sb_access_token']) # This is an admin action, probably not what we want.
            # The go-true server for Supabase doesn't have a simple /logout endpoint that revokes a specific JWT.
            # The client is expected to "forget" the JWT.
            pass
        except Exception as e:
            app.logger.error(f"Error during Supabase signout attempt for {user_email}: {e}", exc_info=True)
            flash('An error occurred during server-side sign out. Your local session is cleared.', 'warning')

    session.pop('user', None)
    session.pop('sb_access_token', None)
    session.pop('sb_refresh_token', None)
    clear_session_data() # Crucial: Clear data cleaning related session info
    flash('You have been logged out.', 'success')
    app.logger.info(f"User {user_email} logged out.")
    return redirect(url_for('index'))

@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    app.logger.info("--- ACCOUNT ROUTE ENTERED ---")
    user_session_data = get_current_user_from_session()
    if not user_session_data:
        flash('User data not found in session. Please log in again.', 'danger')
        app.logger.error("Account page accessed without user_session_data.")
        return redirect(url_for('login'))

    auth_user_id = user_session_data.get('id') 
    user_email_for_logging = user_session_data.get('email', 'UNKNOWN_EMAIL')

    app.logger.debug(f"--- [/account ROUTE TOP] ---")
    app.logger.debug(f"[/account route] auth_user_id from session (this is the logged-in user): '{auth_user_id}' (Type: {type(auth_user_id)})")

    if not auth_user_id:
        flash('User authentication ID not found in session. Please log in again.', 'danger')
        app.logger.error(f"auth_user_id missing from session['user'] for {user_email_for_logging} in account route.")
        return redirect(url_for('login'))

    app.logger.debug(f"[/account] Page access for user: {user_email_for_logging}, auth_id: {auth_user_id}")

    if supabase and 'sb_access_token' in session and session.get('sb_access_token'):
        try:
            supabase.auth.set_session(
                access_token=session['sb_access_token'],
                refresh_token=session.get('sb_refresh_token')
            )
            app.logger.debug(f"[/account] Supabase auth session explicitly set for user {user_email_for_logging}.")
        except Exception as e_set_session:
            app.logger.error(f"[/account] Failed to set Supabase auth session for {user_email_for_logging}: {e_set_session}", exc_info=True)
            flash("Authentication session issue. Could not load account details. Please try logging in again.", "danger")
            return redirect(url_for('login'))
    elif supabase is None:
        app.logger.error("[/account] Supabase client is not initialized. Cannot perform DB operations.")
        flash("Database service is unavailable. Please try again later.", "danger")
        return render_template('account.html', user_profile_data={}, referred_users_count=0, referred_users_list=[])
    else:
        app.logger.error(f"[/account] Supabase access token missing from Flask session for {user_email_for_logging}.")
        flash("Your session has expired or is invalid. Please log in again.", "danger")
        return redirect(url_for('login'))

    display_data = {
        'email': user_session_data.get('email', 'N/A'),
        'username': user_session_data.get('user_metadata', {}).get('username', 'N/A'),
        'full_name': user_session_data.get('user_metadata', {}).get('full_name', ''),
        'occupation': user_session_data.get('user_metadata', {}).get('occupation', ''),
        'workplace': user_session_data.get('user_metadata', {}).get('workplace', ''),
        'subscription_tier': user_session_data.get('user_metadata', {}).get('subscription_tier', 'basic'),
        'referral_code': str(auth_user_id) if auth_user_id else 'N/A',
        'valid_till': user_session_data.get('user_metadata', {}).get('subscription_valid_till', 'N/A')
    }
    app.logger.debug(f"[/account] Initial display_data from session for {user_email_for_logging}: {display_data}")
    
    profile_res = None 
    if supabase:
        try:
            profile_res = supabase.table('profiles').select("*, referral_pro_reward_claimed_at").eq('id', str(auth_user_id)).maybe_single().execute()
            if profile_res.data:
                app.logger.debug(f"[/account] Fetched profile from DB for display: {profile_res.data}")
                display_data.update({
                    'username': profile_res.data.get('username', display_data['username']),
                    'full_name': profile_res.data.get('full_name', display_data['full_name']),
                    'occupation': profile_res.data.get('occupation', display_data['occupation']),
                    'workplace': profile_res.data.get('workplace', display_data['workplace']),
                    'subscription_tier': profile_res.data.get('subscription_tier', display_data['subscription_tier']),
                    'referral_code': profile_res.data.get('referral_code', display_data['referral_code']),
                    'valid_till': str(profile_res.data.get('subscription_valid_till')) if profile_res.data.get('subscription_valid_till') else 'N/A'
                })
                app.logger.debug(f"[/account] Refreshed display_data after DB query: {display_data}")
            elif request.method == 'GET':
                 app.logger.warning(f"[/account] No profile found in DB for user ID {auth_user_id}. Using session data for display.")
        except PostgrestAPIError as e:
            app.logger.error(f"[/account] PostgrestAPIError fetching profile for display: {e.message}", exc_info=True)
            if request.method == 'GET': flash("Could not retrieve latest profile details from database.", "warning")
        except Exception as e_gen:
            app.logger.error(f"[/account] General error fetching profile for display: {e_gen}", exc_info=True)
            if request.method == 'GET': flash("An unexpected error occurred while retrieving your profile.", "warning")

    if request.method == 'POST':
        form_type = request.form.get('form_type')
        app.logger.info(f"[/account] POST request for form_type: {form_type} by user {auth_user_id}")
        
        if form_type == 'profile':
            # Placeholder - Implement actual profile update logic
            flash('Profile update functionality placeholder.', 'info')
            return redirect(url_for('account'))
        elif form_type == 'password':
            # Placeholder - Implement actual password change logic
            flash('Password change functionality placeholder.', 'info')
            return redirect(url_for('account'))
        else:
            flash('Invalid form submission.', 'warning')
            return redirect(url_for('account'))

    app.logger.debug(f"[/account GET] Calling get_referral_data with user_id_to_check: '{str(auth_user_id)}'")
    referral_data_for_page = get_referral_data(str(auth_user_id)) 
    referred_users_count_for_page = referral_data_for_page.get('count', 0)
    referred_users_list_for_page = referral_data_for_page.get('list', [])

    app.logger.debug(f"[/account GET] Data from get_referral_data: count={referred_users_count_for_page}, list_preview_count={len(referred_users_list_for_page)}")

    # *********************************************************************
    # --- MODIFIED: Referral Reward Logic (Stacks on existing sub) ---
    # *********************************************************************
    if supabase and profile_res and profile_res.data:
        referral_count = referred_users_count_for_page
        reward_target = 10 
        reward_already_claimed = profile_res.data.get('referral_pro_reward_claimed_at') is not None

        if referral_count >= reward_target and not reward_already_claimed:
            app.logger.info(f"User {auth_user_id} (Email: {user_email_for_logging}) is eligible for referral reward. Referrals: {referral_count}.")
            try:
                current_db_tier = profile_res.data.get('subscription_tier')
                current_db_valid_till_str = profile_res.data.get('subscription_valid_till') # 'YYYY-MM-DD' or None
                
                now_utc_dt = datetime.now(timezone.utc) # Aware datetime object
                six_months_duration = timedelta(days=183) # Approx 6 months

                # Determine the starting point for adding the 6 months
                current_subscription_end_dt = now_utc_dt # Default to now if no valid sub or it's in the past

                if current_db_valid_till_str:
                    try:
                        parsed_date_obj = date.fromisoformat(current_db_valid_till_str)
                        # Convert to datetime at end of day for comparison/stacking
                        # If subscription ends on YYYY-MM-DD, it's valid *through* that day.
                        # So, new period starts *after* that day.
                        current_valid_till_datetime_obj_end_of_day = datetime.combine(parsed_date_obj, datetime.max.time()).replace(tzinfo=timezone.utc)
                        
                        # If current subscription is still valid in the future, use its end date as the base
                        if current_valid_till_datetime_obj_end_of_day > now_utc_dt:
                            current_subscription_end_dt = current_valid_till_datetime_obj_end_of_day
                        app.logger.info(f"User {auth_user_id} has existing sub ending: {current_valid_till_datetime_obj_end_of_day}. Base for reward: {current_subscription_end_dt}")
                    
                    except ValueError as ve:
                        app.logger.warning(f"Could not parse current_db_valid_till_str '{current_db_valid_till_str}' for user {auth_user_id}. Using current time as base. Error: {ve}")
                        # current_subscription_end_dt remains now_utc_dt
                
                # Add 6 months to the determined starting point
                new_subscription_end_date_dt = current_subscription_end_dt + six_months_duration
                
                app.logger.info(f"User {auth_user_id} referral reward. Base date for 6m add: {current_subscription_end_dt}. New end date (datetime): {new_subscription_end_date_dt}")

                profile_updates = {
                    'subscription_tier': 'pro', # Upgrade/set to Pro
                    'subscription_valid_till': new_subscription_end_date_dt.date().isoformat(), # 'YYYY-MM-DD'
                    'referral_pro_reward_claimed_at': now_utc_dt.isoformat() 
                }
                auth_metadata_updates = {
                    'subscription_tier': 'pro',
                    'subscription_valid_till': new_subscription_end_date_dt.date().isoformat()
                }

                db_update_response = supabase.table('profiles').update(profile_updates).eq('id', str(auth_user_id)).execute()
                if not (hasattr(db_update_response, 'data') and db_update_response.data):
                    app.logger.error(f"Failed to update profile for referral reward (user: {auth_user_id}). Response: {db_update_response}")
                    raise Exception("Profile database update for reward failed.")
                app.logger.info(f"Successfully updated 'profiles' table for referral reward (user: {auth_user_id}).")

                auth_update_response = supabase.auth.update_user(attributes={'data': auth_metadata_updates})
                if not auth_update_response.user:
                    app.logger.error(f"Failed to update auth user metadata for referral reward (user: {auth_user_id}). Response: {auth_update_response}")
                app.logger.info(f"Successfully updated Supabase Auth user_metadata for referral reward (user: {auth_user_id}).")

                if 'user' in session and session['user']:
                    session['user'].setdefault('user_metadata', {}).update(auth_metadata_updates)
                    if session['user'].get('db_profile'):
                        session['user']['db_profile'].update(profile_updates)
                    else:
                        session['user']['db_profile'] = profile_updates.copy()
                    session.modified = True

                display_data['subscription_tier'] = profile_updates['subscription_tier']
                display_data['valid_till'] = profile_updates['subscription_valid_till']

                flash(f"🎉 Congratulations, {display_data.get('username', 'User')}! You've earned a 6-month DataWarp Pro subscription. Your Pro access is now valid until {display_data['valid_till']}.", "success")
                app.logger.info(f"Referral reward (6 months Pro) granted and stacked for user {auth_user_id}. New subscription validity (date): {profile_updates['subscription_valid_till']}")

            except PostgrestAPIError as e_db:
                app.logger.error(f"Database error applying referral reward to user {auth_user_id}: {e_db.message}", exc_info=True)
                flash("A database error occurred while applying your referral reward. Please contact support.", "danger")
            except AuthApiError as e_auth:
                app.logger.error(f"Auth API error applying referral reward to user {auth_user_id}: {e_auth.message}", exc_info=True)
                flash("An authentication system error occurred while updating your account for the referral reward. Please contact support.", "danger")
            except Exception as e_gen:
                app.logger.error(f"General error applying referral reward to user {auth_user_id}: {e_gen}", exc_info=True)
                flash("An unexpected error occurred while applying your referral reward. Please contact support.", "danger")
    
    elif supabase and not (profile_res and profile_res.data) and request.method == 'GET':
        app.logger.warning(f"[/account GET] Profile data not available for user {auth_user_id}, skipping referral reward check.")

    app.logger.debug(f"[/account GET] Rendering account.html for user {auth_user_id}. Passing referred_users_count = {referred_users_count_for_page}, display_data: {display_data}")
    
    return render_template('account.html',
                           user_profile_data=display_data, 
                           referred_users_count=referred_users_count_for_page,
                           referred_users_list=referred_users_list_for_page)


@app.route('/subscription-plans')
@login_required # Ensure user is logged in to see plans
def subscription_plans():
    user_session_data = get_current_user_from_session()
    current_subscription_tier = "basic" # Default
    if user_session_data and user_session_data.get('user_metadata'):
        current_subscription_tier = user_session_data['user_metadata'].get('subscription_tier', 'basic')
    
    # You might want to pass the plans in a specific order
    ordered_plans = [
        SUBSCRIPTION_PLANS_DATA['pro'],
        SUBSCRIPTION_PLANS_DATA['basic']
    ]

    return render_template('subscription_plans.html',
                           plans=ordered_plans,
                           current_subscription_id=current_subscription_tier)

@app.route('/plan-details/pro')
@login_required # Or remove if you want non-logged-in users to see it
def pro_plan_details():
    plan_data = SUBSCRIPTION_PLANS_DATA.get('pro')
    if not plan_data:
        flash('Pro plan details not found.', 'error')
        return redirect(url_for('subscription_plans')) # Or some other fallback

    # You can add more specific details or transform data here if needed
    # For instance, structuring benefits for the "Summary of benefits" section
    pro_benefits = [
        {
            "icon": "bi-lightning-charge-fill", # Bootstrap Icon
            "title": "Advanced AI Cleaning",
            "description": "Leverage cutting-edge AI for intelligent data cleaning suggestions, anomaly detection, and automated data quality improvements. Reduce manual effort significantly."
        },
        {
            "icon": "bi-diagram-3-fill",
            "title": "Automated Pipelines",
            "description": "Configure and schedule automated data cleaning pipelines. Process new datasets consistently and efficiently without manual intervention."
        },
        {
            "icon": "bi-people-fill",
            "title": "Team Collaboration",
            "description": "Enable up to 5 users to collaborate on data cleaning projects, share configurations, and manage team workflows seamlessly within DataWarp."
        },
        {
            "icon": "bi-headset",
            "title": "Priority Support",
            "description": "Get expedited assistance with priority email and live chat support from our dedicated team of data specialists."
        },
        {
            "icon": "bi-hdd-stack-fill",
            "title": "1TB Project Storage",
            "description": "Ample storage for your datasets, cleaning configurations, and project versions. Keep everything organized and accessible."
        },
        {
            "icon": "bi-stars",
            "title": "Beta Feature Access",
            "description": "Be the first to experience and provide feedback on upcoming DataWarp features and enhancements before they are widely released."
        }
    ]
    plan_data['detailed_benefits'] = pro_benefits


    return render_template('pro_details.html', plan=plan_data)

@app.route('/plan-details/plus')
@login_required # Or remove if you want non-logged-in users to see it
def plus_plan_details():
    plan_data = SUBSCRIPTION_PLANS_DATA.get('plus')
    if not plan_data:
        flash('Plus plan details not found.', 'error')
        return redirect(url_for('subscription_plans'))

    # Define specific detailed benefits for the Plus plan
    plus_benefits = [
        {
            "icon": "bi-tools", # Bootstrap Icon
            "title": "Expanded Cleaning Toolkit",
            "description": "Access a wider array of cleaning tools, including advanced outlier detection (IQR, Z-score), complex data transformations, and value mapping capabilities."
        },
        {
            "icon": "bi-save2-fill",
            "title": "Auto Clean Configurations",
            "description": "Save and load your preferred Auto Clean configurations to apply consistent cleaning steps across multiple datasets with a single click."
        },
        {
            "icon": "bi-binoculars-fill",
            "title": "Deeper Feature Insights",
            "description": "Unlock more detailed feature analysis, including advanced normality tests, correlation matrices (Spearman), and text pattern recognition."
        },
        {
            "icon": "bi-bar-chart-line-fill",
            "title": "Enhanced Visualizations",
            "description": "Gain access to a broader range of plot types and customization options to better understand and present your data."
        },
        {
            "icon": "bi-hdd-fill",
            "title": "100GB Project Storage",
            "description": "Store more of your datasets and project files securely with an increased storage allowance tailored for regular use."
        },
        {
            "icon": "bi-envelope-fill",
            "title": "Standard Email Support",
            "description": "Receive assistance from our support team via email for any questions or issues you encounter while using DataWarp Plus."
        }
    ]
    plan_data['detailed_benefits'] = plus_benefits

    return render_template('plus_details.html', plan=plan_data)



# --- Main Routes ---


@app.route('/signed_out')
def signed_out_page():
    # This page is for users who are explicitly signed out or not yet signed in.
    # If a user somehow lands here while logged in, redirect them to a logged-in page.
    if get_current_user_from_session():
        return redirect(url_for('clean_data_interface')) # Or your main logged-in dashboard/index

    # You can pass any specific data needed for the signed_out.html template here
    return render_template('signed_out.html')

@app.route('/')
def index():
    # If user is not logged in, redirect them to the new signed_out_page
    if not get_current_user_from_session():
        app.logger.debug("User not logged in, redirecting from / to /signed_out")
        return redirect(url_for('signed_out_page'))

    # If user IS logged in, proceed with the normal index page logic
    # This part of the code will only be reached by authenticated users.
    app.logger.debug(f"User {session.get('user', {}).get('email', 'UNKNOWN')} is logged in, serving index.html (upload/saved sessions page).")
    
    saved_files_display_info = []
    saved_sessions_path = app.config.get('SAVED_SESSIONS_FOLDER', 'saved_sessions') # Use .get for safety

    if not os.path.exists(saved_sessions_path):
        app.logger.warning(f"SAVED_SESSIONS_FOLDER '{saved_sessions_path}' does not exist. Creating it.")
        try:
            os.makedirs(saved_sessions_path, exist_ok=True)
        except OSError as e:
            app.logger.error(f"Could not create SAVED_SESSIONS_FOLDER '{saved_sessions_path}': {e}", exc_info=True)
            # Optionally, flash a message to the user if this is critical,
            # but for now, the page will just show no saved files.
            # flash(f"Error accessing saved sessions directory. Please contact support. ({e})", "danger")

    try:
        # List files only if the directory exists
        if os.path.exists(saved_sessions_path):
            raw_saved_files = [
                f for f in os.listdir(saved_sessions_path)
                if os.path.isfile(os.path.join(saved_sessions_path, f)) and f.endswith('.parquet')
            ]
            app.logger.debug(f"Found raw saved Parquet files: {raw_saved_files}")

            for full_filename in raw_saved_files:
                display_name, _ = os.path.splitext(full_filename)
                saved_files_display_info.append({
                    'display': display_name,
                    'full': full_filename
                })
            
            # Sort by display name (filename without extension)
            saved_files_display_info.sort(key=lambda x: x['display'].lower())
            app.logger.debug(f"Processed saved files for display: {saved_files_display_info}")
        else:
            app.logger.info(f"SAVED_SESSIONS_FOLDER '{saved_sessions_path}' still not found after check/creation attempt. No saved files will be listed.")


    except FileNotFoundError: # Should be caught by os.path.exists now, but as a fallback
        app.logger.warning(f"SAVED_SESSIONS_FOLDER '{saved_sessions_path}' was not found when listing files (this should be rare after initial check).")
        pass 
    except Exception as e:
        app.logger.error(f"An unexpected error occurred while listing saved files in index: {e}", exc_info=True)
        flash("An error occurred while trying to load the list of saved sessions.", "warning")
        # Continue to render the page but without the list or with an error message in the list area.

    # This part is for logged-in users, showing upload options, connect DB, and saved files.
    return render_template('index.html', saved_files_info=saved_files_display_info)

def load_data_into_session(df, source_info):
    """Helper to load df into session and redirect."""
    if df is not None:
        clear_session_data() # Start fresh
        store_dataframe_in_session(df)
        session['source_info'] = source_info
        return redirect(url_for('clean_data_interface'))
    else:
        flash('Could not load data.', 'error')
        return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Handles file upload, loads data into session."""
    # (Similar upload logic as before, but use load_data_into_session)
    if 'file' not in request.files:
        flash('No file part', 'error')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'error')
        return redirect(url_for('index'))

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Save temporarily, process, then potentially remove
        # Or read directly from file stream if possible and safe
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(filepath)
            df = None
            file_ext = filename.rsplit('.', 1)[1].lower()
            if file_ext == 'csv':
                 # Try detecting separator, fall back to comma
                 try:
                     df = pd.read_csv(filepath, sep=None, engine='python', on_bad_lines='warn')
                     if df.shape[1] <= 1:
                          df = pd.read_csv(filepath, on_bad_lines='warn')
                 except Exception as read_err:
                      flash(f'Could not automatically determine CSV separator, trying comma. Error: {read_err}', 'warning')
                      df = pd.read_csv(filepath, on_bad_lines='warn')
            elif file_ext == 'tsv':
                df = pd.read_csv(filepath, sep='\t', on_bad_lines='warn')
            elif file_ext == 'xlsx':
                # Consider asking for sheet name if multiple sheets exist
                df = pd.read_excel(filepath)

            os.remove(filepath) # Clean up temporary file
            return load_data_into_session(df, f"{filename}")

        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            if os.path.exists(filepath): # Clean up if error occurred after save
                 try:
                     os.remove(filepath)
                 except OSError: pass # Ignore error if removal fails
            return redirect(url_for('index'))
    else:
        flash('Invalid file type.', 'error')
        return redirect(url_for('index'))


@app.route('/database_form', methods=['GET'])
@login_required
def database_form():
    """Shows the database connection form."""
    return render_template('database_form.html')

@app.route('/database_query', methods=['POST'])
@login_required
def database_query():
    """Connects to DB, loads data into session."""
    # (Similar DB logic as before, but use load_data_into_session)
    db_type = request.form.get('db_type')
    db_host = request.form.get('db_host')
    db_port = request.form.get('db_port')
    db_name = request.form.get('db_name') # For SQLite, this is the file path
    db_user = request.form.get('db_user')
    db_password = request.form.get('db_password')
    query = request.form.get('query')

    if not query:
        flash('SQL Query cannot be empty.', 'error')
        return redirect(url_for('database_form'))

    connection_string = None
    engine = None
    source_info = f"Database: {db_type}"
    df = None

    try:
        # ... (Connection string logic same as before) ...
        if db_type == 'sqlite':
            connection_string = f"sqlite:///{db_name}"
            source_info = f"SQLite: {db_name}"
        elif db_type == 'postgresql':
            connection_string = f"postgresql+psycopg2://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            source_info = f"PostgreSQL: {db_user}@{db_host}:{db_port}/{db_name}"
        elif db_type == 'mysql':
             connection_string = f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
             source_info = f"MySQL: {db_user}@{db_host}:{db_port}/{db_name}"
        else: # Should have validation on form too
             flash('Unsupported database type.', 'error')
             return redirect(url_for('database_form'))

        engine = create_engine(connection_string)
        with engine.connect() as connection:
            df = pd.read_sql(text(query), connection)
        flash('Query successful.', 'success')

    except ImportError as e:
         flash(f"Database driver error: {e}. Make sure the required driver is installed.", "error")
         return redirect(url_for('database_form'))
    except exc.SQLAlchemyError as e:
        flash(f"Database connection or query error: {e}", "error")
        return redirect(url_for('database_form'))
    except Exception as e:
        flash(f"An unexpected error occurred: {str(e)}", "error")
        return redirect(url_for('database_form'))
    finally:
        if engine:
            engine.dispose()

    return load_data_into_session(df, source_info + f" (Query: {query[:50]}...)")


@app.route('/clean')
@login_required
def clean_data_interface():
    """Displays the main data cleaning interface."""
    df = get_dataframe_from_session()
    if df is None:
        flash("No data loaded. Please upload a file or connect to a database.", "warning")
        return redirect(url_for('index'))

    # --- REPLACE THE OLD LOGIC BLOCK WITH THIS ---
    is_premium_user = check_premium_status(get_current_user_from_session())
    # --- END OF REPLACEMENT ---

    table_html, total_rows, total_columns = render_table_html(df)
    columns = df.columns.tolist() if df is not None else []
    source_info = session.get('source_info', 'Unknown Source')
    saved_filename = session.get('saved_filename') 

    return render_template(
        'clean_data.html',
        table_html=table_html,
        columns=columns,
        source_info=source_info,
        undo_redo_status=get_undo_redo_status(),
        saved_filename=saved_filename,
        total_rows=total_rows,
        total_columns=total_columns,
        is_premium_user=is_premium_user
    )


@app.route('/get_valid_columns_for_formula', methods=['GET'])
@login_required
def get_valid_columns_for_formula_route():
    df = get_dataframe_from_session()
    if df is None or df.empty:
        return jsonify({'error': 'No data loaded or data is empty.'}), 400

    formula_name = request.args.get('formula', '').upper()
    valid_columns = []

    if not formula_name:
        return jsonify({'error': 'Formula name not provided.'}), 400

    numeric_non_bool_cols = []
    text_like_cols = []
    datetime_cols = []
    boolean_cols = []
    all_cols = df.columns.tolist()

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col]):
            numeric_non_bool_cols.append(col)
        if pd.api.types.is_object_dtype(df[col]) or \
           pd.api.types.is_string_dtype(df[col]) or \
           pd.api.types.is_categorical_dtype(df[col]):
            text_like_cols.append(col)
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            datetime_cols.append(col)
        if pd.api.types.is_bool_dtype(df[col]):
            boolean_cols.append(col)


    if formula_name in ['SUM', 'AVG', 'MIN', 'MAX', 'STDEV', 'VAR', 'MEDIAN', 
                        'SUMSQ', 'RANGE', 'PERCENTILE', 'IQR', 'SKEW', 'KURT', 'CV']:
        valid_columns = numeric_non_bool_cols
    elif formula_name in ['COUNT', 'COUNTUNIQUE', 'MODE']:
        valid_columns = all_cols
    elif formula_name in ['CONCAT_ROWS', 'LEN_AVG', 'COUNTEMPTY', 'COUNTNONEMPTY',
                        'COUNT_REGEX', 'LONGEST_STR_LEN', 'SHORTEST_STR_LEN']:
        valid_columns = text_like_cols
    elif formula_name in ['DATE_RANGE_DAYS', 'COMMON_YEAR', 'COMMON_MONTH_NAME']:
        valid_columns = datetime_cols
    elif formula_name in ['COUNT_TRUE', 'COUNT_FALSE', 'ALL_TRUE', 'ANY_TRUE']:
        valid_columns = boolean_cols
    else:
        return jsonify({'error': f'Unsupported formula: {formula_name}'}), 400

    return jsonify({'columns': valid_columns})


@app.route('/apply_formula', methods=['POST'])
@login_required
def apply_formula_route():
    df = get_dataframe_from_session()
    if df is None or df.empty:
        return jsonify({'error': 'No data loaded or data is empty.'}), 400

    try:
        data = request.get_json()
        formula = data.get('formula', '').upper()
        column_name = data.get('column_name')
        row_start_1based = data.get('row_start')
        row_end_1based = data.get('row_end')
        parameter = data.get('parameter') # New: get the parameter
    except Exception as e:
        return jsonify({'error': f'Invalid request format: {str(e)}'}), 400

    # ... (rest of the input validation for formula, column_name, row_start, row_end remains the same) ...
    if not formula or not column_name:
        return jsonify({'error': 'Formula and column name are required.'}), 400
    if column_name not in df.columns:
        return jsonify({'error': f'Column "{column_name}" not found.'}), 400

    series_to_calc = df[column_name]
    start_idx = 0 
    end_idx = len(series_to_calc)
    if row_start_1based is not None:
        if not isinstance(row_start_1based, int) or row_start_1based < 1: return jsonify({'error': 'Start row must be a positive integer.'}), 400
        start_idx = row_start_1based - 1
        if start_idx >= len(series_to_calc): return jsonify({'error': 'Start row out of bounds.'}), 400
    if row_end_1based is not None:
        if not isinstance(row_end_1based, int) or row_end_1based < 1: return jsonify({'error': 'End row must be a positive integer.'}), 400
        end_idx = row_end_1based 
        if end_idx > len(series_to_calc): end_idx = len(series_to_calc)
        if row_start_1based is not None and start_idx >= end_idx : return jsonify({'error': 'End row must be after start row.'}), 400
    
    if row_start_1based is not None or row_end_1based is not None:
        series_slice = series_to_calc.iloc[start_idx:end_idx]
    else:
        series_slice = series_to_calc

    if series_slice.empty and formula not in ['COUNT', 'COUNTUNIQUE', 'COUNTEMPTY', 'COUNTNONEMPTY', 'COUNT_TRUE', 'COUNT_FALSE']:
        return jsonify({'result': 'N/A (empty slice)'})

    result = None
    try:
        is_num_col = pd.api.types.is_numeric_dtype(series_slice) and not pd.api.types.is_bool_dtype(series_slice)
        is_text_like_col = pd.api.types.is_object_dtype(series_slice) or \
                           pd.api.types.is_string_dtype(series_slice) or \
                           pd.api.types.is_categorical_dtype(series_slice)
        is_datetime_col = pd.api.types.is_datetime64_any_dtype(series_slice)
        is_bool_col = pd.api.types.is_bool_dtype(series_slice)

        # --- Existing Formulas ---
        if formula == 'SUM':
            if not is_num_col: return jsonify({'error': 'SUM: Numeric non-boolean column required.'}), 400
            result = series_slice.sum()
        elif formula == 'COUNT':
            result = series_slice.count()
        elif formula == 'AVG':
            if not is_num_col: return jsonify({'error': 'AVG: Numeric non-boolean column required.'}), 400
            result = series_slice.mean()
        elif formula == 'MEDIAN':
            if not is_num_col: return jsonify({'error': 'MEDIAN: Numeric non-boolean column required.'}), 400
            result = series_slice.median()
        elif formula == 'MIN':
            if series_slice.dropna().empty: result = pd.NA
            elif not (is_num_col or is_datetime_col or is_text_like_col): return jsonify({'error': 'MIN: Numeric, datetime or text-like column required.'}), 400
            result = series_slice.min()
        elif formula == 'MAX':
            if series_slice.dropna().empty: result = pd.NA
            elif not (is_num_col or is_datetime_col or is_text_like_col): return jsonify({'error': 'MAX: Numeric, datetime or text-like column required.'}), 400
            result = series_slice.max()
        elif formula == 'STDEV':
            if not is_num_col: return jsonify({'error': 'STDEV: Numeric non-boolean column required.'}), 400
            result = series_slice.std()
        elif formula == 'VAR':
            if not is_num_col: return jsonify({'error': 'VAR: Numeric non-boolean column required.'}), 400
            result = series_slice.var()
        elif formula == 'SUMSQ':
            if not is_num_col: return jsonify({'error': 'SUMSQ: Numeric non-boolean column required.'}), 400
            result = (series_slice.dropna() ** 2).sum()
        elif formula == 'RANGE':
            if not is_num_col: return jsonify({'error': 'RANGE: Numeric non-boolean column required.'}), 400
            if series_slice.dropna().empty: result = pd.NA
            else: result = series_slice.max() - series_slice.min()
        elif formula == 'COUNTUNIQUE':
            result = series_slice.nunique()
        elif formula == 'MODE':
            modes = series_slice.mode()
            if modes.empty: result = pd.NA
            else: result = ", ".join(modes.astype(str).tolist()) if len(modes) > 1 else modes.iloc[0]
        elif formula == 'CONCAT_ROWS':
            if not is_text_like_col and not series_slice.empty : return jsonify({'error': 'CONCAT_ROWS: Text-like column required.'}), 400
            if series_slice.empty: result = ""
            else: result = series_slice.astype(str).str.cat(sep=' ')
        elif formula == 'LEN_AVG':
            if not is_text_like_col and not series_slice.empty: return jsonify({'error': 'LEN_AVG: Text-like column required.'}), 400
            if series_slice.empty: result = pd.NA
            else: result = series_slice.astype(str).str.len().mean()
        elif formula == 'COUNTEMPTY':
            if not is_text_like_col and not series_slice.empty: return jsonify({'error': 'COUNTEMPTY: Text-like column required.'}), 400
            if series_slice.empty: result = 0
            else: result = (series_slice.astype(str).str.strip() == '').sum()
        elif formula == 'COUNTNONEMPTY':
            if not is_text_like_col and not series_slice.empty: return jsonify({'error': 'COUNTNONEMPTY: Text-like column required.'}), 400
            if series_slice.empty: result = 0
            else: result = (series_slice.astype(str).str.strip() != '').sum()
        
        # --- New Formulas ---
        elif formula == 'PERCENTILE':
            if not is_num_col: return jsonify({'error': 'PERCENTILE: Numeric non-boolean column required.'}), 400
            if parameter is None: return jsonify({'error': 'PERCENTILE: P value (0-100) parameter is required.'}), 400
            try:
                p_val = float(parameter)
                if not (0 <= p_val <= 100): return jsonify({'error': 'PERCENTILE: P value must be between 0 and 100.'}), 400
                result = series_slice.quantile(p_val / 100.0)
            except ValueError: return jsonify({'error': 'PERCENTILE: Invalid P value.'}), 400
        elif formula == 'IQR':
            if not is_num_col: return jsonify({'error': 'IQR: Numeric non-boolean column required.'}), 400
            if series_slice.dropna().empty or len(series_slice.dropna()) < 2 : result = pd.NA # IQR not well-defined for <2 points
            else: result = series_slice.quantile(0.75) - series_slice.quantile(0.25)
        elif formula == 'SKEW':
            if not is_num_col: return jsonify({'error': 'SKEW: Numeric non-boolean column required.'}), 400
            result = series_slice.skew()
        elif formula == 'KURT': # Kurtosis
            if not is_num_col: return jsonify({'error': 'KURT: Numeric non-boolean column required.'}), 400
            result = series_slice.kurt()
        elif formula == 'CV': # Coefficient of Variation
            if not is_num_col: return jsonify({'error': 'CV: Numeric non-boolean column required.'}), 400
            mean_val = series_slice.mean()
            std_val = series_slice.std()
            if pd.isna(mean_val) or pd.isna(std_val) or mean_val == 0: result = pd.NA # Avoid division by zero or NaN result
            else: result = std_val / mean_val
        elif formula == 'DATE_RANGE_DAYS':
            if not is_datetime_col: return jsonify({'error': 'DATE_RANGE_DAYS: Datetime column required.'}), 400
            if series_slice.dropna().empty or len(series_slice.dropna()) < 2: result = pd.NA
            else: result = (series_slice.max() - series_slice.min()).days
        elif formula == 'COMMON_YEAR':
            if not is_datetime_col: return jsonify({'error': 'COMMON_YEAR: Datetime column required.'}), 400
            if series_slice.dropna().empty: result = pd.NA
            else: modes = series_slice.dt.year.mode(); result = modes.iloc[0] if not modes.empty else pd.NA
        elif formula == 'COMMON_MONTH_NAME':
            if not is_datetime_col: return jsonify({'error': 'COMMON_MONTH_NAME: Datetime column required.'}), 400
            if series_slice.dropna().empty: result = pd.NA
            else: modes = series_slice.dt.month_name().mode(); result = modes.iloc[0] if not modes.empty else pd.NA
        elif formula == 'COUNT_REGEX':
            if not is_text_like_col and not series_slice.empty: return jsonify({'error': 'COUNT_REGEX: Text-like column required.'}), 400
            if parameter is None or not isinstance(parameter, str) or parameter.strip() == '':
                return jsonify({'error': 'COUNT_REGEX: Regex pattern parameter is required.'}), 400
            try:
                re.compile(parameter) # Validate regex
                if series_slice.empty: result = 0
                else: result = series_slice.astype(str).str.contains(parameter, regex=True, na=False).sum()
            except re.error: return jsonify({'error': 'COUNT_REGEX: Invalid regex pattern.'}), 400
        elif formula == 'LONGEST_STR_LEN':
            if not is_text_like_col and not series_slice.empty: return jsonify({'error': 'LONGEST_STR_LEN: Text-like column required.'}), 400
            if series_slice.dropna().empty: result = pd.NA
            else: result = series_slice.astype(str).str.len().max()
        elif formula == 'SHORTEST_STR_LEN': # Shortest non-empty string length
            if not is_text_like_col and not series_slice.empty: return jsonify({'error': 'SHORTEST_STR_LEN: Text-like column required.'}), 400
            non_empty_strings = series_slice.astype(str).str.strip()
            non_empty_strings = non_empty_strings[non_empty_strings != '']
            if non_empty_strings.empty: result = pd.NA
            else: result = non_empty_strings.str.len().min()
        elif formula == 'COUNT_TRUE':
            if not is_bool_col: return jsonify({'error': 'COUNT_TRUE: Boolean column required.'}), 400
            result = (series_slice == True).sum() # More explicit for boolean type
        elif formula == 'COUNT_FALSE':
            if not is_bool_col: return jsonify({'error': 'COUNT_FALSE: Boolean column required.'}), 400
            result = (series_slice == False).sum()
        elif formula == 'ALL_TRUE':
            if not is_bool_col: return jsonify({'error': 'ALL_TRUE: Boolean column required.'}), 400
            if series_slice.empty: result = False # Or pd.NA, depending on desired logic for empty
            else: result = series_slice.all()
        elif formula == 'ANY_TRUE':
            if not is_bool_col: return jsonify({'error': 'ANY_TRUE: Boolean column required.'}), 400
            if series_slice.empty: result = False
            else: result = series_slice.any()
        else:
            return jsonify({'error': f'Unsupported formula: {formula}'}), 400

        # --- Formatting the result (same as before) ---
        if pd.isna(result):
            result_display = "N/A"
        elif isinstance(result, (float, np.floating)):
            if abs(result) > 1e-4 or result == 0:
                if not math.isinf(result) and result == int(result): result_display = f"{int(result)}"
                else: result_display = f"{result:.4g}"
            else: result_display = f"{result:.4e}"
        elif isinstance(result, pd.Timestamp):
            result_display = result.isoformat()
        elif isinstance(result, (bool, np.bool_)): # Explicitly handle boolean results
            result_display = str(result)
        else:
            result_display = str(result)
        
        if isinstance(result_display, str) and len(result_display) > 100 and formula == 'CONCAT_ROWS':
            result_display = result_display[:100] + "..."

        return jsonify({'result': result_display})

    except TypeError as te:
        app.logger.warning(f"TypeError during formula '{formula}' on column '{column_name}' (slice type: {series_slice.dtype}): {te}", exc_info=True)
        return jsonify({'error': f'Type error for {formula}. Check column type/slice. Error: {str(te)}'}), 400
    except Exception as e_calc:
        app.logger.error(f"Error applying formula '{formula}' on col '{column_name}': {e_calc}", exc_info=True)
        return jsonify({'error': f'Calculation error: {str(e_calc)}'}), 500



# --- AJAX Endpoints for Cleaning Operations ---

@app.route('/clean_operation', methods=['POST'])
@login_required
def handle_clean_operation():
    """
    Generic handler for cleaning operations triggered by AJAX.
    Retrieves data from session, performs operation, updates session,
    and returns JSON response for the frontend.
    """
    # 1. Get the current DataFrame from session
    df = get_dataframe_from_session()
    if df is None:
        # Return error if no data is loaded in the session
        return jsonify({'error': 'No data loaded in session. Please load data first.'}), 400

    # 2. Get operation details from the JSON request body
    try:
        request_data = request.get_json()
        if not request_data:
            return jsonify({'error': 'Invalid request format. JSON body expected.'}), 400
        operation = request_data.get('operation')
        params = request_data.get('params', {})
        if not operation:
             return jsonify({'error': 'Missing "operation" in request.'}), 400
    except Exception as e:
        app.logger.error(f"Error parsing request JSON: {e}")
        return jsonify({'error': f'Error parsing request: {str(e)}'}), 400

    # 3. Store current state for Undo BEFORE modifying the DataFrame
    current_df_json = session.get('current_df_json') # Get the JSON string directly
    # Ensure add_to_undo handles the case where current_df_json might be None initially,
    # though we check for df existence earlier.
    add_to_undo(current_df_json) # This helper should also clear the redo history

    # 4. Perform the requested cleaning operation
    try:
        original_shape = df.shape
        action_msg = "" # To store the success message

        # --- Apply the requested operation ---
        if operation == 'remove_duplicates':
            subset = params.get('subset') # Optional: list of columns, None means all
            # Ensure subset columns exist if provided (basic check)
            if subset and not all(col in df.columns for col in subset):
                 return jsonify({'error': 'One or more subset columns not found.'}), 400
            df_new = df.drop_duplicates(subset=subset, keep='first')
            removed_count = original_shape[0] - df_new.shape[0]
            action_msg = f"Removed {removed_count} duplicate row(s)."
            df = df_new # Assign the result back to df

        elif operation == 'remove_missing':
            how = params.get('how', 'any') # 'any' or 'all'
            subset = params.get('subset') # Optional: list of columns
            if how not in ['any', 'all']:
                 return jsonify({'error': 'Invalid value for "how". Must be "any" or "all".'}), 400
            if subset and not all(col in df.columns for col in subset):
                 return jsonify({'error': 'One or more subset columns not found.'}), 400
            df_new = df.dropna(axis=0, how=how, subset=subset) # axis=0 for rows
            removed_count = original_shape[0] - df_new.shape[0]
            action_msg = f"Removed {removed_count} row(s) containing missing values."
            df = df_new

        elif operation == 'fill_missing':
            # Get parameters: method, column (optional), value (optional)
            method = params.get('method', 'value') # 'value', 'mean', 'median', 'mode', 'ffill', 'bfill'
            column = params.get('column') # Optional: specific column name
            fill_value_str = params.get('value') # Value provided by user (only used if method='value')

            allowed_methods = ['value', 'mean', 'median', 'mode', 'ffill', 'bfill']
            if method not in allowed_methods:
                 return jsonify({'error': f'Invalid fill method "{method}". Allowed methods: {allowed_methods}'}), 400

            # --- Method: Fill with a specific VALUE ---
            if method == 'value':
                if fill_value_str is None: # Value is required for this method
                    return jsonify({'error': 'A fill value must be provided when method is "value".'}), 400

                if column: # Fill specific column with value
                    if column not in df.columns:
                        return jsonify({'error': f'Column "{column}" not found'}), 400

                    # Attempt type conversion of fill_value_str to match column type
                    fill_value = fill_value_str # Default to string
                    warning_msg = ""
                    try:
                        col_dtype = df[column].dtype
                        if pd.api.types.is_numeric_dtype(col_dtype):
                            fill_value = pd.to_numeric(fill_value_str) if fill_value_str != '' else pd.NA
                        elif pd.api.types.is_datetime64_any_dtype(col_dtype):
                            fill_value = pd.to_datetime(fill_value_str) if fill_value_str != '' else pd.NaT
                        elif pd.api.types.is_bool_dtype(col_dtype):
                              lowered_val = fill_value_str.lower()
                              if lowered_val in ['true', '1', 'yes']: fill_value = True
                              elif lowered_val in ['false', '0', 'no']: fill_value = False
                              elif lowered_val == '': fill_value = pd.NA
                              else: raise ValueError("Invalid boolean value")
                        # else: keep as string
                    except (ValueError, TypeError) as conv_err:
                         warning_msg = f" (Warning: Could not convert '{fill_value_str}' to column type, used as string)."
                         fill_value = fill_value_str # Fallback to string

                    df[column].fillna(fill_value, inplace=True) # Use inplace for single column efficiency
                    action_msg = f"Filled missing values in column '{column}' with value '{fill_value_str}'." + warning_msg

                else: # Fill ALL columns with the same value
                    # Simple approach: fill all with the same string value.
                    # A more complex approach could try type conversion per column, but adds complexity.
                    df.fillna(fill_value_str, inplace=True)
                    action_msg = f"Filled missing values in all columns with value '{fill_value_str}'."

            # --- Method: Fill with Mean, Median, or Mode ---
            elif method in ['mean', 'median', 'mode']:
                if column: # Fill specific column with statistic
                    if column not in df.columns:
                        return jsonify({'error': f'Column "{column}" not found'}), 400
                    if not pd.api.types.is_numeric_dtype(df[column]):
                         # Mode could potentially apply to non-numeric, but let's restrict for simplicity now
                         return jsonify({'error': f'Method "{method}" can only be applied to numeric columns.'}), 400
                    if df[column].isnull().all(): # Cannot calculate statistic if all null
                         action_msg = f"Skipped: Cannot calculate {method} for column '{column}' as all values are missing."
                    else:
                        fill_stat = None
                        if method == 'mean':
                            fill_stat = df[column].mean()
                        elif method == 'median':
                            fill_stat = df[column].median()
                        elif method == 'mode':
                            mode_result = df[column].mode()
                            if not mode_result.empty:
                                fill_stat = mode_result[0] # Take the first mode if multiple exist
                            else: # Should not happen if not all null, but safety check
                                 action_msg = f"Skipped: Could not determine mode for column '{column}'."
                                 fill_stat = None # Ensure fill doesn't happen

                        if fill_stat is not None:
                             df[column].fillna(fill_stat, inplace=True)
                             action_msg = f"Filled missing values in numeric column '{column}' with its {method} ({fill_stat:.4g})." # Format stat

                else: # Fill ALL applicable (numeric) columns with their respective statistic
                    filled_cols = []
                    skipped_cols = []
                    for col_loop in df.columns:
                        if pd.api.types.is_numeric_dtype(df[col_loop]) and not df[col_loop].isnull().all():
                            fill_stat = None
                            try:
                                if method == 'mean': fill_stat = df[col_loop].mean()
                                elif method == 'median': fill_stat = df[col_loop].median()
                                elif method == 'mode':
                                     mode_result = df[col_loop].mode()
                                     if not mode_result.empty: fill_stat = mode_result[0]
                            except Exception as e:
                                 app.logger.warning(f"Could not calculate {method} for {col_loop}: {e}")

                            if fill_stat is not None:
                                 df[col_loop].fillna(fill_stat, inplace=True)
                                 filled_cols.append(f"{col_loop} ({fill_stat:.4g})")
                            else:
                                 skipped_cols.append(col_loop + " (calc error)")
                        else:
                            skipped_cols.append(col_loop + " (not numeric/all null)")

                    if filled_cols:
                         action_msg = f"Filled missing values in numeric columns with their respective {method}: {'; '.join(filled_cols)}."
                         if skipped_cols:
                             action_msg += f" Skipped: {', '.join(skipped_cols)}."
                    else:
                         action_msg = f"No numeric columns found/filled using {method} method."

            # --- Method: Forward Fill (ffill) or Backward Fill (bfill) ---
            elif method in ['ffill', 'bfill']:
                if column: # Fill specific column
                    if column not in df.columns:
                        return jsonify({'error': f'Column "{column}" not found'}), 400
                    df[column].fillna(method=method, inplace=True)
                    action_msg = f"Applied {method} (propagate last/next valid value) to column '{column}'."
                else: # Fill ALL columns
                    df.fillna(method=method, inplace=True) # Fills across entire DataFrame
                    action_msg = f"Applied {method} (propagate last/next valid value) across all columns."
            else:
                 # This case should be caught by the initial method validation
                 return jsonify({'error': 'Unknown fill method encountered.'}), 500

        elif operation == 'remove_spaces':
             column = params.get('column')
             if not column:
                  return jsonify({'error': 'Column parameter is required for removing spaces.'}), 400
             if column not in df.columns:
                  return jsonify({'error': f'Column "{column}" not found'}), 400

             # Only apply to object/string columns
             if pd.api.types.is_object_dtype(df[column]) or pd.api.types.is_string_dtype(df[column]):
                 # Ensure column is treated as string, then strip
                 df[column] = df[column].astype(str).str.strip()
                 action_msg = f"Removed leading/trailing spaces from column '{column}'."
             else:
                  action_msg = f"Operation skipped: Remove spaces only applicable to text columns (column '{column}' is not text)."
                  # Don't return error, just inform user maybe? Or return 400?
                  # return jsonify({'error': f'Remove spaces only applicable to text columns (column "{column}" is not text)'}), 400


        elif operation == 'fix_datetime':
             column = params.get('column')
             date_format = params.get('format') # Optional format string (e.g., '%Y-%m-%d')
             if not column:
                  return jsonify({'error': 'Column parameter is required for fixing dates.'}), 400
             if column not in df.columns:
                  return jsonify({'error': f'Column "{column}" not found'}), 400

             # errors='coerce' will turn unparseable dates into NaT (Not a Time/Null)
             original_nulls = df[column].isnull().sum()
             df[column] = pd.to_datetime(df[column], format=date_format, errors='coerce')
             new_nulls = df[column].isnull().sum()
             coerced_count = new_nulls - original_nulls

             action_msg = f"Converted column '{column}' to datetime type."
             if coerced_count > 0:
                 action_msg += f" {coerced_count} value(s) could not be parsed and were set to null."
        

        # === Check IDs ===
        elif operation == 'check_id_uniqueness':
            df_modified = False # This operation doesn't change the DataFrame
            column = params.get('column')
            if not column:
                 return jsonify({'error': 'Column parameter is required.'}), 400
            if column not in df.columns:
                 return jsonify({'error': f'Column "{column}" not found'}), 400

            if df[column].is_unique:
                action_msg = f"Column '{column}' contains unique values."
            else:
                duplicates = df[df[column].duplicated()][column].unique()
                dup_count = df[column].duplicated().sum()
                preview = duplicates[:5].tolist() # Show first 5 duplicates
                action_msg = f"Column '{column}' contains {dup_count} duplicate value(s). Examples: {preview}"

        elif operation == 'check_id_format':
            df_modified = False # This operation doesn't change the DataFrame
            column = params.get('column')
            pattern = params.get('pattern')
            if not column:
                 return jsonify({'error': 'Column parameter is required.'}), 400
            if column not in df.columns:
                 return jsonify({'error': f'Column "{column}" not found'}), 400
            if not pattern:
                 return jsonify({'error': 'Pattern parameter is required for format check.'}), 400

            try:
                # Attempt to compile regex to check validity early
                re.compile(pattern)
                # Use na=False to treat NaN as non-matching
                matches = df[column].astype(str).str.match(f'^{pattern}$', na=False) # Anchor pattern
                non_matching_count = (~matches).sum()
                if non_matching_count == 0:
                    action_msg = f"All values in column '{column}' match the pattern."
                else:
                    action_msg = f"Checked format for column '{column}'. {non_matching_count} value(s) did not match the pattern '{pattern}'."
            except re.error as e:
                 return jsonify({'error': f'Invalid regex pattern provided: {e}'}), 400
            except Exception as e:
                 return jsonify({'error': f'Error during format check: {e}'}), 500


        # === Correcting Numerical Outliers (Updated Section) ===
        elif operation == 'remove_outliers_iqr':
            column = params.get('column')
            factor = params.get('factor', 1.5)
            # --- Validation ---
            if not column: return jsonify({'error': 'Column parameter is required.'}), 400
            if column not in df.columns: return jsonify({'error': f'Column "{column}" not found.'}), 400
            if not pd.api.types.is_numeric_dtype(df[column]): return jsonify({'error': f'Column "{column}" must be numeric for IQR.'}), 400
            try:
                 factor = float(factor)
                 if factor <= 0: raise ValueError("Factor must be positive.")
            except (ValueError, TypeError): return jsonify({'error': 'Invalid IQR factor.'}), 400

            # --- Calculation & Removal ---
            col_data_nonan = df[column].dropna()
            if len(col_data_nonan) < 4: # Not enough data for meaningful IQR
                 action_msg = f"Skipped IQR outlier removal for '{column}' (too few non-NA values)."
            else:
                Q1 = col_data_nonan.quantile(0.25)
                Q3 = col_data_nonan.quantile(0.75)
                IQR = Q3 - Q1
                if IQR >= 0: # Allow IQR to be 0
                    lower_bound = Q1 - factor * IQR
                    upper_bound = Q3 + factor * IQR
                    # Create a boolean mask for rows to keep (non-outliers)
                    # Important: Apply mask to original df's index to handle NaNs correctly if any
                    mask_to_keep = (df[column] >= lower_bound) & (df[column] <= upper_bound)
                    mask_to_keep = mask_to_keep | df[column].isnull() # Keep rows with NaNs in this column
                    
                    df_new = df[mask_to_keep].reset_index(drop=True) # This removes rows globally
                    removed_count = original_shape[0] - df_new.shape[0]
                    action_msg = f"Removed {removed_count} row(s) with outliers from column '{column}' using IQR (factor={factor}). Bounds: [{lower_bound:.2f}, {upper_bound:.2f}]."
                    df = df_new # Update the main DataFrame
                else:
                    action_msg = f"Skipped IQR outlier removal for '{column}' (Invalid IQR calculation)."


        elif operation == 'clip_outliers_iqr':
            column = params.get('column')
            factor = params.get('factor', 1.5)
            # --- Validation (same as remove_outliers_iqr) ---
            if not column: return jsonify({'error': 'Column required.'}), 400
            if column not in df.columns: return jsonify({'error': f'Column "{column}" not found.'}), 400
            if not pd.api.types.is_numeric_dtype(df[column]): return jsonify({'error': f'Column "{column}" must be numeric.'}), 400
            try: factor = float(factor); assert factor > 0
            except: return jsonify({'error': 'Invalid IQR factor.'}), 400

            # --- Calculation & Clipping ---
            col_data_nonan = df[column].dropna()
            if len(col_data_nonan) < 4:
                action_msg = f"Skipped IQR clipping for '{column}' (too few non-NA values)."
            else:
                Q1 = col_data_nonan.quantile(0.25)
                Q3 = col_data_nonan.quantile(0.75)
                IQR = Q3 - Q1
                if IQR >= 0:
                    lower_bound = Q1 - factor * IQR
                    upper_bound = Q3 + factor * IQR
                    original_values = df[column].copy() # To count how many were clipped
                    # Clip operates on the Series and returns a new one
                    df[column] = df[column].clip(lower=lower_bound, upper=upper_bound)
                    df_modified_in_place = True # Mark that df was modified directly
                    clipped_count = (original_values != df[column]).sum() # Count where values changed
                    action_msg = f"Clipped {clipped_count} outlier(s) in column '{column}' using IQR (factor={factor}). Bounds: [{lower_bound:.2f}, {upper_bound:.2f}]."
                else:
                     action_msg = f"Skipped IQR clipping for '{column}' (Invalid IQR calculation)."

        # ***** NEW: Z-score Based Outlier Handling *****
        elif operation == 'remove_outliers_zscore':
            column = params.get('column')
            threshold = params.get('threshold', 3.0) # Default Z-score threshold
            # --- Validation ---
            if not column: return jsonify({'error': 'Column parameter is required.'}), 400
            if column not in df.columns: return jsonify({'error': f'Column "{column}" not found.'}), 400
            if not pd.api.types.is_numeric_dtype(df[column]): return jsonify({'error': f'Column "{column}" must be numeric for Z-score.'}), 400
            try:
                 threshold = float(threshold)
                 if threshold <= 0: raise ValueError("Threshold must be positive.")
            except (ValueError, TypeError): return jsonify({'error': 'Invalid Z-score threshold.'}), 400

            # --- Calculation & Removal ---
            col_data_nonan = df[column].dropna()
            if len(col_data_nonan) < 2 or col_data_nonan.std(ddof=0) < 1e-9 : # Need std > 0 and at least 2 points
                action_msg = f"Skipped Z-score outlier removal for '{column}' (std is zero or too few non-NA values)."
            else:
                # Calculate Z-scores only for non-NaN values
                z_scores_nonan = np.abs((col_data_nonan - col_data_nonan.mean()) / col_data_nonan.std(ddof=0))
                # Create a boolean mask for rows to keep (non-outliers based on Z-score)
                # Start with all False, then mark non-outliers as True
                mask_to_keep = pd.Series(False, index=df.index)
                mask_to_keep.loc[col_data_nonan[z_scores_nonan <= threshold].index] = True
                mask_to_keep = mask_to_keep | df[column].isnull() # Also keep rows that were originally NaN

                df_new = df[mask_to_keep].reset_index(drop=True)
                removed_count = original_shape[0] - df_new.shape[0]
                action_msg = f"Removed {removed_count} row(s) with Z-score outliers from column '{column}' (threshold={threshold})."
                df = df_new # Update the main DataFrame

        elif operation == 'clip_outliers_zscore':
            column = params.get('column')
            threshold = params.get('threshold', 3.0)
            # --- Validation (same as remove_outliers_zscore) ---
            if not column: return jsonify({'error': 'Column required.'}), 400
            if column not in df.columns: return jsonify({'error': f'Column "{column}" not found.'}), 400
            if not pd.api.types.is_numeric_dtype(df[column]): return jsonify({'error': f'Column "{column}" must be numeric.'}), 400
            try: threshold = float(threshold); assert threshold > 0
            except: return jsonify({'error': 'Invalid Z-score threshold.'}), 400

            # --- Calculation & Clipping ---
            col_data_nonan = df[column].dropna()
            if len(col_data_nonan) < 2 or col_data_nonan.std(ddof=0) < 1e-9:
                action_msg = f"Skipped Z-score clipping for '{column}' (std is zero or too few non-NA values)."
            else:
                mean_val = col_data_nonan.mean() # Use non-NA mean for bounds
                std_val = col_data_nonan.std(ddof=0)  # Use non-NA std for bounds
                
                lower_bound_z = mean_val - threshold * std_val
                upper_bound_z = mean_val + threshold * std_val

                original_values = df[column].copy()
                df[column] = df[column].clip(lower=lower_bound_z, upper=upper_bound_z)
                df_modified_in_place = True
                clipped_count = (original_values != df[column]).sum()
                action_msg = f"Clipped {clipped_count} outlier(s) in column '{column}' using Z-score (threshold={threshold}). Bounds: [{lower_bound_z:.2f}, {upper_bound_z:.2f}]."

        # === Define Valid Output (Filtering) ===
        elif operation == 'filter_rows':
            column = params.get('column')
            condition = params.get('condition')
            value_str = params.get('value') # Value might not be needed for isnull/notnull
            filter_action = params.get('action', 'keep') # 'keep' or 'remove'

            if not column: return jsonify({'error': 'Column parameter is required.'}), 400
            if column not in df.columns: return jsonify({'error': f'Column "{column}" not found'}), 400
            if not condition: return jsonify({'error': 'Condition parameter is required.'}), 400
            if filter_action not in ['keep', 'remove']: return jsonify({'error': 'Invalid action. Must be "keep" or "remove".'}), 400

            valid_conditions = ['==', '!=', '>', '<', '>=', '<=', 'contains', 'startswith', 'endswith', 'isnull', 'notnull']
            if condition not in valid_conditions:
                 return jsonify({'error': f'Invalid condition "{condition}". Valid conditions are: {valid_conditions}'}), 400

            # Handle conditions that don't need a value
            if condition in ['isnull', 'notnull']:
                mask = df[column].isnull() if condition == 'isnull' else df[column].notnull()
                value_display = "" # No value to display
            else:
                # Conditions requiring a value
                if value_str is None: # Check if value was provided
                     return jsonify({'error': f'Value parameter is required for condition "{condition}".'}), 400

                value_display = f"'{value_str}'" # For message
                target_value = value_str # Default to string

                # Attempt type conversion based on column dtype for comparison
                col_dtype = df[column].dtype
                try:
                     if pd.api.types.is_numeric_dtype(col_dtype):
                          target_value = pd.to_numeric(value_str)
                          value_display = str(target_value)
                     elif pd.api.types.is_datetime64_any_dtype(col_dtype):
                          target_value = pd.to_datetime(value_str)
                          value_display = str(target_value)
                     elif pd.api.types.is_bool_dtype(col_dtype):
                           lowered_val = value_str.lower()
                           if lowered_val in ['true', '1', 'yes']: target_value = True
                           elif lowered_val in ['false', '0', 'no']: target_value = False
                           else: raise ValueError("Invalid boolean value")
                           value_display = str(target_value)
                     # Else: Keep as string (already assigned) for string operations
                except (ValueError, TypeError) as conv_err:
                     # If conversion fails for numeric/datetime/bool, return error as comparison likely invalid
                      return jsonify({'error': f'Could not convert value "{value_str}" to match type of column "{column}". Error: {conv_err}'}), 400

                # Build mask based on condition
                if condition == '==': mask = (df[column] == target_value)
                elif condition == '!=': mask = (df[column] != target_value)
                elif condition == '>': mask = (df[column] > target_value)
                elif condition == '<': mask = (df[column] < target_value)
                elif condition == '>=': mask = (df[column] >= target_value)
                elif condition == '<=': mask = (df[column] <= target_value)
                # String conditions (apply only if target_value is string, maybe check col type too?)
                elif condition == 'contains':
                    if not isinstance(target_value, str): return jsonify({'error': 'Contains condition requires a string value.'}), 400
                    mask = df[column].astype(str).str.contains(target_value, na=False)
                elif condition == 'startswith':
                    if not isinstance(target_value, str): return jsonify({'error': 'Startswith condition requires a string value.'}), 400
                    mask = df[column].astype(str).str.startswith(target_value, na=False)
                elif condition == 'endswith':
                    if not isinstance(target_value, str): return jsonify({'error': 'Endswith condition requires a string value.'}), 400
                    mask = df[column].astype(str).str.endswith(target_value, na=False)

            # Apply filter
            if filter_action == 'keep':
                df_new = df[mask].reset_index(drop=True)
                kept_removed_count = df_new.shape[0]
                action_word = "Kept"
            else: # remove
                df_new = df[~mask].reset_index(drop=True)
                kept_removed_count = original_shape[0] - df_new.shape[0]
                action_word = "Removed"

            action_msg = f"{action_word} {kept_removed_count} row(s) where '{column}' {condition} {value_display}."
            df = df_new


        # === Transforming and Rearranging ===
        elif operation == 'split_column':
            column = params.get('column')
            delimiter = params.get('delimiter')
            new_column_names_str = params.get('new_column_names') # Expect comma-separated string from UI

            if not column: return jsonify({'error': 'Column parameter is required.'}), 400
            if column not in df.columns: return jsonify({'error': f'Column "{column}" not found'}), 400
            if not delimiter: return jsonify({'error': 'Delimiter parameter is required.'}), 400
            if not (pd.api.types.is_object_dtype(df[column]) or pd.api.types.is_string_dtype(df[column])):
                 return jsonify({'error': 'Split column operation only applicable to text columns.'}), 400

            try:
                # Perform the split
                split_data = df[column].astype(str).str.split(delimiter, expand=True)
                num_new_cols = split_data.shape[1]

                # Determine new column names
                if new_column_names_str:
                    new_names = [name.strip() for name in new_column_names_str.split(',') if name.strip()]
                    if len(new_names) != num_new_cols:
                        return jsonify({'error': f'Provided {len(new_names)} new column names, but split resulted in {num_new_cols} columns.'}), 400
                else:
                    # Generate default names
                    new_names = [f"{column}_split_{i+1}" for i in range(num_new_cols)]

                # Check if new names conflict with existing ones (excluding original column)
                existing_cols = set(df.columns) - {column}
                conflicts = set(new_names) & existing_cols
                if conflicts:
                     return jsonify({'error': f'New column names conflict with existing columns: {list(conflicts)}'}), 400

                # Add new columns to the DataFrame
                df[new_names] = split_data
                action_msg = f"Split column '{column}' into {num_new_cols} new column(s): {', '.join(new_names)}."
                # Optional: Add parameter to drop original column `df = df.drop(columns=[column])`
            except Exception as e:
                return jsonify({'error': f'Error during split operation: {e}'}), 500

        elif operation == 'combine_columns':
            columns_to_combine = params.get('columns_to_combine') # Expect list
            new_column_name = params.get('new_column_name')
            separator = params.get('separator', '') # Default to empty string

            if not columns_to_combine or not isinstance(columns_to_combine, list) or len(columns_to_combine) < 2:
                 return jsonify({'error': 'Requires a list of at least two columns to combine.'}), 400
            if not new_column_name:
                 return jsonify({'error': 'New column name parameter is required.'}), 400
            if not all(col in df.columns for col in columns_to_combine):
                 missing = [col for col in columns_to_combine if col not in df.columns]
                 return jsonify({'error': f'Columns not found: {missing}'}), 400
            if new_column_name in df.columns:
                 # Optional: Allow overwrite? For now, prevent it.
                 return jsonify({'error': f'New column name "{new_column_name}" already exists.'}), 400

            try:
                # Convert all columns to string and join
                df[new_column_name] = df[columns_to_combine].astype(str).agg(separator.join, axis=1)
                action_msg = f"Combined columns {columns_to_combine} into '{new_column_name}' using separator '{separator}'."
                # Optional: Add parameter to drop original columns `df = df.drop(columns=columns_to_combine)`
            except Exception as e:
                return jsonify({'error': f'Error during combine operation: {e}'}), 500

        # === Other Common Operations ===

        elif operation == 'change_dtype':
            column = params.get('column')
            target_type = params.get('target_type')
            if not column: return jsonify({'error': 'Column parameter is required.'}), 400
            if column not in df.columns: return jsonify({'error': f'Column "{column}" not found'}), 400
            if not target_type: return jsonify({'error': 'Target type parameter is required.'}), 400

            original_nulls = df[column].isnull().sum()
            coerced_count = 0
            try:
                if target_type in ['int', 'integer']:
                    # Use Int64 for nullable integers
                    df[column] = pd.to_numeric(df[column], errors='coerce').astype('Int64')
                elif target_type in ['float', 'double', 'number']:
                    df[column] = pd.to_numeric(df[column], errors='coerce').astype(float) # Standard float
                elif target_type in ['str', 'string', 'text', 'object']:
                    df[column] = df[column].astype(str)
                elif target_type in ['datetime', 'date']:
                    df[column] = pd.to_datetime(df[column], errors='coerce')
                elif target_type in ['bool', 'boolean']:
                     # pd.BooleanDtype() allows NA
                     df[column] = df[column].astype(pd.BooleanDtype()) # This handles 'True','False','true','false',1,0, NAs well
                elif target_type == 'category':
                    df[column] = df[column].astype('category')
                else:
                    return jsonify({'error': f'Unsupported target type: {target_type}'}), 400

                new_nulls = df[column].isnull().sum()
                coerced_count = new_nulls - original_nulls
                action_msg = f"Converted column '{column}' to type '{target_type}'."
                if coerced_count > 0:
                     action_msg += f" {coerced_count} value(s) set to null due to conversion errors."

            except Exception as e:
                # Revert if conversion fails? Less critical here as errors='coerce' handles most cases
                return jsonify({'error': f'Error converting column "{column}" to {target_type}: {e}'}), 500


        elif operation == 'rename_column':
            old_name = params.get('old_name')
            new_name = params.get('new_name')
            if not old_name: return jsonify({'error': 'Old column name parameter is required.'}), 400
            if old_name not in df.columns: return jsonify({'error': f'Column "{old_name}" not found'}), 400
            if not new_name: return jsonify({'error': 'New column name parameter is required.'}), 400
            if new_name == old_name: return jsonify({'message': 'New name is the same as the old name. No change made.', 'df_modified': False }), 200 # No change needed
            if new_name in df.columns: return jsonify({'error': f'New column name "{new_name}" already exists.'}), 400

            df.rename(columns={old_name: new_name}, inplace=True)
            action_msg = f"Renamed column '{old_name}' to '{new_name}'."


        elif operation == 'drop_columns':
            columns_to_drop = params.get('columns_to_drop') # Expect list
            if not columns_to_drop or not isinstance(columns_to_drop, list):
                 return jsonify({'error': 'Requires a list of columns to drop.'}), 400

            actual_cols_to_drop = [col for col in columns_to_drop if col in df.columns]
            if not actual_cols_to_drop:
                 return jsonify({'error': 'None of the specified columns found in the data.'}), 400

            df = df.drop(columns=actual_cols_to_drop) # Assign back is safer than inplace
            action_msg = f"Dropped columns: {', '.join(actual_cols_to_drop)}."
            if len(actual_cols_to_drop) < len(columns_to_drop):
                 missing = [col for col in columns_to_drop if col not in actual_cols_to_drop]
                 action_msg += f" (Columns not found and ignored: {', '.join(missing)})"

        elif operation == 'replace_text':
             column = params.get('column')
             text_to_find = params.get('text_to_find')
             replace_with = params.get('replace_with', '') # Default to replace with empty string
             use_regex = params.get('use_regex', False) # Default to literal replacement

             if not column: return jsonify({'error': 'Column parameter is required.'}), 400
             if column not in df.columns: return jsonify({'error': f'Column "{column}" not found'}), 400
             if text_to_find is None: return jsonify({'error': 'Text to find parameter is required.'}), 400 # Allow empty string
             if not (pd.api.types.is_object_dtype(df[column]) or pd.api.types.is_string_dtype(df[column])):
                  return jsonify({'error': 'Replace text operation only applicable to text columns.'}), 400

             try:
                 # Ensure string type for replacement
                 df[column] = df[column].astype(str).str.replace(str(text_to_find), str(replace_with), regex=bool(use_regex))
                 mode = "regex" if use_regex else "literal"
                 action_msg = f"Replaced text '{text_to_find}' with '{replace_with}' in column '{column}' (mode: {mode})."
             except re.error as e:
                 if use_regex:
                      return jsonify({'error': f'Invalid regex pattern provided: {e}'}), 400
                 else: # Should not happen in literal mode, but just in case
                      return jsonify({'error': f'Error during text replacement: {e}'}), 500
             except Exception as e:
                  return jsonify({'error': f'Error during text replacement: {e}'}), 500

        elif operation == 'change_case':
            column = params.get('column')
            case_type = params.get('case_type') # 'lower', 'upper', 'title'
            if not column: return jsonify({'error': 'Column parameter is required.'}), 400
            if column not in df.columns: return jsonify({'error': f'Column "{column}" not found'}), 400
            if not (pd.api.types.is_object_dtype(df[column]) or pd.api.types.is_string_dtype(df[column])):
                 return jsonify({'error': 'Change case operation only applicable to text columns.'}), 400
            if case_type not in ['lower', 'upper', 'title']:
                 return jsonify({'error': 'Invalid case type. Must be "lower", "upper", or "title".'}), 400

            if case_type == 'lower': df[column] = df[column].astype(str).str.lower()
            elif case_type == 'upper': df[column] = df[column].astype(str).str.upper()
            elif case_type == 'title': df[column] = df[column].astype(str).str.title()
            action_msg = f"Converted text in column '{column}' to {case_type} case."

        elif operation == 'map_values':
            column = params.get('column')
            mapping_dict = params.get('mapping_dict') # Expect a dict/object
            if not column: return jsonify({'error': 'Column parameter is required.'}), 400
            if column not in df.columns: return jsonify({'error': f'Column "{column}" not found'}), 400
            if not mapping_dict or not isinstance(mapping_dict, dict):
                 return jsonify({'error': 'Mapping dictionary parameter is required and must be an object/dictionary.'}), 400

            try:
                 # Use replace which is generally more flexible than map for this purpose
                 df[column] = df[column].replace(mapping_dict)
                 action_msg = f"Mapped values in column '{column}' using provided dictionary."
            except Exception as e: # Handle potential type issues if dict keys/values mismatch column
                 return jsonify({'error': f'Error applying map/replace: {e}'}), 500

        elif operation == 'sort_values':
            columns_to_sort_by = params.get('columns_to_sort_by') # Expect list
            ascending = params.get('ascending', True) # Default True, can be bool or list

            if not columns_to_sort_by or not isinstance(columns_to_sort_by, list):
                 return jsonify({'error': 'Requires a list of columns to sort by.'}), 400
            if not all(col in df.columns for col in columns_to_sort_by):
                 missing = [col for col in columns_to_sort_by if col not in df.columns]
                 return jsonify({'error': f'Columns not found: {missing}'}), 400

            # Validate ascending parameter format if it's a list
            if isinstance(ascending, list) and len(ascending) != len(columns_to_sort_by):
                return jsonify({'error': 'If "ascending" is a list, its length must match the number of columns to sort by.'}), 400

            try:
                 # Use ignore_index=True to reset the index after sorting
                 df = df.sort_values(by=columns_to_sort_by, ascending=ascending, ignore_index=True)
                 asc_desc = "ascending" if ascending is True else ("descending" if ascending is False else str(ascending))
                 action_msg = f"Sorted DataFrame by columns: {', '.join(columns_to_sort_by)} ({asc_desc})."
            except Exception as e:
                 return jsonify({'error': f'Error during sorting: {e}'}), 500


        # --- Add more 'elif operation == ...' blocks here for other functions ---
        # elif operation == 'remove_outliers_iqr':
        #     # Get column, calculate Q1, Q3, IQR, filter df
        #     action_msg = "Removed outliers using IQR method..."
        # elif operation == 'rename_column':
        #     # Get old_name, new_name, perform df.rename()
        #     action_msg = "Renamed column..."

        # --- Operation not found ---
        else:
            # If operation isn't recognized, we shouldn't have added to undo.
            # This part is tricky because undo was already potentially modified.
            # Best practice: Validate operation *before* modifying undo history.
            # Quick Fix: Log it, maybe try to pop from undo? (Risky)
            app.logger.warning(f"Unknown cleaning operation received: {operation}")
            # Attempt to revert undo (may not be perfectly safe depending on add_to_undo logic)
            undo_history = session.get('undo_history', [])
            if undo_history:
                 session['undo_history'] = undo_history[:-1] # Remove the last added state

            return jsonify({'error': f'Unknown cleaning operation: {operation}'}), 400

        # 5. Store the MODIFIED DataFrame back into the session
        store_dataframe_in_session(df) # Use the helper function

        table_html, total_rows, total_columns = render_table_html(df)

        # 6. Prepare successful JSON response
        response_data = {
            'message': action_msg,
            'table_html': render_table_html(df), # Use helper to generate HTML
            'columns': df.columns.tolist(),       # Send updated column list
            'undo_redo_status': get_undo_redo_status(), # Send button states
            'total_rows': total_rows,
            'total_columns': total_columns
        }
        return jsonify(response_data), 200

    except Exception as e:
        # 7. Handle unexpected errors during the operation
        app.logger.error(f"Error during cleaning operation '{operation}': {e}", exc_info=True) # Log full traceback

        # Attempt to rollback state by restoring the last known good state from undo history
        # This prevents the session from holding a potentially corrupted intermediate state
        undo_history = session.get('undo_history', [])
        if undo_history:
             # The last item in undo_history is the state *before* the failed operation
             last_good_state_json = undo_history.pop() # Remove it as it represents the current state now
             session['current_df_json'] = last_good_state_json
             session['undo_history'] = undo_history # Save the shortened undo history
             # Don't clear redo; the failed action didn't succeed, so redo might still be valid.
        else:
             # If no undo history, we might be in trouble. Clear the current DF?
             clear_session_data() # Or handle differently

        # Send generic error back to frontend
        return jsonify({'error': f'An internal server error occurred during the operation: {str(e)}'}), 500


@app.route('/calculate_outlier_ranges', methods=['GET'])
@login_required
def calculate_outlier_ranges_route():
    """
    Calculates IQR and Z-score based outlier ranges for all numerical columns.
    """
    df = get_dataframe_from_session()
    if df is None or df.empty:
        return jsonify({'error': 'No data loaded.'}), 400

    ranges_data = {}
    # Standard factors/thresholds to show in the UI
    iqr_factors_to_show = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    zscore_thresholds_to_show = [1.0, 1.5, 2.0, 2.5, 3.0] # Absolute values

    # Exclude boolean and constant columns
    bool_cols = df.select_dtypes(include=np.bool_).columns.tolist()
    constant_cols = [col for col in df.columns if df[col].nunique(dropna=False) <= 1]
    numerical_cols = df.select_dtypes(include=np.number).columns.tolist()
    cols_to_analyze = [col for col in numerical_cols if col not in bool_cols and col not in constant_cols]

    if not cols_to_analyze:
        return jsonify({'message': 'No suitable numerical columns found for outlier range calculation.'}), 200

    for col in cols_to_analyze:
        col_ranges = {'iqr': {}, 'zscore': {}}
        series = df[col].dropna() # Use non-NA data for calculations
        n_nonan = len(series)

        # IQR Ranges
        if n_nonan >= 4: # Need enough data for quartiles
            try:
                q1 = series.quantile(0.25)
                q3 = series.quantile(0.75)
                iqr_value = q3 - q1
                if pd.notna(iqr_value) and iqr_value >= 0: # Check if IQR is valid
                    for factor in iqr_factors_to_show:
                        lower = q1 - factor * iqr_value
                        upper = q3 + factor * iqr_value
                        col_ranges['iqr'][f"{factor}x IQR"] = {'lower': round(lower, 4), 'upper': round(upper, 4)}
                else:
                    col_ranges['iqr']['Error'] = "Could not calculate (IQR invalid or zero)"
            except Exception as e:
                app.logger.warning(f"Error calculating IQR ranges for {col}: {e}")
                col_ranges['iqr']['Error'] = str(e)
        else:
            col_ranges['iqr']['Info'] = "Not enough data points"

        # Z-score Ranges
        if n_nonan > 1: # Need at least 2 points for std deviation
            try:
                mean_val = series.mean()
                std_val = series.std(ddof=0) # Population standard deviation
                if pd.notna(mean_val) and pd.notna(std_val) and std_val > 1e-9: # Check for valid mean/std
                    for threshold in zscore_thresholds_to_show:
                        lower = mean_val - threshold * std_val
                        upper = mean_val + threshold * std_val
                        col_ranges['zscore'][f"±{threshold}σ"] = {'lower': round(lower, 4), 'upper': round(upper, 4)}
                elif std_val <= 1e-9 :
                     col_ranges['zscore']['Error'] = "Standard deviation is zero or too small"
                else:
                     col_ranges['zscore']['Error'] = "Could not calculate mean/std"

            except Exception as e:
                app.logger.warning(f"Error calculating Z-score ranges for {col}: {e}")
                col_ranges['zscore']['Error'] = str(e)
        else:
            col_ranges['zscore']['Info'] = "Not enough data points"

        ranges_data[col] = col_ranges

    return jsonify({'ranges_data': ranges_data}), 200



# --- NEW Search and Suggestion Endpoints ---
@app.route('/get_suggestions', methods=['GET'])
@login_required
def get_suggestions():
    df = get_dataframe_from_session()
    if df is None:
        return jsonify({'error': 'No data loaded.'}), 400

    column_name = request.args.get('column')
    query_term = request.args.get('query', '').lower()

    if not column_name or column_name not in df.columns:
        return jsonify({'suggestions': []}) # Avoid error if column is temp unavailable (e.g. during quick typing)

    if not query_term:
        return jsonify({'suggestions': []})

    try:
        # Ensure column is treated as string, handle NaN by dropping them before unique/search
        # This is for suggestions, so performance on unique values is key.
        # Limit number of unique values to process for suggestions if very high.
        unique_vals_series = df[column_name].dropna().astype(str)
        if len(unique_vals_series) > 50000: # Heuristic limit for suggestion source
            unique_values_sampled = unique_vals_series.sample(n=50000, random_state=1).unique()
        else:
            unique_values_sampled = unique_vals_series.unique()
        
        suggestions = [
            val for val in unique_values_sampled if query_term in val.lower()
        ]
        return jsonify({'suggestions': suggestions[:15]}) # Return top 15
    except Exception as e:
        app.logger.error(f"Error getting suggestions for column '{column_name}': {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/perform_search', methods=['POST'])
@login_required
def perform_search():
    df_original = get_dataframe_from_session()
    if df_original is None:
        return jsonify({'error': 'No data loaded.'}), 400

    data = request.get_json()
    column_name = data.get('column')
    search_term_raw = data.get('term', '') # Keep original case for potential display/session storage
    search_term_lower = search_term_raw.lower()

    if not column_name or column_name not in df_original.columns:
        return jsonify({'error': 'Invalid column specified for search.'}), 400

    if not search_term_raw: # If search term is empty, effectively clear search
        session.pop('active_search_criteria', None)
        table_html, total_rows, total_columns = render_table_html(df_original)
        return jsonify({
            'table_html': table_html,
            'total_rows': total_rows,
            'total_columns': total_columns,
            'search_cleared': True,
            'columns': df_original.columns.tolist()
        })

    try:
        mask = df_original[column_name].astype(str).str.lower().str.contains(search_term_lower, na=False)
        df_filtered = df_original[mask]
        
        # Store raw term for display consistency if needed later
        session['active_search_criteria'] = {'column': column_name, 'term_raw': search_term_raw}

        table_html, total_rows_filtered, total_cols_filtered = render_table_html(df_filtered)
        
        return jsonify({
            'table_html': table_html,
            'total_rows': total_rows_filtered, # This is filtered row count
            'total_columns': total_cols_filtered, # Should be same as original
            'search_applied': True,
            'filtered_row_count': len(df_filtered),
            'original_row_count': len(df_original),
            'search_term_applied': search_term_raw, # The term that was applied
            'search_column_applied': column_name,
            'columns': df_original.columns.tolist() # Full list of columns for dropdown consistency
        })
    except Exception as e:
        app.logger.error(f"Error performing search on column '{column_name}': {e}", exc_info=True)
        session.pop('active_search_criteria', None) # Clear search if it errored
        return jsonify({'error': f'Error during search: {str(e)}'}), 500


@app.route('/clear_search_filter', methods=['POST'])
@login_required
def clear_search_filter_route(): # Renamed to avoid conflict with helper function
    df = get_dataframe_from_session()
    if df is None:
        return jsonify({'error': 'No data to display.'}), 400
    
    session.pop('active_search_criteria', None)

    table_html, total_rows, total_columns = render_table_html(df)
    return jsonify({
        'message': 'Search filter cleared.',
        'table_html': table_html,
        'columns': df.columns.tolist(),
        'total_rows': total_rows,
        'total_columns': total_columns,
        'search_cleared': True
    })



# --- New Route for Auto Cleaning ---
 
@app.route('/get_auto_clean_config', methods=['GET'])
@login_required
def get_auto_clean_config_route():
    """Returns the currently saved auto-clean configuration from the session."""
    # Define default configuration structure
    default_config = {
        'outlier_handling': 'none',
        'outlier_iqr_factor': 1.5,
        'outlier_zscore_threshold': 3.0,
        'missing_numeric_method': 'median',
        'missing_other_method': 'ffill_bfill',
        'case_change_method': 'none',
        'trim_whitespace': True,
        'convert_numeric': True,
        'convert_datetime': True,
        'convert_category': True
    }
    current_config = session.get('auto_clean_config', default_config.copy()) # Use a copy of defaults
    # Ensure all keys from default_config are present in current_config
    for key, value in default_config.items():
        current_config.setdefault(key, value)

    return jsonify({'config': current_config}), 200
    
@app.route('/save_auto_clean_config', methods=['POST'])
@login_required
def save_auto_clean_config():
    """
    Receives auto-clean configuration from the frontend, validates it,
    and saves it to the user's session.
    """
    try:
        config_data = request.get_json() # Get JSON data from the request body
        if not config_data or not isinstance(config_data, dict):
            return jsonify({'error': 'Invalid configuration format. JSON object expected.'}), 400

        # --- Define Default Structure & Validation ---
        # This helps ensure all expected keys are present and have sensible defaults/types.
        # You can expand validation here if needed (e.g., specific allowed values for selects).
        default_config = {
            'outlier_handling': 'none',
            'outlier_iqr_factor': 1.5,
            'outlier_zscore_threshold': 3.0,
            'missing_numeric_method': 'median',
            'missing_other_method': 'ffill_bfill',
            'case_change_method': 'none',
            'trim_whitespace': True,
            'convert_numeric': True,
            'convert_datetime': True,
            'convert_category': True
        }

        validated_config = {}

        # Outlier Handling
        validated_config['outlier_handling'] = config_data.get('outlier_handling', default_config['outlier_handling'])
        if validated_config['outlier_handling'] not in ['none', 'clip_iqr', 'remove_iqr', 'clip_zscore', 'remove_zscore']:
            validated_config['outlier_handling'] = default_config['outlier_handling'] # Reset to default if invalid

        try:
            iqr_factor = float(config_data.get('outlier_iqr_factor', default_config['outlier_iqr_factor']))
            validated_config['outlier_iqr_factor'] = iqr_factor if iqr_factor > 0 else default_config['outlier_iqr_factor']
        except (ValueError, TypeError):
            validated_config['outlier_iqr_factor'] = default_config['outlier_iqr_factor']

        try:
            zscore_thresh = float(config_data.get('outlier_zscore_threshold', default_config['outlier_zscore_threshold']))
            validated_config['outlier_zscore_threshold'] = zscore_thresh if zscore_thresh > 0 else default_config['outlier_zscore_threshold']
        except (ValueError, TypeError):
            validated_config['outlier_zscore_threshold'] = default_config['outlier_zscore_threshold']


        # Missing Value Imputation
        validated_config['missing_numeric_method'] = config_data.get('missing_numeric_method', default_config['missing_numeric_method'])
        if validated_config['missing_numeric_method'] not in ['median', 'mean', 'none']:
            validated_config['missing_numeric_method'] = default_config['missing_numeric_method']

        validated_config['missing_other_method'] = config_data.get('missing_other_method', default_config['missing_other_method'])
        if validated_config['missing_other_method'] not in ['ffill_bfill', 'none']:
            validated_config['missing_other_method'] = default_config['missing_other_method']


        # Case Conversion
        validated_config['case_change_method'] = config_data.get('case_change_method', default_config['case_change_method'])
        if validated_config['case_change_method'] not in ['none', 'lower', 'upper', 'title']:
            validated_config['case_change_method'] = default_config['case_change_method']


        # Toggleable Operations (ensure they are boolean)
        validated_config['trim_whitespace'] = bool(config_data.get('trim_whitespace', default_config['trim_whitespace']))
        validated_config['convert_numeric'] = bool(config_data.get('convert_numeric', default_config['convert_numeric']))
        validated_config['convert_datetime'] = bool(config_data.get('convert_datetime', default_config['convert_datetime']))
        validated_config['convert_category'] = bool(config_data.get('convert_category', default_config['convert_category']))

        # Store the validated configuration in the session
        session['auto_clean_config'] = validated_config
        app.logger.info(f"Saved Auto Clean Config to session: {validated_config}")

        return jsonify({'message': 'Auto Clean configuration saved to session.', 'config': validated_config}), 200

    except Exception as e:
        app.logger.error(f"Error saving auto_clean_config: {e}", exc_info=True)
        return jsonify({'error': f'An internal server error occurred while saving configuration: {str(e)}'}), 500

@app.route('/auto_clean', methods=['POST'])
@login_required
def auto_clean_data():
    """
    Applies a predefined set of non-destructive cleaning steps, including:
    - Trims whitespace from string columns.
    - Attempts conversion of object columns to numeric/datetime (errors='coerce').
    - Clips outliers in numeric columns using IQR method (factor=1.5).
    - Fills missing values based on type (median for numeric, ffill/bfill for others).
    - Converts low-cardinality strings to Category.
    - Converts string/category columns to lowercase.
    """
    # 1. Get DataFrame and add to undo
    df = get_dataframe_from_session()
    if df is None:
        return jsonify({'error': 'No data loaded.'}), 400

    current_df_json = session.get('current_df_json')
    add_to_undo(current_df_json) # Save state before cleaning

    actions_performed = [] # Keep track of what was done per column
    df_cleaned = df.copy() # Work on a copy

    # --- Get Configurations ---
    # Get from session, or use defaults if not set by the user
    # If sending via POST request body: config = request.json.get('config', {})
    config = session.get('auto_clean_config', {})

    # --- Configuration Options ---
    # Outliers
    outlier_handling = config.get('outlier_handling', 'none') # 'none', 'clip_iqr', 'clip_zscore', 'remove_iqr', 'remove_zscore'
    outlier_iqr_factor = float(config.get('outlier_iqr_factor', 1.5))
    outlier_zscore_threshold = float(config.get('outlier_zscore_threshold', 3.0))

    # Missing Values
    missing_numeric_method = config.get('missing_numeric_method', 'median') # 'median', 'mean', 'none'
    missing_other_method = config.get('missing_other_method', 'ffill_bfill') # 'ffill_bfill', 'none'

    # Case Change
    case_change_method = config.get('case_change_method', 'none') # 'none', 'lower', 'upper', 'title'

    # Toggles
    trim_whitespace = config.get('trim_whitespace', True)
    convert_numeric = config.get('convert_numeric', True)
    convert_datetime = config.get('convert_datetime', True)
    convert_category = config.get('convert_category', True)


    app.logger.info(f"Auto Clean Config: {config}") # Log received config

    # --- NEW: Set to collect indices of rows to drop globally ---
    indices_to_drop_for_outliers = set()

    try:
        # --- Iterate through columns to apply cleaning steps ---
        for col in df_cleaned.columns:
            original_dtype_str = str(df_cleaned[col].dtype)
            col_actions = []
            series_to_process = df_cleaned[col] # Work on the current state of the column

            # --- 1. Trim Whitespace (Toggleable) ---
            if trim_whitespace and (pd.api.types.is_object_dtype(original_dtype_str) or pd.api.types.is_string_dtype(original_dtype_str)):
                try:
                    mask = series_to_process.notna()
                    if mask.any():
                        original_values = series_to_process[mask].astype(str)
                        stripped_values = original_values.str.strip()
                        if not original_values.equals(stripped_values):
                            # Create a copy to modify, then assign back to df_cleaned[col]
                            series_copy = series_to_process.copy()
                            series_copy.loc[mask] = stripped_values
                            df_cleaned[col] = series_copy
                            series_to_process = df_cleaned[col] # Update for next steps
                            col_actions.append("Trimmed whitespace")
                except Exception as e: app.logger.warning(f"AutoClean Error (Whitespace {col}): {e}")


            # --- 2. Numeric/Datetime Conversion (Toggleable) ---
            current_dtype_after_strip = str(series_to_process.dtype)
            if pd.api.types.is_object_dtype(current_dtype_after_strip):
                temp_series = series_to_process.copy() # Work on a temporary series for conversion attempts
                if convert_numeric:
                    try:
                        converted_numeric = pd.to_numeric(temp_series, errors='coerce')
                        if pd.api.types.is_numeric_dtype(converted_numeric.dtype) and \
                           converted_numeric.dtype != current_dtype_after_strip and \
                           converted_numeric.notna().any():
                            if (converted_numeric.dropna() % 1 == 0).all():
                                temp_series = converted_numeric.astype(pd.Int64Dtype())
                                col_actions.append("Converted to Integer")
                            else:
                                temp_series = converted_numeric.astype(float)
                                col_actions.append("Converted to Float")
                            series_to_process = temp_series # Update if conversion successful
                    except Exception as e: app.logger.warning(f"AutoClean Error (Numeric Conv {col}): {e}")

                if convert_datetime and pd.api.types.is_object_dtype(temp_series.dtype): # Check again
                     try:
                         converted_datetime = pd.to_datetime(temp_series, errors='coerce', infer_datetime_format=True)
                         if pd.api.types.is_datetime64_any_dtype(converted_datetime.dtype) and \
                            converted_datetime.dtype != current_dtype_after_strip and \
                            converted_datetime.notna().any():
                              temp_series = converted_datetime
                              col_actions.append("Converted to Datetime")
                              series_to_process = temp_series # Update if conversion successful
                     except Exception as e: app.logger.warning(f"AutoClean Error (Datetime Conv {col}): {e}")
                df_cleaned[col] = series_to_process # Assign final converted series back to DataFrame


            # --- 3. Outlier Handling (Configurable) ---
            current_dtype_after_conv = str(df_cleaned[col].dtype) # Use df_cleaned[col] for current dtype
            if outlier_handling != 'none' and pd.api.types.is_numeric_dtype(current_dtype_after_conv) and not pd.api.types.is_bool_dtype(current_dtype_after_conv):
                try:
                    col_data_for_outliers = df_cleaned[col]
                    col_data_nonan = col_data_for_outliers.dropna()
                    n_nonan = len(col_data_nonan)

                    if n_nonan >= 2: # Need at least 2 points for std dev, more for IQR
                        outlier_mask = pd.Series(False, index=df_cleaned.index)
                        outliers_count = 0

                        if outlier_handling == 'clip_iqr' or outlier_handling == 'remove_iqr':
                            Q1 = col_data_nonan.quantile(0.25)
                            Q3 = col_data_nonan.quantile(0.75)
                            IQR = Q3 - Q1
                            if IQR >= 0:
                                lower_bound = Q1 - outlier_iqr_factor * IQR
                                upper_bound = Q3 + outlier_iqr_factor * IQR
                                # Identify outliers on the original column's non-NA values to get correct indices
                                current_col_values = df_cleaned[col]
                                outlier_mask = (current_col_values < lower_bound) | (current_col_values > upper_bound)
                                outliers_count = outlier_mask.sum()

                                if outliers_count > 0:
                                    if outlier_handling == 'clip_iqr':
                                        # Create a copy, clip, then assign back
                                        series_copy = df_cleaned[col].copy()
                                        series_copy = series_copy.clip(lower=lower_bound, upper=upper_bound)
                                        df_cleaned[col] = series_copy
                                        col_actions.append(f"Clipped {outliers_count} outliers (IQR Factor: {outlier_iqr_factor})")
                                    elif outlier_handling == 'remove_iqr':
                                        indices_to_drop_for_outliers.update(df_cleaned[outlier_mask].index)
                                        col_actions.append(f"Flagged {outliers_count} IQR outliers for row removal")

                        elif outlier_handling == 'clip_zscore' or outlier_handling == 'remove_zscore':
                            if n_nonan > 1 and col_data_nonan.std() > 0: # Z-score needs std > 0
                                z_scores = np.abs(scipy_stats.zscore(col_data_nonan)) # Use scipy for robust zscore on non-NaN
                                # Map z_scores back to original series to get correct indices for outlier_mask
                                temp_z_series = pd.Series(index=col_data_nonan.index, data=z_scores)
                                full_z_series = temp_z_series.reindex(df_cleaned.index).fillna(0)

                                outlier_mask = full_z_series > outlier_zscore_threshold
                                outliers_count = outlier_mask.sum()

                                if outliers_count > 0:
                                    if outlier_handling == 'clip_zscore':
                                        # Calculate bounds based on original series' mean and std for clipping
                                        mean_val = df_cleaned[col].mean() # Use mean of the whole column (could be mean of col_data_nonan)
                                        std_val = df_cleaned[col].std()   # Use std of the whole column
                                        if std_val > 0:
                                            lower_bound_z = mean_val - outlier_zscore_threshold * std_val
                                            upper_bound_z = mean_val + outlier_zscore_threshold * std_val
                                            series_copy = df_cleaned[col].copy()
                                            series_copy = series_copy.clip(lower=lower_bound_z, upper=upper_bound_z)
                                            df_cleaned[col] = series_copy
                                            col_actions.append(f"Clipped {outliers_count} outliers (Z-score > {outlier_zscore_threshold})")
                                    elif outlier_handling == 'remove_zscore':
                                        indices_to_drop_for_outliers.update(df_cleaned[outlier_mask].index)
                                        col_actions.append(f"Flagged {outliers_count} Z-score outliers for row removal")
                            else:
                                col_actions.append(f"Z-score outlier detection skipped (std=0 or too few values)")
                except Exception as e: app.logger.warning(f"AutoClean Error (Outliers {col}): {e}")

            # --- 4. Fill Missing Values (Configurable) ---
            series_to_process = df_cleaned[col] # Get latest state of the column
            current_dtype_after_outlier = str(series_to_process.dtype)
            if series_to_process.isnull().any():
                try:
                    # Ensure to use series_to_process and assign back to df_cleaned[col]
                    if pd.api.types.is_numeric_dtype(current_dtype_after_outlier) and not pd.api.types.is_bool_dtype(current_dtype_after_outlier):
                        filled_series = series_to_process.copy()
                        if missing_numeric_method == 'median':
                            median_val = filled_series.median()
                            if not pd.isna(median_val): filled_series.fillna(median_val, inplace=True); col_actions.append(f"Filled NA with Median ({median_val:.4g})")
                        elif missing_numeric_method == 'mean':
                            mean_val = filled_series.mean()
                            if not pd.isna(mean_val): filled_series.fillna(mean_val, inplace=True); col_actions.append(f"Filled NA with Mean ({mean_val:.4g})")
                        df_cleaned[col] = filled_series
                    elif missing_other_method == 'ffill_bfill':
                        filled_series = series_to_process.copy()
                        original_nulls = filled_series.isnull().sum()
                        filled_series.fillna(method='ffill', inplace=True)
                        filled_series.fillna(method='bfill', inplace=True)
                        if filled_series.isnull().sum() < original_nulls: col_actions.append("Filled NA (ffill/bfill)")
                        df_cleaned[col] = filled_series
                except Exception as e: app.logger.warning(f"AutoClean Error (Missing Fill {col}): {e}")


            # --- 5. Convert Low-Cardinality Strings to Category (Toggleable) ---
            dtype_after_fill = str(df_cleaned[col].dtype)
            if convert_category and (pd.api.types.is_object_dtype(dtype_after_fill) or pd.api.types.is_string_dtype(dtype_after_fill)) and \
               not pd.api.types.is_categorical_dtype(dtype_after_fill):
                try:
                     n_unique = df_cleaned[col].nunique()
                     # Using fixed thresholds from features page for consistency
                     if n_unique / len(df_cleaned) < 0.02 or n_unique <= 10: # Example heuristic
                         df_cleaned[col] = df_cleaned[col].astype('category')
                         col_actions.append(f"Converted to Category ({n_unique} unique)")
                except Exception as e: app.logger.warning(f"AutoClean Error (Category Conv {col}): {e}")


            # --- 6. Change Case (Configurable) ---
            dtype_after_cat = str(df_cleaned[col].dtype)
            if case_change_method != 'none' and \
               (pd.api.types.is_object_dtype(dtype_after_cat) or pd.api.types.is_string_dtype(dtype_after_cat) or pd.api.types.is_categorical_dtype(dtype_after_cat)):
                try:
                    mask = df_cleaned[col].notna()
                    if mask.any():
                        changed = False
                        if case_change_method == 'lower':
                            if (df_cleaned.loc[mask, col].astype(str) != df_cleaned.loc[mask, col].astype(str).str.lower()).any():
                                if pd.api.types.is_categorical_dtype(dtype_after_cat): df_cleaned[col].cat.rename_categories(str.lower, inplace=True)
                                else: df_cleaned.loc[mask, col] = df_cleaned.loc[mask, col].astype(str).str.lower()
                                changed = True
                        elif case_change_method == 'upper':
                            if (df_cleaned.loc[mask, col].astype(str) != df_cleaned.loc[mask, col].astype(str).str.upper()).any():
                                if pd.api.types.is_categorical_dtype(dtype_after_cat): df_cleaned[col].cat.rename_categories(str.upper, inplace=True)
                                else: df_cleaned.loc[mask, col] = df_cleaned.loc[mask, col].astype(str).str.upper()
                                changed = True
                        elif case_change_method == 'title':
                            if (df_cleaned.loc[mask, col].astype(str) != df_cleaned.loc[mask, col].astype(str).str.title()).any():
                                if pd.api.types.is_categorical_dtype(dtype_after_cat): df_cleaned[col].cat.rename_categories(str.title, inplace=True)
                                else: df_cleaned.loc[mask, col] = df_cleaned.loc[mask, col].astype(str).str.title()
                                changed = True
                        if changed: col_actions.append(f"Converted to {case_change_method}case")
                except Exception as e: app.logger.warning(f"AutoClean Error (Case Change {col}): {e}")

            if col_actions:
                actions_performed.append(f"Column '{col}' ({original_dtype_str} -> {str(df_cleaned[col].dtype)}): {'; '.join(col_actions)}")

        # --- Global Row Removal for Outliers (Applied ONCE after loop) ---
        if indices_to_drop_for_outliers:
            original_row_count = len(df_cleaned)
            # Ensure indices are valid and sorted to avoid issues with some backends if not unique
            valid_indices_to_drop = sorted(list(set(indices_to_drop_for_outliers).intersection(df_cleaned.index)))
            if valid_indices_to_drop:
                df_cleaned.drop(index=valid_indices_to_drop, inplace=True)
                rows_removed = original_row_count - len(df_cleaned)
                if rows_removed > 0:
                    actions_performed.append(f"Globally removed {rows_removed} row(s) containing identified outliers.")
            else:
                app.logger.info("No valid outlier indices found to drop after loop.")

        store_dataframe_in_session(df_cleaned)
        summary_message = "Auto Clean with custom configuration complete."
        if actions_performed:
             actions_html = "<ul>" + "".join(f"<li>{action}</li>" for action in actions_performed) + "</ul>"
             summary_message += f" Actions Performed:<br>{actions_html}"
        else:
             summary_message += " No specific cleaning actions were applied based on the configuration."

        table_html, total_rows, total_columns = render_table_html(df_cleaned)
        response_data = {
            'message': summary_message, 'table_html': table_html,
            'columns': df_cleaned.columns.tolist(), 'undo_redo_status': get_undo_redo_status(),
            'total_rows': total_rows, 'total_columns': total_columns
        }
        return jsonify(response_data), 200

    except Exception as e:
        app.logger.error(f"Error during Auto Clean: {e}", exc_info=True)
        # Attempt rollback (keep existing rollback logic)
        undo_history = session.get('undo_history', [])
        if undo_history:
             last_good_state_json = undo_history.pop()
             session['current_df_json'] = last_good_state_json
             session['undo_history'] = undo_history
        return jsonify({'error': f'An internal server error occurred during Auto Clean: {str(e)}'}), 500
    

# Helper to safely convert pandas describe() output to JSON-serializable format
def safe_describe_to_dict(describe_result):
    stats_dict = {}
    if describe_result is None:
        return stats_dict
    try:
        # Convert Series/DataFrame describe output to dict
        if isinstance(describe_result, pd.Series):
            stats_dict = describe_result.to_dict()
        elif isinstance(describe_result, pd.DataFrame):
            # Handle multi-index if necessary, or just convert first column if simple describe
            stats_dict = describe_result.iloc[:, 0].to_dict() # Adjust if describe returns multiple columns
        else:
            return {} # Not a recognized describe result

        # Ensure all values are JSON serializable (handle Timestamps, NaNs etc.)
        for key, value in stats_dict.items():
            if pd.isna(value):
                stats_dict[key] = None # Convert Pandas NA/NaN to None
            elif isinstance(value, (np.integer, np.int64)):
                stats_dict[key] = int(value)
            elif isinstance(value, (np.floating, np.float64)):
                stats_dict[key] = float(value)
            # Add other type conversions if needed (e.g., Timestamps)
            elif isinstance(value, pd.Timestamp):
                 stats_dict[key] = value.isoformat() # Convert Timestamp to ISO string

        return stats_dict
    except Exception as e:
        app.logger.error(f"Error converting describe result to dict: {e}")
        return {}


@app.route('/column_stats/<path:column_name>')
@login_required
def get_column_stats(column_name):
    """Calculates and returns statistics for a specific column."""
    df = get_dataframe_from_session()
    if df is None:
        return jsonify({'error': 'No data loaded.'}), 400

    if column_name not in df.columns:
        return jsonify({'error': f'Column "{column_name}" not found.'}), 404

    try:
        selected_col = df[column_name]
        stats = {}
        dtype_str = str(selected_col.dtype)
        total_rows_df = len(df) # Total rows in the entire DataFrame

        # --- Common Stats ---
        stats['Data Type'] = dtype_str
        stats['Total Rows (DataFrame)'] = int(total_rows_df)
        stats['Non-Missing Values'] = int(selected_col.count()) # Count non-NA/null values
        missing_count = int(selected_col.isnull().sum())
        stats['Missing Values'] = missing_count
        stats['Missing (%)'] = f"{(missing_count / total_rows_df * 100):.2f}%" if total_rows_df > 0 else "0.00%"
        
        unique_count_total_with_nan = int(selected_col.nunique(dropna=False))
        stats['Unique Values (Incl. NaN)'] = unique_count_total_with_nan
        stats['Unique (%) (Incl. NaN)'] = f"{(unique_count_total_with_nan / total_rows_df * 100):.2f}%" if total_rows_df > 0 else "0.00%"
        
        unique_count_no_nan = int(selected_col.nunique()) 
        stats['Unique Values (Excl. NaN)'] = unique_count_no_nan

        try:
            mem_usage_bytes = selected_col.memory_usage(deep=True)
            if mem_usage_bytes < 1024:
                 stats['Memory Usage'] = f"{mem_usage_bytes} B"
            elif mem_usage_bytes < 1024**2:
                 stats['Memory Usage'] = f"{mem_usage_bytes/1024:.2f} KB"
            else:
                 stats['Memory Usage'] = f"{mem_usage_bytes/(1024**2):.2f} MB"
        except Exception:
             stats['Memory Usage'] = "N/A"

        # --- Type-Specific Stats ---
        if pd.api.types.is_numeric_dtype(selected_col) and not pd.api.types.is_bool_dtype(selected_col):
            desc = selected_col.describe()
            numeric_stats = safe_describe_to_dict(desc) 
            if 'mean' in numeric_stats: stats['Mean'] = numeric_stats['mean']
            if 'std' in numeric_stats: stats['Std Dev'] = numeric_stats['std']
            if 'min' in numeric_stats: stats['Min'] = numeric_stats['min']
            if '25%' in numeric_stats: stats['25% (Q1)'] = numeric_stats['25%']
            if '50%' in numeric_stats: stats['Median (50%)'] = numeric_stats['50%']
            if '75%' in numeric_stats: stats['75% (Q3)'] = numeric_stats['75%']
            if 'max' in numeric_stats: stats['Max'] = numeric_stats['max']
            stats['Zero Count'] = int((selected_col == 0).sum())
            stats['Negative Count'] = int((selected_col < 0).sum())
            try:
                col_data_nonan = selected_col.dropna() 
                if len(col_data_nonan) >= 4: 
                    Q1 = col_data_nonan.quantile(0.25)
                    Q3 = col_data_nonan.quantile(0.75)
                    IQR = Q3 - Q1
                    if IQR >= 0: 
                        factor = 1.5 
                        lower_bound = Q1 - factor * IQR
                        upper_bound = Q3 + factor * IQR
                        outliers_count = int(((col_data_nonan < lower_bound) | (col_data_nonan > upper_bound)).sum())
                        stats['Outliers (IQR, 1.5x)'] = outliers_count
                        stats['Outliers (%)'] = f"{(outliers_count / total_rows_df * 100):.2f}%" if total_rows_df > 0 else "0.00%"
                        if IQR == 0 and outliers_count == 0 and Q1 == Q3 : 
                             stats['Outliers (IQR, 1.5x)'] = "0 (No Spread in Non-NA Data)"
                    else: 
                        stats['Outliers (IQR, 1.5x)'] = 'Error (IQR<0)'
                        stats['Outliers (%)'] = 'Error'
                else:
                     stats['Outliers (IQR, 1.5x)'] = 'N/A (Too Few Non-NA Values)'
                     stats['Outliers (%)'] = 'N/A'
            except Exception as e:
                app.logger.warning(f"Could not calculate IQR outliers for {column_name}: {e}") # Use app.logger
                stats['Outliers (IQR, 1.5x)'] = 'Error'
                stats['Outliers (%)'] = 'Error'

        elif pd.api.types.is_datetime64_any_dtype(selected_col):
            try:
                desc = selected_col.describe(datetime_is_numeric=False)
                dt_stats = safe_describe_to_dict(desc)
                if 'first' in dt_stats: stats['First Date'] = dt_stats['first'] 
                if 'last' in dt_stats: stats['Last Date'] = dt_stats['last']   
            except Exception as e:
                app.logger.warning(f"Could not describe datetime column {column_name}: {e}") # Use app.logger
                if selected_col.count() > 0:
                    try: stats['First Date'] = selected_col.min().isoformat()
                    except: pass 
                    try: stats['Last Date'] = selected_col.max().isoformat()
                    except: pass 

        elif pd.api.types.is_categorical_dtype(selected_col) or pd.api.types.is_object_dtype(selected_col) or pd.api.types.is_string_dtype(selected_col):
            try:
                 desc = selected_col.describe(include='all') 
                 cat_stats = safe_describe_to_dict(desc)
                 if 'top' in cat_stats: stats['Most Frequent Value'] = cat_stats['top']
                 if 'freq' in cat_stats: stats['Frequency (Most Freq.)'] = cat_stats['freq']
            except Exception as e:
                 app.logger.warning(f"Could not describe categorical/object column {column_name}: {e}") # Use app.logger

            if selected_col.count() > 0 and (pd.api.types.is_string_dtype(selected_col.dtype) or \
               (pd.api.types.is_object_dtype(selected_col.dtype) and isinstance(selected_col.dropna().iloc[0] if not selected_col.dropna().empty else "", str)) or \
               (pd.api.types.is_categorical_dtype(selected_col.dtype) and isinstance(selected_col.cat.categories[0] if len(selected_col.cat.categories)>0 else "", str))):
                try:
                    str_col_for_len = selected_col.astype(str) 
                    lengths = str_col_for_len.str.len()
                    if lengths.count() > 0: 
                        stats['Min Length'] = int(lengths.min())
                        stats['Max Length'] = int(lengths.max())
                        stats['Avg Length'] = float(f"{lengths.mean():.2f}")
                except Exception as e:
                    app.logger.warning(f"Could not calculate string lengths for {column_name}: {e}") # Use app.logger

        elif pd.api.types.is_bool_dtype(selected_col):
             try:
                  value_counts_bool = selected_col.value_counts(dropna=False)
                  stats['Value Counts (Boolean)'] = {str(k): int(v) for k, v in value_counts_bool.items()}
             except Exception as e:
                  app.logger.warning(f"Could not calculate boolean value counts for {column_name}: {e}") # Use app.logger

        # --- Unique and Duplicate Value Analysis (Applicable to All Types) ---
        max_list_display = 99999 
        value_counts_all = selected_col.value_counts(dropna=False)

        truly_unique_values_series = value_counts_all[value_counts_all == 1]
        truly_unique_values_list = truly_unique_values_series.index.tolist()
        stats['unique_values_sample'] = [
            'NULL' if pd.isna(v) else str(v)
            for v in truly_unique_values_list[:max_list_display]
        ]
        stats['unique_values_total_count'] = len(truly_unique_values_list)

        # --- MODIFIED: Duplicate Values with Counts and Percentages (Sample) ---
        duplicates_series = value_counts_all[value_counts_all > 1] 
        duplicates_sample_list = []
        for val, count_val in duplicates_series.head(max_list_display).items(): # Renamed count to count_val to avoid conflict
            str_val = 'NULL' if pd.isna(val) else str(val)
            current_count = int(count_val)
            percentage = (current_count / total_rows_df * 100) if total_rows_df > 0 else 0.0
            percentage_str = f"{percentage:.2f}%"
            duplicates_sample_list.append([str_val, current_count, percentage_str]) # Added percentage_str

        stats['duplicate_values_sample'] = duplicates_sample_list
        stats['duplicate_values_distinct_count'] = len(duplicates_series) 
        
        total_duplicate_occurrences = int(duplicates_series.sum())
        stats['duplicate_occurrences_total'] = total_duplicate_occurrences
        
        # NEW: Overall percentage of rows that are part of duplications
        percentage_rows_with_duplicates = (total_duplicate_occurrences / total_rows_df * 100) if total_rows_df > 0 else 0.0
        stats['duplicate_occurrences_percentage'] = f"{percentage_rows_with_duplicates:.2f}%"
        # --- END MODIFICATION ---

        return jsonify({'column': column_name, 'stats': stats, 'dtype': dtype_str})

    except Exception as e:
        app.logger.error(f"Error calculating stats for column '{column_name}': {e}", exc_info=True) # Use app.logger
        return jsonify({'error': f'Error calculating stats: {str(e)}'}), 500


@app.route('/optimize_categories', methods=['POST'])
@login_required
def optimize_categories():
    """
    Converts string/object columns with low cardinality to 'category' dtype
    for memory efficiency.
    """
    # 1. Get DataFrame and add to undo
    df = get_dataframe_from_session()
    if df is None:
        return jsonify({'error': 'No data loaded.'}), 400

    current_df_json = session.get('current_df_json')
    add_to_undo(current_df_json) # Save state before optimizing

    actions_performed = []
    df_optimized = df.copy() # Work on a copy

    # Define thresholds (these could potentially be parameters later)
    unique_fraction_threshold = 0.5 # e.g., less than 50% unique values
    absolute_unique_threshold = 1000 # e.g., less than 1000 unique values absolute max

    try:
        for col in df_optimized.columns:
            dtype = df_optimized[col].dtype

            # Check if it's a candidate type (object, string) and NOT already category
            if (pd.api.types.is_object_dtype(dtype) or pd.api.types.is_string_dtype(dtype)) and \
               not pd.api.types.is_categorical_dtype(dtype):

                n_unique = df_optimized[col].nunique()
                fraction_unique = n_unique / len(df_optimized) if len(df_optimized) > 0 else 0

                # Apply heuristic: low absolute unique count OR low fraction unique
                if n_unique < absolute_unique_threshold and fraction_unique < unique_fraction_threshold:
                    try:
                        df_optimized[col] = df_optimized[col].astype('category')
                        actions_performed.append(f"Column '{col}' ({n_unique} unique)")
                    except Exception as e:
                        app.logger.warning(f"Could not convert column '{col}' to category: {e}")

        # 4. Store modified DataFrame and prepare response
        store_dataframe_in_session(df_optimized)

        if actions_performed:
            summary_message = f"Optimized Categories complete. Converted columns: {', '.join(actions_performed)}."
        else:
            summary_message = "Optimize Categories complete. No suitable columns found for conversion based on criteria."

        response_data = {
            'message': summary_message,
            'table_html': render_table_html(df_optimized),
            'columns': df_optimized.columns.tolist(), # Columns don't change, but type does
            'undo_redo_status': get_undo_redo_status()
        }
        return jsonify(response_data), 200

    except Exception as e:
        app.logger.error(f"Error during Optimize Categories: {e}", exc_info=True)
        # Attempt rollback
        undo_history = session.get('undo_history', [])
        if undo_history:
             last_good_state_json = undo_history.pop()
             session['current_df_json'] = last_good_state_json
             session['undo_history'] = undo_history
        return jsonify({'error': f'An internal server error occurred during Optimize Categories: {str(e)}'}), 500


# --- Undo/Redo Routes ---

@app.route('/undo', methods=['POST'])
@login_required
def undo():
    """Reverts to the previous state."""
    current_df_json = session.get('current_df_json')
    undo_history = session.get('undo_history', [])
    redo_history = session.get('redo_history', [])

    if not undo_history:
        return jsonify({'error': 'Nothing to undo'}), 400

    # Move current state to redo
    if current_df_json:
        redo_history.insert(0, current_df_json) # Add to beginning of redo list

    # Get last state from undo
    last_state_json = undo_history.pop()

    # Update session
    session['current_df_json'] = last_state_json
    session['undo_history'] = undo_history
    session['redo_history'] = redo_history[-10:] # Limit redo history size

    # Load DF and prepare response
    df = get_dataframe_from_session()

    table_html, total_rows, total_columns = render_table_html(df)

    response_data = {
        'message': 'Undo successful.',
        'table_html': render_table_html(df),
        'columns': df.columns.tolist() if df is not None else [],
        'undo_redo_status': get_undo_redo_status(),
        'total_rows': total_rows,
        'total_columns': total_columns
    }
    return jsonify(response_data)

@app.route('/redo', methods=['POST'])
@login_required
def redo():
    """Re-applies a previously undone state."""
    current_df_json = session.get('current_df_json')
    undo_history = session.get('undo_history', [])
    redo_history = session.get('redo_history', [])

    if not redo_history:
        return jsonify({'error': 'Nothing to redo'}), 400

    # Move current state to undo
    if current_df_json:
        undo_history.append(current_df_json)

    # Get first state from redo
    next_state_json = redo_history.pop(0) # Get from beginning

    # Update session
    session['current_df_json'] = next_state_json
    session['undo_history'] = undo_history[-10:] # Limit undo history size
    session['redo_history'] = redo_history

    # Load DF and prepare response
    df = get_dataframe_from_session()

    table_html, total_rows, total_columns = render_table_html(df)

    response_data = {
        'message': 'Redo successful.',
        'table_html': render_table_html(df),
        'columns': df.columns.tolist() if df is not None else [],
        'undo_redo_status': get_undo_redo_status(),
        'total_rows': total_rows,
        'total_columns': total_columns
    }
    return jsonify(response_data)


# --- Download and Save Routes ---

@app.route('/download/<filetype>')
@login_required
def download_file(filetype):
    """Downloads the current DataFrame as CSV or XLSX."""
    df = get_dataframe_from_session()
    if df is None:
        flash("No data to download.", "error")
        return redirect(url_for('clean_data_interface'))

    buffer = io.BytesIO()
    filename = f"cleaned_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    try:
        if filetype == 'csv':
            df.to_csv(buffer, index=False, encoding='utf-8')
            mimetype = 'text/csv'
            filename += '.csv'
        elif filetype == 'xlsx':
            # Requires openpyxl
            df.to_excel(buffer, index=False, engine='openpyxl')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            filename += '.xlsx'
        else:
            flash("Invalid file type for download.", "error")
            return redirect(url_for('clean_data_interface'))

        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype
        )
    except Exception as e:
        flash(f"Error generating download file: {e}", "error")
        app.logger.error(f"Download Error: {e}", exc_info=True)
        return redirect(url_for('clean_data_interface'))

@app.route('/save', methods=['POST'])
@login_required
def save_session():
    """Saves the current DataFrame state to a Parquet file on the server.""" # Docstring updated
    df = get_dataframe_from_session()
    if df is None:
        return jsonify({'error': 'No data to save'}), 400

    save_name = request.json.get('filename')
    if save_name:
         filename = secure_filename(save_name).replace('..', '')
         if not filename.endswith('.parquet'): # CHANGED from .pkl
             filename += '.parquet'          # CHANGED from .pkl
    else:
         filename = f"session_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d')}.parquet" # CHANGED from .pkl

    filepath = os.path.join(app.config['SAVED_SESSIONS_FOLDER'], filename)

    try:
        df.to_parquet(filepath, index=False) # CHANGED from to_pickle, added index=False
        session['saved_filename'] = filename
        flash(f"Session saved as '{filename}'. You can reopen it later.", "success")
        return jsonify({
            'message': f"Session saved as {filename}",
            'saved_filename': filename
        })
    except Exception as e:
        flash(f"Error saving session: {e}", "error")
        app.logger.error(f"Save Error: {e}", exc_info=True)
        return jsonify({'error': f'Error saving session: {str(e)}'}), 500

# In open_saved_session function:
@app.route('/open_saved/<filename>')
@login_required
def open_saved_session(filename):
    """Loads a previously saved DataFrame session from a Parquet file.""" # Docstring updated
    safe_filename = secure_filename(filename)
    if not safe_filename.endswith('.parquet'): # CHANGED from .pkl
         flash("Invalid file format. Expected .parquet", "error") # Message updated
         return redirect(url_for('index'))

    filepath = os.path.join(app.config['SAVED_SESSIONS_FOLDER'], safe_filename)

    if not os.path.exists(filepath):
        flash(f"Saved session '{safe_filename}' not found.", "error")
        return redirect(url_for('index'))

    try:
        df = pd.read_parquet(filepath) # CHANGED from read_pickle
        clear_session_data()
        store_dataframe_in_session(df)
        base_name, _ = os.path.splitext(safe_filename)
        session['source_info'] = base_name
        session['saved_filename'] = safe_filename
        flash(f"Loaded saved session '{safe_filename}'.", "info")
        return redirect(url_for('clean_data_interface'))
    except Exception as e:
        flash(f"Error loading saved session: {e}", "error")
        app.logger.error(f"Open Saved Error: {e}", exc_info=True)
        return redirect(url_for('index'))

# --- NEW ROUTE FOR DELETING SAVED SESSIONS ---
@app.route('/delete_saved/<filename>', methods=['POST'])
@login_required
def delete_saved_session(filename):
    """Deletes a previously saved session file."""
    safe_filename = secure_filename(filename)
    if not safe_filename.endswith('.parquet'):
        flash("Invalid file format for deletion. Expected .parquet", "error")
        return redirect(url_for('index'))

    filepath = os.path.join(app.config['SAVED_SESSIONS_FOLDER'], safe_filename)

    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            # If the deleted file was the currently 'saved_filename' in session, clear it
            if session.get('saved_filename') == safe_filename:
                session.pop('saved_filename', None)
            flash(f"Session '{safe_filename}' deleted successfully.", "success")
        except OSError as e:
            flash(f"Error deleting file '{safe_filename}': {e}", "error")
            app.logger.error(f"Error deleting saved session file {safe_filename}: {e}", exc_info=True)
    else:
        flash(f"File '{safe_filename}' not found. Could not delete.", "warning")

    return redirect(url_for('index'))

# --- NEW ROUTE FOR DOWNLOADING SAVED FILES AS CSV/XLSX ---
@app.route('/download_saved_file/<path:filename>/<filetype>')
@login_required
def download_saved_file(filename, filetype):
    """
    Reads a saved Parquet file, converts it to CSV or XLSX,
    and sends it for download.
    """
    safe_filename = secure_filename(filename)
    if not safe_filename.endswith('.parquet'):
        flash("Invalid source file for download. Must be a .parquet file.", "error")
        return redirect(url_for('index'))

    filepath = os.path.join(app.config['SAVED_SESSIONS_FOLDER'], safe_filename)

    if not os.path.exists(filepath):
        flash(f"Saved file '{safe_filename}' not found.", "error")
        return redirect(url_for('index'))

    try:
        df = pd.read_parquet(filepath)
    except Exception as e:
        flash(f"Error reading saved file '{safe_filename}': {e}", "error")
        app.logger.error(f"Error reading Parquet file {filepath} for download: {e}", exc_info=True)
        return redirect(url_for('index'))

    buffer = io.BytesIO()
    download_basename = os.path.splitext(safe_filename)[0] # Get name without .parquet extension

    try:
        if filetype == 'csv':
            df.to_csv(buffer, index=False, encoding='utf-8')
            mimetype = 'text/csv'
            download_filename_complete = f"{download_basename}.csv"
        elif filetype == 'xlsx':
            # Requires openpyxl to be installed
            df.to_excel(buffer, index=False, engine='openpyxl')
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            download_filename_complete = f"{download_basename}.xlsx"
        else:
            flash(f"Unsupported file type for download: {filetype}", "error")
            return redirect(url_for('index'))

        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=download_filename_complete,
            mimetype=mimetype
        )
    except ImportError:
        if filetype == 'xlsx':
            flash("Cannot generate XLSX: 'openpyxl' library is not installed. Please ask the admin to install it (`pip install openpyxl`).", "error")
            app.logger.error("XLSX download failed: openpyxl not found.")
        else:
            flash(f"Error generating download file due to a missing library.", "error") # General message for other import errors
            app.logger.error(f"Download generation import error for {filetype}", exc_info=True)
        return redirect(url_for('index'))
    except Exception as e:
        flash(f"Error generating download file: {e}", "error")
        app.logger.error(f"Download generation error: {e}", exc_info=True)
        return redirect(url_for('index'))
# --- END NEW DOWNLOAD ROUTE ---
    


# --- New Route for Features Page ---
    
# --- Complete Route for Features Page ---
@app.route('/features')
@login_required
def show_features():
    """
    Displays a page focused on detected features, patterns, and potential
    feature extraction/cleaning needs. Enhanced for data analysts.
    """
    df = get_dataframe_from_session()
    if df is None or df.empty:
        flash("No data loaded or data is empty. Cannot analyze features.", "warning")
        return redirect(url_for('index'))

    feature_summary = {}
    error_message = None

    # --- Define Thresholds Used in Analysis ---
    correlation_threshold = 0.3
    skewness_threshold = 1.0
    kurtosis_threshold = 1.5 # Fisher kurtosis
    normality_alpha = 0.05
    high_missing_threshold = 0.5
    warning_missing_threshold = 0.1
    low_cardinality_unique_threshold = 10
    low_cardinality_fraction_threshold = 0.02 # As a fraction of total rows
    high_cardinality_fraction_threshold = 0.95 # As a fraction of total rows
    high_zero_fraction_threshold = 0.5
    text_pattern_sample_size = 100
    group_by_max_categories = 10
    special_char_regex = r'[^\w\s.,\-]' # Chars not word, space, period, comma, hyphen
    # Define the limit for modes
    max_modes_to_show = 25


    try:
        # --- 1. General Info & Memory Usage ---
        rows = int(len(df))
        columns = int(len(df.columns))
        total_cells = int(df.size)
        duplicate_rows = int(df.duplicated().sum())

        memory_usage = df.memory_usage(deep=True)
        total_memory_bytes = memory_usage.sum()
        memory_by_type = {}
        for dtype in df.dtypes.unique():
            dtype_str = str(dtype)
            cols_of_type = df.select_dtypes(include=[dtype]).columns
            mem = memory_usage[cols_of_type].sum()
            if mem < 1024: mem_str = f"{mem} B"
            elif mem < 1024**2: mem_str = f"{mem/1024:.2f} KB"
            elif mem < 1024**3: mem_str = f"{mem/(1024**2):.2f} MB"
            else: mem_str = f"{mem/(1024**3):.2f} GB"
            memory_by_type[dtype_str] = mem_str

        if total_memory_bytes < 1024: total_mem_str = f"{total_memory_bytes} B"
        elif total_memory_bytes < 1024**2: total_mem_str = f"{total_memory_bytes/1024:.2f} KB"
        elif total_memory_bytes < 1024**3: total_mem_str = f"{total_memory_bytes/(1024**2):.2f} MB"
        else: total_mem_str = f"{total_memory_bytes/(1024**3):.2f} GB"

        feature_summary.update({
            'rows_raw': rows, 'columns': columns, 'rows': f"{rows:,d}",
            'total_cells': f"{total_cells:,d}", 'duplicate_rows': f"{duplicate_rows:,d}",
            'duplicate_rows_raw': duplicate_rows,
            'total_memory': total_mem_str, 'memory_by_type': memory_by_type
        })

        # --- 2. Column Types, Constants, Mixed Types ---
        dtype_counts_raw = Counter()
        constant_value_cols = []
        mixed_type_cols = [] # Columns with genuinely mixed Python types (excluding NaN)
        warning_missing_cols = []

        for col in df.columns:
            series = df[col]
            dtype_str = str(series.dtype)
            dtype_counts_raw[dtype_str] += 1

            if series.nunique(dropna=False) <= 1:
                constant_value_cols.append(col)

            if dtype_str == 'object': # Check for mixed types in object columns
                try:
                    # Consider non-NaN values. If multiple Python types exist, flag it.
                    non_nan_types = series.dropna().apply(type).nunique()
                    if non_nan_types > 1:
                        mixed_type_cols.append(col)
                except Exception as e:
                    app.logger.warning(f"Error inferring dtype for mixed type check on {col}: {e}")

            missing_frac = series.isnull().mean()
            if warning_missing_threshold < missing_frac <= high_missing_threshold:
                warning_missing_cols.append(col)

        feature_summary['column_types'] = {k: f"{v:,d}" for k, v in dtype_counts_raw.items()}
        feature_summary['constant_value_cols'] = constant_value_cols
        feature_summary['mixed_type_cols'] = mixed_type_cols
        feature_summary['warning_missing_cols'] = warning_missing_cols

        # --- 3. Missing Data Overview ---
        total_missing = int(df.isnull().sum().sum())
        missing_percentage = (total_missing / total_cells * 100) if total_cells > 0 else 0
        feature_summary.update({
            'total_missing_raw': total_missing, 'total_missing': f"{total_missing:,d}",
            'missing_percentage': f"{missing_percentage:.2f}%"
        })
        missing_series = df.isnull().mean()
        feature_summary['high_missing_cols'] = missing_series[missing_series > high_missing_threshold].index.tolist()

        # --- 4. Numerical Patterns (INCLUDING DESCRIPTIVE STATS & ADVANCED NORMALITY TESTS) ---
        numeric_col_details = {}
        numeric_cols_list = [] # This list will store numeric columns suitable for further analysis
        
        # Get boolean columns once to exclude them from numeric analysis
        bool_cols = df.select_dtypes(include=np.bool_).columns.tolist()

        for col in df.select_dtypes(include=np.number).columns:
            # Skip boolean columns and columns already identified as constant
            if col in bool_cols or col in constant_value_cols: 
                continue
            
            numeric_cols_list.append(col) # Add to our list of suitable numeric columns
            details = {}
            
            # Prepare data: drop NaNs and ensure float type for statistical tests
            col_data_nonan = df[col].dropna().astype(float)
            n_nonan = len(col_data_nonan)
            
            # Basic Descriptive Statistics
            if n_nonan > 0:
                details['min'] = round(col_data_nonan.min(), 4)
                details['max'] = round(col_data_nonan.max(), 4)
                details['mean'] = round(col_data_nonan.mean(), 4)
                details['median'] = round(col_data_nonan.median(), 4) # Added median
                details['std'] = round(col_data_nonan.std(), 4)
                details['variance'] = round(col_data_nonan.var(), 4) # Added variance
            else:
                details['min'] = details['max'] = details['mean'] = details['median'] = details['std'] = details['variance'] = 'N/A'

            # Skewness
            details['skewness'], details['skew_comment'] = ('N/A', None)
            if n_nonan > 2: # Skewness requires more than 2 data points
                try:
                    skew = col_data_nonan.skew()
                    if pd.notna(skew) and not math.isinf(skew):
                        details['skewness'] = round(skew, 2)
                        if abs(skew) > skewness_threshold: details['skew_comment'] = "Highly Skewed"
                        elif abs(skew) > 0.5: details['skew_comment'] = "Moderately Skewed"
                        else: details['skew_comment'] = "Approx. Symmetric"
                except Exception as e:
                    details['skewness'] = 'Error'
                    app.logger.warning(f"Skewness calculation error for {col}: {e}")
            
            # Kurtosis (Fisher's definition: Normal = 0)
            details['kurtosis'], details['kurtosis_comment'] = ('N/A', None)
            if n_nonan > 3: # Kurtosis requires more than 3 data points
                try:
                    kurt = col_data_nonan.kurt()
                    if pd.notna(kurt) and not math.isinf(kurt):
                        details['kurtosis'] = round(kurt, 2)
                        if kurt > kurtosis_threshold: details['kurtosis_comment'] = "Leptokurtic (Peaked, Heavy Tails)"
                        elif kurt < -kurtosis_threshold: details['kurtosis_comment'] = "Platykurtic (Flat, Light Tails)"
                        else: details['kurtosis_comment'] = "Mesokurtic (Normal-like Peak)"
                except Exception as e:
                    details['kurtosis'] = 'Error'
                    app.logger.warning(f"Kurtosis calculation error for {col}: {e}")

            # --- Normality Tests ---
            details['normality_tests'] = {}
            can_run_norm_tests = n_nonan >= 8 and col_data_nonan.nunique() > 1 
            
            if not can_run_norm_tests:
                details['normality_tests']['common_message'] = "N/A (too few unique/non-missing values)"
            else:
                # Shapiro-Wilk Test
                if SCIPY_AVAILABLE:
                    shapiro_result = {'p_value': 'N/A', 'comment': "Not run"}
                    if n_nonan <= 5000:
                        try:
                            _, p_value = scipy_stats.shapiro(col_data_nonan)
                            shapiro_result['p_value'] = round(p_value, 4)
                            shapiro_result['comment'] = "Likely NOT Normal" if p_value <= normality_alpha else "Cannot Reject Normality"
                        except ValueError as ve: 
                            shapiro_result['comment'] = f"Skipped ({str(ve)[:30]})"
                            app.logger.debug(f"Shapiro ValueError for {col}: {ve}")
                        except Exception as e:
                            shapiro_result['comment'] = f"Error ({str(e)[:30]})"
                            app.logger.warning(f"Shapiro error for {col}: {e}")
                    else:
                        shapiro_result['comment'] = "Skipped (>5000 values)"
                    details['normality_tests']['Shapiro-Wilk'] = shapiro_result
                else:
                    details['normality_tests']['Shapiro-Wilk'] = {'comment': "Requires SciPy"}

                # Kolmogorov-Smirnov (KS) Test
                if SCIPY_AVAILABLE:
                    ks_result = {'p_value': 'N/A', 'comment': "Not run"}
                    try:
                        mean_val = col_data_nonan.mean()
                        std_val = col_data_nonan.std()
                        if std_val > 1e-9: 
                            _, p_value = scipy_stats.kstest(col_data_nonan, 'norm', args=(mean_val, std_val))
                            ks_result['p_value'] = round(p_value, 4)
                            ks_result['comment'] = "Likely NOT Normal" if p_value <= normality_alpha else "Cannot Reject Normality"
                        else:
                            ks_result['comment'] = "Skipped (std dev too small)"
                    except Exception as e:
                        ks_result['comment'] = f"Error ({str(e)[:30]})"
                        app.logger.warning(f"KS test error for {col}: {e}")
                    details['normality_tests']['Kolmogorov-Smirnov'] = ks_result
                else:
                    details['normality_tests']['Kolmogorov-Smirnov'] = {'comment': "Requires SciPy"}

                # Lilliefors Test
                # Check for STATSMODELS_DIAG_AVAILABLE (assuming you defined it as suggested for lilliefors)
                if STATSMODELS_DIAG_AVAILABLE: # or STATSMODELS_AVAILABLE if it's a general flag
                    lilliefors_result = {'p_value': 'N/A', 'comment': "Not run"}
                    if n_nonan >= 20: 
                        try:
                            _, p_value = lilliefors(col_data_nonan, dist='norm', pvalmethod='approx')
                            lilliefors_result['p_value'] = round(p_value, 4)
                            lilliefors_result['comment'] = "Likely NOT Normal" if p_value <= normality_alpha else "Cannot Reject Normality"
                        except Exception as e:
                            lilliefors_result['comment'] = f"Error ({str(e)[:30]})"
                            app.logger.warning(f"Lilliefors test error for {col}: {e}")
                    else:
                        lilliefors_result['comment'] = "Skipped (n < 20)"
                    details['normality_tests']['Lilliefors'] = lilliefors_result
                else:
                    details['normality_tests']['Lilliefors'] = {'comment': "Requires statsmodels"}

                # Anderson-Darling Test
                if SCIPY_AVAILABLE:
                    ad_result = {'statistic': 'N/A', 'comment': "Not run"}
                    try:
                        result_ad = scipy_stats.anderson(col_data_nonan, dist='norm')
                        ad_result['statistic'] = round(result_ad.statistic, 4)
                        sig_level_idx = -1
                        target_sig_level_percent = normality_alpha * 100
                        for i, sig_percent in enumerate(result_ad.significance_level):
                            if math.isclose(sig_percent, target_sig_level_percent):
                                sig_level_idx = i
                                break
                        if sig_level_idx != -1:
                            critical_value = result_ad.critical_values[sig_level_idx]
                            interpretation = "Likely NOT Normal" if result_ad.statistic > critical_value else "Cannot Reject Normality"
                            ad_result['comment'] = f"{interpretation} (vs CV at {normality_alpha*100:.0f}%)"
                        else: # Fallback to 5% if exact alpha not found
                            idx_5_percent = -1
                            for i, sig_percent in enumerate(result_ad.significance_level): # Find 5% index
                                if math.isclose(sig_percent, 5.0): idx_5_percent = i; break
                            if idx_5_percent != -1:
                                critical_value_5pct = result_ad.critical_values[idx_5_percent]
                                interpretation = "Likely NOT Normal" if result_ad.statistic > critical_value_5pct else "Cannot Reject Normality"
                                ad_result['comment'] = f"{interpretation} (vs CV at 5%)"
                            else:
                                ad_result['comment'] = f"CV for {normality_alpha*100:.0f}% not found"
                    except UserWarning as uw: 
                        ad_result['comment'] = f"Skipped ({str(uw)[:30]})"
                        app.logger.debug(f"Anderson-Darling UserWarning for {col}: {uw}")
                    except Exception as e:
                        ad_result['comment'] = f"Error ({str(e)[:30]})"
                        app.logger.warning(f"Anderson-Darling error for {col}: {e}")
                    details['normality_tests']['Anderson-Darling'] = ad_result
                else:
                    details['normality_tests']['Anderson-Darling'] = {'comment': "Requires SciPy"}
            
            # Outliers (IQR Method)
            details['outliers_iqr'], details['outliers_percent'] = ('N/A', 'N/A')
            if n_nonan >= 4:
                try:
                    Q1 = col_data_nonan.quantile(0.25)
                    Q3 = col_data_nonan.quantile(0.75)
                    IQR = Q3 - Q1
                    if IQR >= 0: 
                        factor = 1.5
                        lower_bound = Q1 - factor * IQR
                        upper_bound = Q3 + factor * IQR
                        outliers_count = int(((col_data_nonan < lower_bound) | (col_data_nonan > upper_bound)).sum())
                        outliers_percent_val = (outliers_count / rows * 100) if rows > 0 else 0 
                        details['outliers_iqr'] = f"{outliers_count:,d}"
                        details['outliers_percent'] = f"{outliers_percent_val:.2f}%"
                        if IQR == 0 and outliers_count == 0: 
                            details['outliers_iqr'] += " (No Spread)"
                    else: 
                        details['outliers_iqr'], details['outliers_percent'] = 'Error (IQR<0)', 'Error'
                except Exception as e:
                    app.logger.warning(f"IQR outliers error for {col}: {e}")
                    details['outliers_iqr'], details['outliers_percent'] = 'Error', 'Error'

            # Zero Percentage
            details['zero_percent'], details['zero_comment'] = ("N/A", None)
            if n_nonan > 0:
                try:
                    zero_frac = (col_data_nonan == 0).mean()
                    details['zero_percent'] = f"{zero_frac * 100:.2f}%"
                    if zero_frac > high_zero_fraction_threshold:
                        details['zero_comment'] = "Very High % Zeros"
                except Exception as e:
                    details['zero_percent'] = "Error"
                    app.logger.warning(f"Zero percentage error for {col}: {e}")

            # Mode(s)
            details['modes'], details['mode_comment'] = ([], None)
            if n_nonan > 0:
                try:
                    modes_raw = col_data_nonan.mode().tolist()
                    num_modes_original = len(modes_raw)
                    
                    if num_modes_original > max_modes_to_show:
                        modes_to_display = modes_raw[:max_modes_to_show]
                        details['mode_comment'] = f"Multimodal (Top {max_modes_to_show} of {num_modes_original} shown)"
                    else:
                        modes_to_display = modes_raw
                        if num_modes_original > 1:
                            details['mode_comment'] = "Multimodal"
                        elif num_modes_original == 1:
                            details['mode_comment'] = "Unimodal"
                        # If num_modes_original is 0 (empty series after dropna), comment remains None
                    
                    details['modes'] = [
                        round(m, 4) if isinstance(m, (float, np.floating)) else (str(m) if m is not None else 'NaN') 
                        for m in modes_to_display
                    ]
                except Exception as e:
                    details['modes'] = ['Error']
                    app.logger.warning(f"Mode calculation error for {col}: {e}")


            # Extended Quantiles
            details['quantiles'] = None 
            if n_nonan >= 10:
                try:
                    q_values = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
                    quantiles_raw = col_data_nonan.quantile(q_values)
                    details['quantiles'] = {
                        f"{int(q*100)}%": round(quantiles_raw.loc[q], 4) if pd.notna(quantiles_raw.loc[q]) else 'N/A'
                        for q in q_values
                    }
                except Exception as e:
                    details['quantiles'] = {'Error': '!'}
                    app.logger.warning(f"Quantile calculation error for {col}: {e}")

            if details: # Ensure details dict is not empty before adding
                numeric_col_details[col] = details
        
        feature_summary['numeric_col_details'] = numeric_col_details
        # This list is crucial for subsequent sections (Correlation, Grouped Analysis)
        feature_summary['numeric_cols_for_analysis'] = numeric_cols_list 

        # --- 5. Categorical / Text Patterns ---
        categorical_col_details = {}
        low_cardinality_cols_list = [] # For grouped stats and suggestions
        id_like_cols = [] # Potential ID columns

        patterns_regex = {
            'Email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            'URL': r'^https?://[^\s/$.?#].[^\s]*$',
            'Date (YYYY-MM-DD)': r'^\d{4}-\d{2}-\d{2}$',
            'Date (MM/DD/YYYY)': r'^(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])/\d{4}$',
            'Phone (US-like)': r'^(\+?\d{1,2}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}$'
        }

        for col in df.select_dtypes(include=['object', 'string', 'category']).columns:
            if col in constant_value_cols: continue
            details = {}
            series = df[col]
            col_data_nonan = series.dropna()
            n_nonan = len(col_data_nonan)
            n_unique = series.nunique(dropna=False) # Consider NaNs in uniqueness for cardinality check
            unique_frac = n_unique / rows if rows > 0 else 0

            is_low_cardinality = (n_unique <= low_cardinality_unique_threshold or (unique_frac < low_cardinality_fraction_threshold and n_nonan > 0)) and n_unique > 1
            is_high_cardinality_id_like = unique_frac > high_cardinality_fraction_threshold and n_unique > 1 and (pd.api.types.is_string_dtype(series.dtype) or pd.api.types.is_object_dtype(series.dtype))


            details['cardinality_comment'] = f"Moderate ({n_unique} unique)"
            if is_low_cardinality:
                low_cardinality_cols_list.append(col)
                details['cardinality_comment'] = f"Low ({n_unique} unique)"
                try:
                    top_n = 5; vc = col_data_nonan.value_counts().head(top_n)
                    details[f'top_{top_n}_values'] = {str(k): f"{int(v):,d}" for k,v in vc.items()}
                except Exception: details[f'top_{top_n}_values'] = {"Error":"!"}
            if is_high_cardinality_id_like:
                id_like_cols.append(col)
                details['cardinality_comment'] = f"High ({n_unique} unique, ID-like?)"

            # String Length Stats
            details['min_len'], details['max_len'], details['avg_len'] = ('N/A','N/A','N/A')
            if n_nonan > 0:
                try:
                    str_col = col_data_nonan.astype(str); lengths = str_col.str.len()
                    if lengths.count() > 0: # Check if lengths series is not all NaN
                        details['min_len'] = int(lengths.min())
                        details['max_len'] = int(lengths.max())
                        details['avg_len'] = round(lengths.mean(), 1)
                except Exception: details['min_len'] = 'Error'

            # Whitespace, Special Chars, Patterns, Word/Sentence (for string-like object/string types)
            if n_nonan > 0 and (pd.api.types.is_string_dtype(series.dtype) or pd.api.types.is_object_dtype(series.dtype)):
                try:
                    # Use .astype(str) on the sample to ensure string methods work
                    sample = col_data_nonan.sample(n=min(text_pattern_sample_size, n_nonan), random_state=1).astype(str)
                    if (sample != sample.str.strip()).any():
                        details['whitespace_comment'] = "Potential leading/trailing whitespace"
                    if sample.str.contains(special_char_regex, regex=True, na=False).any():
                        details['special_chars_comment'] = "Contains non-alphanumeric chars (beyond .,-)"

                    detected_patterns = []
                    for name, pattern_str in patterns_regex.items():
                         try:
                            compiled_pattern = re.compile(f'^{pattern_str}$') # Anchor pattern
                            match_rate = sample.apply(lambda x: bool(compiled_pattern.match(str(x)))).mean()
                            if match_rate > 0.7: detected_patterns.append(f"{name} (~{match_rate:.0%})")
                         except re.error: continue # Skip bad regex patterns
                    if detected_patterns: details['detected_patterns'] = ", ".join(detected_patterns)

                    word_counts = sample.str.split().str.len()
                    if word_counts.count() > 0: details['avg_words'] = round(word_counts.mean(), 1)
                    sentence_counts = sample.str.split(r'[.!?]+').str.len().apply(lambda x: max(0, x - 1)) # Approx sentences
                    if sentence_counts.count() > 0: details['avg_sentences'] = round(sentence_counts.mean(),1)

                except Exception as e_str: app.logger.warning(f"String analysis error for {col}: {e_str}")


            if details: categorical_col_details[col] = details
        feature_summary['categorical_col_details'] = categorical_col_details
        feature_summary['low_cardinality_cols_list'] = low_cardinality_cols_list
        feature_summary['id_like_cols'] = id_like_cols


        # --- 6. Datetime Patterns ---
        datetime_cols_list = df.select_dtypes(include=[np.datetime64, 'datetime64[ns]']).columns.tolist()
        feature_summary['datetime_cols'] = datetime_cols_list # Store the list itself
        dt_summary = {}
        if datetime_cols_list:
            for col in datetime_cols_list:
                if col in constant_value_cols: continue
                col_details = {'min': 'N/A', 'max': 'N/A', 'monotonic': 'N/A'}
                try:
                    col_nonan = df[col].dropna()
                    if len(col_nonan) > 0:
                        col_details['min'] = col_nonan.min().isoformat()
                        col_details['max'] = col_nonan.max().isoformat()
                        if col_nonan.is_monotonic_increasing: col_details['monotonic'] = "Increasing"
                        elif col_nonan.is_monotonic_decreasing: col_details['monotonic'] = "Decreasing"
                        else: col_details['monotonic'] = "Not Monotonic"
                except Exception: col_details = {'min': 'Error', 'max': 'Error', 'monotonic': 'Error'}
                dt_summary[col] = col_details
        feature_summary['datetime_summary'] = dt_summary


        # --- 7. Correlation Analysis (Pearson, Spearman, Kendall) & PCA ---
        pearson_positive, pearson_negative = [], []
        spearman_positive, spearman_negative = [], []
        kendall_positive, kendall_negative = [], []
        
        feature_summary['correlation_threshold'] = correlation_threshold
        feature_summary['correlation_info'] = None # Message if correlation cannot be run
        feature_summary['correlation_error'] = None # For errors during correlation calculation
        feature_summary['pca_summary'] = None # Initialize PCA summary dictionary

        # Retrieve the list of numeric columns suitable for analysis
        # This list should have been populated in Section 4 (Numerical Patterns)
        # and contains numeric columns excluding booleans and constants.
        cols_for_corr_and_pca = feature_summary.get('numeric_cols_for_analysis', [])

        if len(cols_for_corr_and_pca) >= 2:
            try:
                # Further ensure these columns actually exist in the DataFrame 'df'
                # This is a safeguard, though cols_for_corr_and_pca should be derived from df.
                valid_cols_for_analysis = [col for col in cols_for_corr_and_pca if col in df.columns]

                if len(valid_cols_for_analysis) < 2:
                    feature_summary['correlation_info'] = "Not enough valid numerical columns (>=2) found in the DataFrame for correlation/PCA."
                else:
                    # --- Correlation Calculations ---
                    df_for_corr = df[valid_cols_for_analysis] # Use a subset DataFrame for correlations
                    
                    pearson_corr_matrix = df_for_corr.corr(method='pearson')
                    spearman_corr_matrix = df_for_corr.corr(method='spearman')
                    kendall_corr_matrix = df_for_corr.corr(method='kendall')
                    processed_pairs = set()

                    for i in range(len(valid_cols_for_analysis)):
                        for j in range(i + 1, len(valid_cols_for_analysis)):
                            col1, col2 = valid_cols_for_analysis[i], valid_cols_for_analysis[j]
                            pair = tuple(sorted((col1, col2)))
                            if pair in processed_pairs: continue
                            
                            # Pearson
                            try:
                                p_val = pearson_corr_matrix.loc[col1, col2]
                                if pd.notna(p_val) and abs(p_val) >= correlation_threshold:
                                    (pearson_positive if p_val > 0 else pearson_negative).append((col1, col2, p_val, abs(p_val)))
                            except KeyError: app.logger.debug(f"KeyError Pearson: {col1},{col2} not in matrix.")
                            except Exception as e_p: app.logger.warning(f"Pearson error for {pair}: {e_p}")
                            
                            # Spearman
                            try:
                                s_val = spearman_corr_matrix.loc[col1, col2]
                                if pd.notna(s_val) and abs(s_val) >= correlation_threshold:
                                    (spearman_positive if s_val > 0 else spearman_negative).append((col1, col2, s_val, abs(s_val)))
                            except KeyError: app.logger.debug(f"KeyError Spearman: {col1},{col2} not in matrix.")
                            except Exception as e_s: app.logger.warning(f"Spearman error for {pair}: {e_s}")

                            # Kendall
                            try:
                                k_val = kendall_corr_matrix.loc[col1, col2]
                                if pd.notna(k_val) and abs(k_val) >= correlation_threshold:
                                    (kendall_positive if k_val > 0 else kendall_negative).append((col1, col2, k_val, abs(k_val)))
                            except KeyError: app.logger.debug(f"KeyError Kendall: {col1},{col2} not in matrix.")
                            except Exception as e_k: app.logger.warning(f"Kendall error for {pair}: {e_k}")
                            
                            processed_pairs.add(pair)

                    # Sort all correlation lists by magnitude
                    for lst in [pearson_positive, pearson_negative, spearman_positive, spearman_negative, kendall_positive, kendall_negative]:
                        lst.sort(key=lambda item: item[3], reverse=True)

                    # --- Principal Component Analysis (PCA) ---
                    if SKLEARN_AVAILABLE: # Check if scikit-learn was imported successfully
                        pca_results_dict = {} # Use a local dict for PCA results
                        try:
                            # 1. Select data for PCA (already done with df_for_corr using valid_cols_for_analysis)
                            X_pca = df_for_corr.copy() # Use the same data as correlations
                            
                            # 2. Handle NaNs: Impute with mean. PCA cannot handle NaNs.
                            imputer = SimpleImputer(strategy='mean')
                            X_imputed = imputer.fit_transform(X_pca)
                            
                            # 3. Standardize the data: Crucial for PCA.
                            scaler = StandardScaler()
                            X_scaled = scaler.fit_transform(X_imputed)

                            # 4. Apply PCA
                            n_samples, n_features = X_scaled.shape
                            # Number of components should be min of samples or features
                            n_components_to_compute = min(n_samples, n_features) 
                            
                            if n_components_to_compute >= 1: # PCA requires at least 1 component
                                pca_model = PCA(n_components=n_components_to_compute, random_state=42) # Renamed pca to pca_model
                                pca_model.fit(X_scaled)

                                explained_variance_ratio = pca_model.explained_variance_ratio_
                                cumulative_explained_variance = np.cumsum(explained_variance_ratio)
                                
                                pca_results_dict['explained_variance_ratio'] = [round(x * 100, 2) for x in explained_variance_ratio]
                                pca_results_dict['cumulative_explained_variance'] = [round(x * 100, 2) for x in cumulative_explained_variance]
                                
                                common_thresholds = [80, 90, 95, 99]
                                components_for_threshold = {}
                                for thresh in common_thresholds:
                                    try:
                                        # Find first index where cumulative variance meets threshold
                                        num_comps = np.argmax(cumulative_explained_variance * 100 >= thresh) + 1
                                        components_for_threshold[thresh] = int(num_comps)
                                    except ValueError: 
                                        # If threshold not met by any number of components (e.g. only 1 component total < threshold)
                                        components_for_threshold[thresh] = "N/A" if cumulative_explained_variance[-1]*100 < thresh else n_components_to_compute
                                pca_results_dict['components_for_threshold'] = components_for_threshold
                                pca_results_dict['n_original_features'] = n_features

                                # Suggestion based on PCA
                                if n_features > 2: # Only suggest if there's potential for reduction
                                    comps_for_90 = components_for_threshold.get(90)
                                    if comps_for_90 and isinstance(comps_for_90, int) and comps_for_90 < n_features * 0.75:
                                        pca_results_dict['suggestion'] = (
                                            f"Consider using {comps_for_90} principal components "
                                            f"to capture ~90% of the variance, reducing from {n_features} features. "
                                            "This can help with multicollinearity and model simplicity."
                                        )
                                    elif components_for_threshold.get(80) and isinstance(components_for_threshold.get(80), int) and components_for_threshold.get(80) == 1 and n_features > 1:
                                         # Check if first component already explains a lot
                                         first_comp_variance = pca_results_dict['cumulative_explained_variance'][0]
                                         pca_results_dict['suggestion'] = (
                                            f"A single principal component captures ~{first_comp_variance}% of variance. "
                                            "This indicates strong linear relationships among these features, potentially high multicollinearity."
                                        )
                            else:
                                pca_results_dict['message'] = "Not enough components to compute PCA (n_components < 1 based on data shape)."
                        except Exception as pca_err:
                            pca_results_dict['error'] = f"PCA calculation failed: {str(pca_err)[:100]}" # Truncate long errors
                            app.logger.error(f"PCA analysis failed: {pca_err}", exc_info=True)
                        
                        feature_summary['pca_summary'] = pca_results_dict # Assign local dict to feature_summary
                    elif not SKLEARN_AVAILABLE:
                        feature_summary['pca_summary'] = {'message': "PCA analysis skipped: scikit-learn library not available."}
                    # else: PCA not applicable if SKLEARN_AVAILABLE is False or not enough valid_cols_for_analysis for PCA

            except Exception as outer_corr_pca_err:
                # This catches errors in the main try block for correlations/PCA setup
                err_msg = f"Error during correlation/PCA setup: {str(outer_corr_pca_err)}"
                feature_summary['correlation_error'] = err_msg # General error for this section
                app.logger.error(f"Correlation/PCA section failed: {outer_corr_pca_err}", exc_info=True)
        
        else: # len(cols_for_corr_and_pca) < 2
             feature_summary['correlation_info'] = "Not enough suitable numerical columns (>=2, non-boolean, non-constant) for correlation or PCA."

        # Assign correlation lists to feature_summary (even if empty)
        feature_summary['pearson_positive'] = pearson_positive
        feature_summary['pearson_negative'] = pearson_negative
        feature_summary['spearman_positive'] = spearman_positive
        feature_summary['spearman_negative'] = spearman_negative
        feature_summary['kendall_positive'] = kendall_positive
        feature_summary['kendall_negative'] = kendall_negative

        # --- 8. Grouped Analysis ---
        grouped_stats = {}
        
        # Retrieve the list of numeric columns suitable for analysis (populated in Section 4)
        # This list excludes boolean and constant columns.
        numeric_cols_for_group_analysis = feature_summary.get('numeric_cols_for_analysis', [])

        # Ensure low_cardinality_cols_list is available (populated in Section 5)
        # And that we have numeric columns to analyze
        if low_cardinality_cols_list and numeric_cols_for_group_analysis:
            # Filter candidate grouping columns by the max categories threshold
            candidate_group_cols = [
                c for c in low_cardinality_cols_list 
                if c in df.columns and df[c].nunique(dropna=False) <= group_by_max_categories
            ] # Added check 'c in df.columns' for robustness

            for group_col in candidate_group_cols:
                group_results_for_this_group_col = {} # Store results for current group_col

                # Prepare the list of numeric columns to aggregate for this specific group_col
                # Exclude the group_col itself and ensure columns are still in the DataFrame
                actual_numeric_cols_to_aggregate = [
                    num_c for num_c in numeric_cols_for_group_analysis
                    if num_c != group_col and num_c in df.columns
                ]
                
                if not actual_numeric_cols_to_aggregate:
                    continue # No suitable numeric columns to aggregate for this group_col

                for num_col_to_agg in actual_numeric_cols_to_aggregate:
                    try:
                        # Perform groupby and aggregation
                        # `observed=False`: include all defined categories of `group_col` even if not present in data subset
                        # `dropna=False` (for `groupby`): if `group_col` has NaNs, treat them as a group
                        # Note: `agg` will operate on non-NaN values of `num_col_to_agg` within each group by default.
                        aggregated_data = df.groupby(group_col, observed=False, dropna=False)[num_col_to_agg].agg(
                            ['mean', 'median', 'count']
                        ).round(2)
                        
                        # Filter out groups with too few data points for reliable stats
                        meaningful_stats = aggregated_data[aggregated_data['count'] > 5]
                        
                        if not meaningful_stats.empty:
                            # Store only mean and median for display
                            group_results_for_this_group_col[num_col_to_agg] = meaningful_stats[['mean', 'median']].to_dict('index')
                    
                    except pd.errors.DataError as pde:
                        # This can happen if a numeric column selected for aggregation ended up being non-numeric 
                        # after some DataFrame manipulations (should be rare if list is built correctly)
                        app.logger.warning(f"Pandas DataError during grouping for {num_col_to_agg} by {group_col}: {pde}. Skipping this pair.")
                    except Exception as e_group:
                        app.logger.warning(f"General grouping error for {num_col_to_agg} by {group_col}: {e_group}")
                
                if group_results_for_this_group_col: # If any numeric cols yielded results for this group_col
                    grouped_stats[group_col] = group_results_for_this_group_col
        
        feature_summary['grouped_stats'] = grouped_stats

        # --- 9. Feature Engineering Suggestions ---
        suggestions = []
        if duplicate_rows > 0: suggestions.append({'column': '(Table-Wide)', 'finding': 'Duplicate Rows', 'suggestion': 'Use "Remove Duplicate Rows" if unintentional.'})
        if feature_summary.get('high_missing_cols'): suggestions.append({'column': ', '.join(feature_summary['high_missing_cols']), 'finding': 'High Missing (>50%)', 'suggestion': 'Strongly consider imputation strategy or column removal.'})
        if feature_summary.get('warning_missing_cols'): suggestions.append({'column': ', '.join(feature_summary['warning_missing_cols']), 'finding': 'Moderate Missing (>10%)', 'suggestion': 'Imputation recommended (check distribution before choosing mean/median/mode).'})
        if constant_value_cols: suggestions.append({'column': ', '.join(constant_value_cols), 'finding': 'Constant Value', 'suggestion': 'Drop these columns as they offer no variance.'})
        if mixed_type_cols: suggestions.append({'column': ', '.join(mixed_type_cols), 'finding': 'Potential Mixed Types', 'suggestion': 'Investigate and enforce a single, appropriate data type for these columns.'})

        for col, details in numeric_col_details.items():
            if isinstance(details.get('skewness'), (int, float)) and abs(details['skewness']) > skewness_threshold: suggestions.append({'column': col, 'finding': 'High Skewness', 'suggestion': 'Consider transformations (log, sqrt, Box-Cox) for models assuming normality.'})
            if 'Likely NOT Normal' in details.get('normality_comment',''): suggestions.append({'column': col, 'finding': 'Potential Non-Normality', 'suggestion': 'May violate assumptions for some statistical tests or models.'})
            try: zero_perc = float(details.get('zero_percent','0%').replace('%',''))
            except: zero_perc = 0
            if zero_perc > high_zero_fraction_threshold*100 : suggestions.append({'column': col, 'finding': 'High Zero %', 'suggestion': 'Consider specific models for zero-inflated data, log(x+1) transformation, or a binary "is_zero" feature.'})
            try: outliers_perc = float(details.get('outliers_percent','0%').replace('%',''))
            except: outliers_perc = 0
            if outliers_perc > 5.0: suggestions.append({'column': col, 'finding': 'High Outlier % (IQR)', 'suggestion': 'Investigate source of outliers. Consider clipping, transformation, or robust statistical models.'})

        for col in low_cardinality_cols_list: suggestions.append({'column': col, 'finding': 'Low Cardinality', 'suggestion': 'Convert to Pandas Category type for memory efficiency. Consider Encoding (One-Hot/Label) for ML.'})
        for col, details in categorical_col_details.items():
            if details.get('whitespace_comment'): suggestions.append({'column': col, 'finding': 'Potential Whitespace', 'suggestion': 'Use "Trim Whitespace" tool for consistency.'})
            if details.get('special_chars_comment'): suggestions.append({'column': col, 'finding': 'Potential Special Chars', 'suggestion': 'Review non-alphanumeric characters; clean or remove if they are noise.'})
            if details.get('detected_patterns'): suggestions.append({'column': col, 'finding': 'Common Pattern Detected', 'suggestion': f"Contains {details['detected_patterns']}. Validate if this structure is expected and consistent. Consider extracting components."})
            avg_words = details.get('avg_words'); avg_len = details.get('avg_len'); card_comment = details.get('cardinality_comment','')
            if 'High' in card_comment and avg_len and avg_len > 30: suggestions.append({'column': col, 'finding': 'High Cardinality & Long Text', 'suggestion': 'Likely free text. Consider NLP techniques (TF-IDF, Embeddings), text statistics features, or hashing for ML.'})

        for col in datetime_cols_list:
            if col not in constant_value_cols:
                suggestions.append({'column': col, 'finding': 'Datetime Column', 'suggestion': 'Extract features: Year, Month, Day, DayOfWeek, Hour, Is_Weekend, Time Since Epoch/Event, etc.'})

        unique_corr_pairs = set()
        for corr_list in [pearson_positive, pearson_negative, spearman_positive, spearman_negative, kendall_positive, kendall_negative]:
            for c1, c2, _, _ in corr_list:
                unique_corr_pairs.add(tuple(sorted((c1,c2))))
        if unique_corr_pairs:
            pairs_str = ", ".join([f"({p[0]}/{p[1]})" for p in list(unique_corr_pairs)[:3]]) # Show first 3 unique pairs
            suggestions.append({'column': '(Multiple)', 'finding': 'High Correlation Detected', 'suggestion': f'Pairs like {pairs_str}... show strong relationships. Check for multicollinearity. Consider interaction terms or PCA.'})

        for group_col, num_cols_data in grouped_stats.items():
            for num_col, stats_dict in num_cols_data.items():
                means = [v['mean'] for v in stats_dict.values() if v and isinstance(v.get('mean'), (int, float))]
                if len(means) > 1:
                    range_means = max(means) - min(means)
                    avg_mean = sum(means) / len(means) if len(means) > 0 else 0
                    if avg_mean != 0 and abs(range_means / avg_mean) > 0.3:
                        suggestions.append({'column': f"{num_col} by {group_col}", 'finding': 'Notable Group Variation', 'suggestion': f'Mean of {num_col} varies across categories of {group_col}. This interaction could be a feature.'})
                        break

        feature_summary['engineering_suggestions'] = suggestions

    except Exception as e:
        error_message = f"An error occurred while calculating features: {str(e)}"
        app.logger.error(f"Error in /features route: {e}", exc_info=True)

    return render_template(
        'features.html',
        summary=feature_summary,
        error_message=error_message,
        source_info=session.get('source_info', 'Unknown Source'),
        high_missing_threshold=high_missing_threshold, # Pass thresholds for display in template if needed
        warning_missing_threshold=warning_missing_threshold,
        high_zero_fraction_threshold=high_zero_fraction_threshold,
        kurtosis_threshold=kurtosis_threshold, # Pass for conditional highlighting in template
        SCIPY_AVAILABLE=SCIPY_AVAILABLE # For conditional messages about Shapiro test
    )


# --- New Route for Visualization Page ---
@app.route('/visualize')
@login_required
def visualize_data():
    """Generates and displays various plots for data visualization, grouped by type."""
    df = get_dataframe_from_session()
    if df is None or df.empty:
        flash("No data loaded or data is empty. Cannot visualize.", "warning")
        return redirect(url_for('clean_data_interface'))

    if not SCIPY_AVAILABLE and not hasattr(visualize_data, '_scipy_warning_logged'):
        app.logger.warning("scipy library not found during visualize_data execution. Clustered heatmap will not be available.")
        visualize_data._scipy_warning_logged = True

    plot_groups = {
        'distributions': {'title': 'Numerical Distributions', 'plots': [], 'messages': []},
        'categorical_analysis': {'title': 'Categorical Analysis', 'plots': [], 'messages': []},
        'correlation_matrix': {'title': 'Correlation & Heatmaps', 'plots': [], 'messages': []},
        'relationships': {'title': 'Bivariate Relationships (Sampled)', 'plots': [], 'messages': []},
        'time_series_analysis': {'title': 'Time Series Analysis (Sampled)', 'plots': [], 'messages': []}, # Title remains general
        'aggregated_summaries': {'title': 'Aggregated Summaries by Category', 'plots': [], 'messages': []}
    }
    error_message = None
    plot_config = {'displayModeBar': False, 'responsive': True}

    # General limits
    max_plots_per_type = 8
    max_histograms = 6
    max_kde_plots = 6
    max_cat_bar_plots = 6
    max_pie_charts = 6
    max_scatter_plots = 6
    max_box_violin_plots = 6
    max_aggregated_bar_charts = 6
    max_categories_for_plot = 20
    
    # Specific for time series
    max_individual_ts_plots = 6 # Limit for smaller individual plots

    sample_size = min(1000, len(df))
    df_sample = df.sample(n=sample_size, random_state=42) if len(df) > sample_size else df.copy()

    try:
        numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime', 'datetime64[ns]', 'datetimetz']).columns.tolist()
        bool_cols = df.select_dtypes(include=np.bool_).columns.tolist()
        constant_cols = [col for col in df.columns if df[col].nunique(dropna=False) <= 1]

        numeric_cols_plot = [col for col in numeric_cols if col not in bool_cols and col not in constant_cols]
        categorical_cols_plot = [col for col in categorical_cols if col not in constant_cols]
        low_card_categorical_cols = [
            col for col in categorical_cols_plot if df[col].nunique(dropna=False) <= max_categories_for_plot
        ]
        
        def add_plot(group_key, fig_html, is_html_string=True):
            if not is_html_string:
                fig_html = pio.to_html(fig_html, full_html=False, include_plotlyjs=False, config=plot_config)
            plot_groups[group_key]['plots'].append(fig_html)

        # --- 1. Distributions (Histograms & Density Plots) ---
        dist_plot_count_hist = 0
        dist_plot_count_kde = 0
        if not numeric_cols_plot:
            plot_groups['distributions']['messages'].append("No suitable numerical columns for distribution plots.")
        else:
            for col in numeric_cols_plot:
                if dist_plot_count_hist < max_histograms:
                    try:
                        fig = px.histogram(df, x=col, title=f'Histogram: {col}', marginal="box", opacity=0.8, color_discrete_sequence=['#636EFA'])
                        fig.update_layout(height=350, title_x=0.5, margin=dict(l=40, r=20, t=50, b=40))
                        add_plot('distributions', fig, is_html_string=False)
                        dist_plot_count_hist += 1
                    except Exception as e:
                        app.logger.warning(f"Histogram error for {col}: {e}")
                        plot_groups['distributions']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error for Histogram: <code>{col}</code>.</div>")
            
            for col in numeric_cols_plot:
                if dist_plot_count_kde < max_kde_plots:
                    try:
                        col_data = df[col].dropna()
                        if len(col_data) < 2: continue 
                        fig = ff.create_distplot([col_data.tolist()], [col], show_hist=False, show_rug=False, colors=['#00CC96'])
                        fig.update_layout(title_text=f'Density Plot (KDE): {col}', height=350, title_x=0.5, margin=dict(l=40, r=20, t=50, b=40))
                        add_plot('distributions', fig, is_html_string=False)
                        dist_plot_count_kde +=1
                    except Exception as e:
                        app.logger.warning(f"KDE plot error for {col}: {e}")
                        plot_groups['distributions']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error for KDE: <code>{col}</code>.</div>")
        if dist_plot_count_hist == 0 and dist_plot_count_kde == 0 and numeric_cols_plot:
             plot_groups['distributions']['messages'].append("Could not generate any distribution plots.")

        # --- 2. Categorical Analysis (Count Plots & Pie Charts) ---
        cat_bar_plot_count = 0
        pie_chart_count = 0
        if not categorical_cols_plot:
            plot_groups['categorical_analysis']['messages'].append("No suitable categorical columns for analysis.")
        else:
            for col in categorical_cols_plot:
                if cat_bar_plot_count < max_cat_bar_plots:
                    n_unique = df[col].nunique(dropna=False)
                    if n_unique > max_categories_for_plot * 1.5: 
                        plot_groups['categorical_analysis']['messages'].append(f"<small>Skipping count plot for <code>{col}</code> (high cardinality: {n_unique}).</small>")
                        continue
                    try:
                        counts = df[col].value_counts(dropna=False).reset_index().head(int(max_categories_for_plot * 1.5))
                        counts.columns = ['Category', 'Count']
                        fig = px.bar(counts, y='Category', x='Count', title=f'Counts: {col}', text_auto='.2s', orientation='h', color_discrete_sequence=px.colors.qualitative.Plotly)
                        fig.update_layout(height=max(250, 20 * min(n_unique, int(max_categories_for_plot*1.5))), title_x=0.5, yaxis={'categoryorder':'total ascending'})
                        add_plot('categorical_analysis', fig, is_html_string=False)
                        cat_bar_plot_count += 1
                    except Exception as e:
                        app.logger.warning(f"Count plot error for {col}: {e}")
                        plot_groups['categorical_analysis']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error for Count Plot: <code>{col}</code>.</div>")

            for col in low_card_categorical_cols:
                if pie_chart_count < max_pie_charts:
                    try:
                        counts = df[col].value_counts(dropna=False).reset_index()
                        counts.columns = ['Category', 'Count']
                        if counts['Count'].sum() == 0: 
                            plot_groups['categorical_analysis']['messages'].append(f"<small>Skipping pie chart for <code>{col}</code> (all counts are zero).</small>")
                            continue
                        fig = px.pie(counts, names='Category', values='Count', title=f'Proportions: {col}', hole=0.3, color_discrete_sequence=px.colors.qualitative.Pastel)
                        fig.update_layout(height=400, title_x=0.5, margin=dict(l=20, r=20, t=50, b=20))
                        add_plot('categorical_analysis', fig, is_html_string=False)
                        pie_chart_count += 1
                    except Exception as e:
                        app.logger.warning(f"Pie chart error for {col}: {e}")
                        plot_groups['categorical_analysis']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error for Pie Chart: <code>{col}</code>.</div>")
        if cat_bar_plot_count == 0 and pie_chart_count == 0 and categorical_cols_plot:
            plot_groups['categorical_analysis']['messages'].append("Could not generate any categorical analysis plots.")

        # --- 3. Correlation & Heatmaps ---
        if len(numeric_cols_plot) >= 2:
            try:
                corr_matrix_pearson = df[numeric_cols_plot].corr(method='pearson').round(2)
                fig_pearson = px.imshow(corr_matrix_pearson, text_auto=True, aspect="auto",
                                        color_continuous_scale='RdBu_r', zmin=-1, zmax=1,
                                        title="Pearson Correlation Heatmap (Linear)")
                fig_pearson.update_layout(height=max(400, 30 * len(numeric_cols_plot)), title_x=0.5)
                add_plot('correlation_matrix', fig_pearson, is_html_string=False)
            except Exception as e:
                app.logger.warning(f"Pearson correlation heatmap error: {e}")
                plot_groups['correlation_matrix']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error generating Pearson heatmap.</div>")

            if SCIPY_AVAILABLE: 
                try:
                    pairwise_distances = distance.pdist(corr_matrix_pearson.fillna(0).values) 
                    linkage = hierarchy.linkage(pairwise_distances, method='average')
                    dendro = hierarchy.dendrogram(linkage, no_plot=True, color_threshold=-1)
                    ordered_cols = [corr_matrix_pearson.columns[i] for i in dendro['leaves']]
                    corr_matrix_clustered = corr_matrix_pearson.loc[ordered_cols, ordered_cols]
                    fig_clustered = px.imshow(corr_matrix_clustered, text_auto=True, aspect="auto",
                                              color_continuous_scale='RdBu_r', zmin=-1, zmax=1,
                                              title="Clustered Pearson Correlation Heatmap")
                    fig_clustered.update_layout(height=max(400, 30 * len(numeric_cols_plot)), title_x=0.5)
                    add_plot('correlation_matrix', fig_clustered, is_html_string=False)
                except Exception as e:
                    app.logger.warning(f"Clustered Pearson heatmap error: {e}")
                    plot_groups['correlation_matrix']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error generating Clustered Pearson heatmap: {str(e)[:100]}...</div>")
            else:
                plot_groups['correlation_matrix']['messages'].append("<small>Clustered heatmap skipped: <code>scipy</code> library not available.</small>")

            try:
                corr_matrix_lower_triangle = corr_matrix_pearson.copy()
                mask = np.triu(np.ones_like(corr_matrix_lower_triangle, dtype=bool), k=1)
                corr_matrix_lower_triangle[mask] = np.nan
                fig_triangle = px.imshow(corr_matrix_lower_triangle, text_auto=True, aspect="auto",
                                         color_continuous_scale='RdBu_r', zmin=-1, zmax=1,
                                         title="Lower Triangle Pearson Correlation")
                fig_triangle.update_layout(height=max(400, 30 * len(numeric_cols_plot)), title_x=0.5)
                add_plot('correlation_matrix', fig_triangle, is_html_string=False)
            except Exception as e:
                app.logger.warning(f"Triangle Pearson heatmap error: {e}")
                plot_groups['correlation_matrix']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error generating Triangle Pearson heatmap.</div>")
            
            numeric_cols_for_spearman = [col for col in numeric_cols_plot if df[col].nunique(dropna=False) > 2]
            if len(numeric_cols_for_spearman) >= 2:
                try:
                    corr_matrix_spearman = df[numeric_cols_for_spearman].corr(method='spearman').round(2)
                    fig_spearman = px.imshow(corr_matrix_spearman, text_auto=True, aspect="auto",
                                             color_continuous_scale='PuOr', zmin=-1, zmax=1,
                                             title="Spearman Rank Correlation Heatmap (Monotonic)")
                    fig_spearman.update_layout(height=max(400, 30 * len(numeric_cols_for_spearman)), title_x=0.5)
                    add_plot('correlation_matrix', fig_spearman, is_html_string=False)
                except Exception as e:
                    app.logger.warning(f"Spearman correlation heatmap error: {e}")
                    plot_groups['correlation_matrix']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error generating Spearman heatmap.</div>")
            else:
                plot_groups['correlation_matrix']['messages'].append("<small>Spearman heatmap skipped: Not enough non-binary numerical columns.</small>")
        else:
            plot_groups['correlation_matrix']['messages'].append("Not enough numerical columns (at least 2) for correlation heatmaps.")

        # --- 4. Bivariate Relationships (Scatter, Box, Violin - Sampled) ---
        scatter_plot_count = 0
        box_violin_plot_count = 0
        plot_pairs = set() 

        if numeric_cols_plot and (len(numeric_cols_plot) >=2 or low_card_categorical_cols):
            if len(numeric_cols_plot) >= 2:
                color_col_candidate = low_card_categorical_cols[0] if low_card_categorical_cols else None
                for i in range(len(numeric_cols_plot)):
                    if scatter_plot_count >= max_scatter_plots: break
                    for j in range(i + 1, len(numeric_cols_plot)):
                        if scatter_plot_count >= max_scatter_plots: break
                        col1, col2 = numeric_cols_plot[i], numeric_cols_plot[j]
                        pair = tuple(sorted((col1, col2, 'scatter')))
                        if pair in plot_pairs: continue
                        try:
                            fig_args = {'x': col1, 'y': col2, 'title': f'{col1} vs. {col2}', 'trendline': "ols", 'opacity': 0.6, 'color_discrete_sequence': ['#EF553B']}
                            if color_col_candidate and color_col_candidate != col1 and color_col_candidate != col2 : 
                                fig_args['color'] = color_col_candidate
                                fig_args['title'] += f' (Color: {color_col_candidate})'
                            fig = px.scatter(df_sample, **fig_args)
                            fig.update_layout(height=350, title_x=0.5, margin=dict(l=40, r=20, t=60, b=40))
                            add_plot('relationships', fig, is_html_string=False)
                            scatter_plot_count += 1; plot_pairs.add(pair)
                        except Exception as e:
                            app.logger.warning(f"Scatter plot error {col1} vs {col2}: {e}")
                            plot_groups['relationships']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error for Scatter: <code>{col1}</code> vs <code>{col2}</code>.</div>")
            
            plot_types_for_cat_num = [('Box Plot', px.box, 'box', '#AB63FA'), ('Violin Plot', px.violin, 'violin', '#FFA15A')]
            for plot_title_prefix, plot_func, plot_key_suffix, default_color in plot_types_for_cat_num:
                for num_col in numeric_cols_plot:
                    if box_violin_plot_count >= max_box_violin_plots: break
                    for cat_col in low_card_categorical_cols:
                        if box_violin_plot_count >= max_box_violin_plots: break
                        if num_col == cat_col: continue
                        pair = tuple(sorted((num_col, cat_col, plot_key_suffix)))
                        if pair in plot_pairs: continue
                        try:
                            df_sample_copy = df_sample.copy()
                            df_sample_copy[cat_col] = df_sample_copy[cat_col].fillna('Missing').astype(str)
                            fig = plot_func(df_sample_copy, x=cat_col, y=num_col, title=f'{plot_title_prefix}: {num_col} by {cat_col}', 
                                            points=False if plot_func == px.box else 'all', 
                                            color=cat_col, 
                                            color_discrete_sequence=px.colors.qualitative.Vivid) 
                            fig.update_layout(height=400, title_x=0.5, margin=dict(l=40, r=20, t=50, b=40), showlegend=False) 
                            add_plot('relationships', fig, is_html_string=False)
                            box_violin_plot_count += 1; plot_pairs.add(pair)
                        except Exception as e:
                            app.logger.warning(f"{plot_title_prefix} error {num_col} vs {cat_col}: {e}")
                            plot_groups['relationships']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error for {plot_title_prefix}: <code>{num_col}</code> vs <code>{cat_col}</code>.</div>")
        
        if scatter_plot_count == 0 and box_violin_plot_count == 0 and numeric_cols_plot:
             plot_groups['relationships']['messages'].append("No suitable column pairs for relationship plots.")


        # --- 5. Time Series Analysis (Line Charts - Sampled) ---
        ts_plot_count = 0 
        if not datetime_cols:
            plot_groups['time_series_analysis']['messages'].append("No datetime columns found for time series analysis.")
        elif not numeric_cols_plot:
            plot_groups['time_series_analysis']['messages'].append("No numerical columns to plot against time.")
        else:
            time_col_to_use = datetime_cols[0] 
            for dt_col_candidate in datetime_cols:
                if df_sample[dt_col_candidate].nunique() > 0.8 * len(df_sample): 
                    time_col_to_use = dt_col_candidate
                    break
            
            df_time_sorted_sample = df_sample.sort_values(by=time_col_to_use).copy()
            all_numeric_cols_for_ts = [col for col in numeric_cols_plot if col != time_col_to_use]
            
            if not all_numeric_cols_for_ts:
                 plot_groups['time_series_analysis']['messages'].append(f"No suitable numeric columns found to plot against <code>{time_col_to_use}</code>.")
            else:
                # Main Combined Plot (Full Width)
                try:
                    num_vars_to_plot = len(all_numeric_cols_for_ts)
                    if num_vars_to_plot == 1:
                        title_text = f'Time Series: {all_numeric_cols_for_ts[0]} over {time_col_to_use}'
                    elif num_vars_to_plot <= 5:
                        title_text = f'Time Series: {", ".join(all_numeric_cols_for_ts)} over {time_col_to_use}'
                    else:
                        title_text = f'Time Series: {num_vars_to_plot} Numeric Variables over {time_col_to_use}'
                    
                    fig_main_ts = px.line(df_time_sorted_sample, x=time_col_to_use, y=all_numeric_cols_for_ts,
                                          title=title_text,
                                          markers=True if len(df_time_sorted_sample) < 50 else False)
                    fig_main_ts.update_layout(height=500, title_x=0.5, margin=dict(l=40, r=20, t=60, b=40))
                    add_plot('time_series_analysis', fig_main_ts, is_html_string=False)
                    ts_plot_count += 1
                except Exception as e:
                    app.logger.warning(f"Main Time Series line chart error: {e}")
                    plot_groups['time_series_analysis']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error generating main time series chart. Details: {str(e)[:100]}</div>")

                # Individual Smaller Plots
                individual_ts_generated = 0
                for num_col in all_numeric_cols_for_ts:
                    if individual_ts_generated >= max_individual_ts_plots:
                        plot_groups['time_series_analysis']['messages'].append(f"<small>...showing first {max_individual_ts_plots} individual time series plots.</small>")
                        break
                    try:
                        fig_individual_ts = px.line(df_time_sorted_sample, x=time_col_to_use, y=num_col,
                                                    title=f'Time Series: {num_col} over {time_col_to_use}',
                                                    markers=True if len(df_time_sorted_sample) < 100 else False)
                        fig_individual_ts.update_layout(height=350, title_x=0.5, margin=dict(l=40, r=20, t=50, b=40))
                        add_plot('time_series_analysis', fig_individual_ts, is_html_string=False)
                        individual_ts_generated += 1
                        ts_plot_count +=1 # Also counts towards a general ts plot counter if needed
                    except Exception as e:
                        app.logger.warning(f"Individual Time Series line chart error for {num_col}: {e}")
                        plot_groups['time_series_analysis']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error for TS: <code>{num_col}</code>.</div>")
        
        if ts_plot_count == 0 and datetime_cols and numeric_cols_plot:
            if not plot_groups['time_series_analysis']['messages']: 
                plot_groups['time_series_analysis']['messages'].append("Could not generate any time series plots for the selected data.")


        # --- 6. Aggregated Summaries by Category (Bar Charts) ---
        agg_plot_count = 0
        if not low_card_categorical_cols or not numeric_cols_plot:
            plot_groups['aggregated_summaries']['messages'].append("Needs at least one low-cardinality categorical and one numerical column for aggregated summaries.")
        else:
            for cat_col in low_card_categorical_cols[:max_aggregated_bar_charts]: # Limit categorical columns processed
                if agg_plot_count >= max_plots_per_type: break 
                
                num_cols_to_agg_for_this_cat = [nc for nc in numeric_cols_plot if nc != cat_col][:3] # Take first 3 numeric not same as cat_col
                
                for num_col in num_cols_to_agg_for_this_cat:
                    if agg_plot_count >= max_plots_per_type: break
                    
                    pair = tuple(sorted((cat_col, num_col, 'agg_bar')))
                    if pair in plot_pairs: continue # Avoid re-plotting exact same agg if logic allows

                    try:
                        # Using df_sample for potentially faster aggregation on large datasets
                        agg_data = df_sample.groupby(cat_col, dropna=False)[num_col].mean().reset_index()
                        agg_data = agg_data.dropna(subset=[num_col])
                        if agg_data.empty: continue
                        agg_data = agg_data.sort_values(by=num_col, ascending=False)
                        
                        fig = px.bar(agg_data, x=cat_col, y=num_col, title=f'Mean of {num_col} by {cat_col}',
                                     color=num_col, 
                                     color_continuous_scale=px.colors.sequential.Viridis, 
                                     text_auto='.2s')
                        fig.update_layout(height=400, title_x=0.5, margin=dict(l=40, r=20, t=50, b=40), 
                                          xaxis_title=cat_col, yaxis_title=f'Mean({num_col})')
                        fig.update_xaxes(type='category') # Ensure x-axis is treated as categorical
                        add_plot('aggregated_summaries', fig, is_html_string=False)
                        agg_plot_count += 1; plot_pairs.add(pair)
                    except Exception as e:
                        app.logger.warning(f"Aggregated bar chart error for {num_col} by {cat_col}: {e}")
                        plot_groups['aggregated_summaries']['messages'].append(f"<div class='alert alert-warning alert-sm p-1 small'>Error for Aggregated Bar: <code>{num_col}</code> by <code>{cat_col}</code>.</div>")
        
        if agg_plot_count == 0 and low_card_categorical_cols and numeric_cols_plot:
            if not plot_groups['aggregated_summaries']['messages']:
                plot_groups['aggregated_summaries']['messages'].append("Could not generate any aggregated summary plots.")

    except Exception as e:
        error_message = f"A critical error occurred while generating visualizations: {str(e)}"
        app.logger.error(f"Critical Error in /visualize route: {e}", exc_info=True)
        if error_message:
            for group_key_loop in plot_groups.keys(): # Use different variable name to avoid conflict
                if not plot_groups[group_key_loop]['plots'] and not plot_groups[group_key_loop]['messages']:
                    plot_groups[group_key_loop]['messages'].append(f"<div class='alert alert-danger alert-sm p-1 small'>A global error prevented plots for this section. Details: {str(e)[:100]}</div>")


    return render_template(
        'visualize.html',
        plot_groups=plot_groups,
        error_message=error_message,
        source_info=session.get('source_info', 'Unknown Source')
    )

# --- Run Application ---
# In app.py, find the final block of code
# if __name__ == '__main__':
#     from waitress import serve
#     print("Starting DataWarp server on http://0.0.0.0:8080")
#     serve(app, host="0.0.0.0", port=8080)
# ------------------------------------

# --- REPLACE it with this new, updated block ---
def open_browser():
    """
    Opens the default web browser to the specified URL.
    """
    # Note: We use 127.0.0.1 because it's the standard address for the local machine.
    # 0.0.0.0 is for listening on all available network interfaces.
    url = "http://127.0.0.1:8080"
    print(f"Opening browser to {url}...")
    webbrowser.open_new(url)

if __name__ == '__main__':
    from waitress import serve

    # Configure the standard Python logger to show messages in the console
    # This format will look similar to Flask's default logger
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )

    # Define the host and port
    HOST = "0.0.0.0"
    PORT = 8080
    
    # --- Start background threads for auto-tasks ---

    # 1. Schedule the browser to open 1 second after the script starts
    threading.Timer(1, open_browser).start()
    
    # 2. Schedule the update check to run 3 seconds after startup.
    #    This gives the app time to initialize before making web requests.
    #    Using a Timer runs the task just once after the delay.
    update_check_thread = threading.Timer(3.0, check_for_updates)
    update_check_thread.daemon = True # Allows app to exit even if thread is running
    update_check_thread.start()
    
    # --- Start the main server ---
    
    logging.info(f"Starting DataWarp server v{__version__} on http://{HOST}:{PORT}")
    logging.info("The application will open in your default browser automatically.")
    
    # Start the production server (this is a blocking call)
    serve(app, host=HOST, port=PORT, threads=10)