from datetime import datetime
import json
import logging
import math
import os
import queue
import re
import threading
import time

from bs4 import BeautifulSoup as bs
import pandas as pd
import pygame
import requests
from flask import Flask, render_template, jsonify, make_response, send_from_directory, request, flash
from flask_caching import Cache
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo

# Set logging level to INFO to reduce verbosity
logging.basicConfig(level=logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)  # Suppress urllib3 debug logs
logging.getLogger("werkzeug").setLevel(logging.WARNING)  # Suppress werkzeug debug logs

logger = logging.getLogger(__name__)
is_muted = False  # Global flag to track mute status
last_alert_time = 0  # Track last played time
countdown_timer = 120  # Initialize countdown timer

def play_alert():
    global last_alert_time, is_muted
    if is_muted or countdown_timer > 0:
        return  # Do not play sound if muted

    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sound_path = os.path.join(base_dir, "static", "alert.mp3")

        logger.info(f"Attempting to play alert sound from: {sound_path}")

        if not os.path.exists(sound_path):
            logger.error(f"Alert sound file does not exist at: {sound_path}")
            return

        current_time = time.time()
        if current_time - last_alert_time < 20:
            return

        last_alert_time = current_time
        pygame.mixer.stop()
        beep_sound = pygame.mixer.Sound(sound_path)
        beep_sound.play()

    except Exception as e:
        logger.error(f"Error playing alert sound: {e}")
app = Flask(__name__, static_url_path='/static', static_folder='static')


cache = Cache(app)
pygame.mixer.init()  # Initialize Pygame mixer
play_alert()  # Play sound when the application is loading

# Add formatNumber as a Jinja2 filter
@app.template_filter('formatNumber')
def format_number(num):
    if num is None:
        return ''
    
    # Handle potential score - round to nearest integer
    if num > 1000:  # Potential scores are typically large numbers
        return str(round(num))
    
    # For percentages and small numbers, keep 2 decimal places
    if isinstance(num, (int, float)):
        return f"{num:.2f}" if num < 100 else str(round(num))
    
    return str(num)

# Add format_number as a Jinja2 filter
def format_number(value, column_type='default'):
    if value is None:
        return '-'
    
    try:
        num = float(value)
        # print(f"Column: {column_type}, Raw Value: {num}")  # Debugging
        
        # Format Close with two decimal places
        if column_type == 'close':
            formatted_value = f"{num:.2f}"
            # print(f"Formatted Close: {formatted_value}")  # Debugging
            return formatted_value  

        # Format Change % with two decimal places and add percentage sign
        if column_type == 'change_percent':
            formatted_value = f"{num:.2f}%"  # Ensure two decimal places
            # print(f"Formatted Change %: {formatted_value}")  # Debugging
            return formatted_value  

        # Format Volume as an integer
        # Format Volume as an integer
        if column_type == 'volume':
            return str(round(num))  # Round to nearest integer and return as string
        
        # Format Score as an integer
        if column_type == 'score':
            return str(round(num))  # Round to nearest integer and return as string  # Convert to integer and return as string
         
        return f"{num:.2f}"  # Default case to format to two decimal places
    except (ValueError, TypeError):
        return str(value)

# Register the filter
app.jinja_env.filters['format_number'] = format_number

# Integrate backend support for Jinja Quick UI Kit components
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# Define the scan conditions
conditions = [
    {
    "name": "Volume Shocker",
    "link": "https://chartink.com/screener/copy-volume-rahim",
    "chart_link": "https://chartink.com/stocks-new?symbol=",
    "scan_clause": """( {57960} ( 
        latest volume > 1 day ago volume and 
        1 day ago volume > 2 days ago volume and 
        latest close > 1 day ago close and 
        1 day ago close > 2 days ago close and 
        latest volume > 1000000 and 
        1 day ago volume > 500000 and 
        latest close > latest open * 1.03 and 
        [=1] 5 minute close < [=1] 5 minute open * 1.03 and 
        latest open > 1 day ago close 
    ) )"""
},
    {
    "name": "85 Volume Shock",
    "scan_clause": """( {57960} ( 
        latest volume > 1 day ago volume * 0.85 and 
        1 day ago volume > 2 days ago volume and 
        latest close > 1 day ago close and 
        1 day ago close > 2 days ago close and 
        latest volume > 1000000 and 
        1 day ago volume > 500000 and 
        latest close > latest open * 1.03 and 
        [=1] 5 minute close < [=1] 5 minute open * 1.03 and 
        latest open > 1 day ago close 
    ) )"""
}

]

# Global variables
data_queue = queue.Queue()
last_update_time = None
update_thread = None
running = True
thread_started = False
scan_results = {}
previous_scores = {}  # Initialize previous_scores here

# Global variable to track mute status
is_muted = False

def load_settings():
    """
    Load settings from JSON file
    """
    default_settings = {
        "mute_status": False,
        "app_selected": 'app',
        "conditions": [c['name'] for c in conditions],
        "browser": '0',
        "app": '1'
    }

    try:
        if os.path.exists('db.json'):
            with open('db.json', 'r') as f:
                settings = json.load(f)
                return settings
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
    
    return default_settings

def save_settings(settings):
    """
    Save settings to JSON file
    """
    try:
        with open('db.json', 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving settings: {e}")

# Load existing settings on startup
settings = load_settings()
is_muted = settings.get('mute_status', False)  # Default to False if not set

@app.route('/clear_cache')
def clear_cache():
    cache.clear()
    return "Cache cleared!"

@app.route('/update-mute-status', methods=['POST'])
def update_mute_status():
    global is_muted
    data = request.get_json()
    is_muted = data.get('isMuted', False)
    return jsonify({'status': 'success', 'isMuted': is_muted})

#@app.route('/get-mute-status', methods=['GET'])
#def get_mute_status():
#    return jsonify({'isMuted': is_muted})

# When the app starts, load the mute status
# settings = load_settings()
# is_muted = settings.get('mute_status', False)
# logger.info(f"Initial mute status loaded: {is_muted}")

def fetch_and_process_data(session, condition):
    """Fetch and process stock data using the provided session"""
    url = "https://chartink.com/screener/process"
    # logger.info(f"Fetching data for condition: {condition['name']}")
    
    try:
        # Get CSRF token
        # logger.info("Fetching CSRF token...")
        r_data = session.get(url)
        r_data.raise_for_status()
        soup = bs(r_data.content, "lxml")
        meta = soup.find("meta", {"name": "csrf-token"})
        if not meta:
            logger.error("Could not find CSRF token")
            return {"error": "Could not find CSRF token"}
        
        header = {"x-csrf-token": meta["content"]}
        # logger.info("CSRF token obtained successfully")

        try:
            # logger.info(f"Request URL: {url}")
            # logger.info(f"Request Headers: {header}")
            # logger.info(f"Request Data: {{'scan_clause': {condition['scan_clause']}}}")
            
            response = session.post(url, headers=header, data={"scan_clause": condition["scan_clause"]})
            response.raise_for_status()
            
            data = response.json()
            # logger.debug(f"Response Status: {response.status_code}")
            # logger.debug(f"Response Headers: {dict(response.headers)}")
            # logger.debug(f"Response Data: {data}")
            
            if 'scan_error' in data:
                logger.error(f"Scan error for {condition['name']}: {data['scan_error']}")
                logger.error(f"Condition that caused error: {condition['scan_clause']}")
                return []
            
            if 'data' not in data:
                logger.error(f"Invalid response format for {condition['name']}: {data}")
                return []
            
            stock_list = pd.DataFrame(data["data"])

            if not stock_list.empty:
                stock_list["per_chg"] = pd.to_numeric(stock_list["per_chg"])
                stock_list["potential_score"] = stock_list["per_chg"] * stock_list["close"]
                
                if condition["name"] == "STRONG":
                    sorted_stock_list = stock_list.sort_values(by="potential_score", ascending=False).head(10)
                    
                elif condition["name"] == "HARSH SELL STOCKS":
                    sorted_stock_list = stock_list.sort_values(by="potential_score", ascending=True)  # Sort by potential_score ascending
                
                elif condition["name"] == "STRONG STOCKS NEGATIVE":
                    sorted_stock_list = stock_list.sort_values(by="potential_score", ascending=True)  # Sort by potential_score ascending
                
                else:
                    sorted_stock_list = stock_list.sort_values(by="potential_score", ascending=False)
                
                # Convert DataFrame to dict for JSON serialization
                return sorted_stock_list.head(10).to_dict('records')
            else:
                # logger.info(f"No stocks found for {condition['name']}")
                return []
        
        except Exception as e:
            logger.error(f"Error processing {condition['name']}: {str(e)}")
            return {"error": str(e)}

    except Exception as e:
        logger.error(f"Error in fetch_and_process_data: {str(e)}")
        return {"error": str(e)}

def fetch_data():
    """
    Fetch stock data from various sources and process them.
    Play alert sound after auto-refresh.
    """
    global last_alert_time, scan_results
    
    # Ensure we're in an application context
    if not 'current_app' in globals() or current_app is None:
        with app.app_context():
            return _fetch_data_impl()
    return _fetch_data_impl()

def _fetch_data_impl(selected_conditions=None):
    """Implementation of fetch_data that assumes app context exists"""
    global last_alert_time, scan_results
    try:
        logger.info("Starting data fetch and process...")
        # If called from background, pass selected_conditions (default to all if None)
        if selected_conditions is None:
            selected_conditions = [cond['name'] for cond in conditions]
        current_results = get_scan_results_internal(selected_conditions)
        if current_results:
            # Play alert sound if not muted and not on cooldown
            current_time = time.time()
            if not is_muted and (current_time - last_alert_time) > 300:  # 5 minutes cooldown
                play_alert()
                last_alert_time = current_time
        return current_results
    except Exception as e:
        logger.error(f"Error in fetch_data: {e}")
        return None

def filter_stocks(stocks, condition):
    # This is a placeholder. In a real implementation, you would filter stocks based on the condition
    # For now, we'll just return all stocks
    return stocks

def update_data():
    """Background thread function to update stock data every 2 minutes"""
    while True:
        try:
            logger.info("Starting background data update...")
            # Create application context
            with app.app_context():
                try:
                    fetch_data()
                    logger.info("Background data update completed")
                except Exception as e:
                    logger.error(f"Error in fetch_data: {e}")
                    # If there's an error, try to reinitialize the app context
                    try:
                        app.app_context().push()
                        fetch_data()
                    except Exception as e2:
                        logger.error(f"Retry failed in update_data: {e2}")
        except Exception as e:
            logger.error(f"Error in update_data: {e}")
        time.sleep(120)  # Wait for 2 minutes before next update

def categorize_stocks():
    """Categorize stocks into Buy and Sell suggestions, and detect significant score jumps."""
    global scan_results, previous_scores
    buy_suggestions = []
    sell_suggestions = []
    alert_triggered = False

    for condition, stocks in scan_results.items():
        for stock in stocks:
            stock_code = stock["nsecode"]
            new_score = stock.get("potential_score", 0)
            stock_price = stock.get("close", 0)  # Get stock price

            # **Exclude stocks with a close price above 2250**
            if stock_price > 2250:
                continue  # Skip this stock

            # Check if we have a previous score for this stock
            old_score = previous_scores.get(stock_code, 0)

            # Detect a significant jump (customize the threshold, e.g., 20% increase)
            if new_score > old_score * 1.2:  # 20% increase threshold
                alert_triggered = True  # We will trigger the beep sound

            # Store the new score for the next refresh
            previous_scores[stock_code] = new_score

            # Categorize as Buy/Sell
            if stock.get("per_chg", 0) > 0:
                buy_suggestions.append(stock)
            else:
                sell_suggestions.append(stock)

    # Limit to top 10 results
    buy_suggestions = sorted(buy_suggestions, key=lambda x: x["potential_score"], reverse=True)[:20]
    sell_suggestions = sorted(sell_suggestions, key=lambda x: x["potential_score"])[:20]

    return buy_suggestions, sell_suggestions


import pygame
import os

# Initialize pygame and its mixer
try:
    pygame.mixer.quit()  # Ensure clean state
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
    logger.info("Pygame mixer initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize pygame mixer: {e}")

last_alert_time = 0  # Track last played time



# def play_beep():
#     """Play alert sound when a stock jumps significantly."""
#     global is_muted
#     if is_muted:
#         # logger.info("Sound is muted. Skipping beep.")
#         return

#     try:
#         sound_path = "E:/vankai/static/beep.mp3"  # Specify the beep sound file path

#         if not os.path.exists(sound_path):
#             logger.error(f"Beep sound file not found: {sound_path}")
#         pygame.mixer.init()
#         beep_sound = pygame.mixer.Sound(sound_path)
#         beep_sound.play()
#         # logger.info("Beep sound played!")
#     except Exception as e:
#         logger.error(f"Error playing beep sound: {e}")

@app.route('/get-scan-results')
def get_scan_results():
    """Get scan results from all conditions and return as JSON"""
    selected_conditions = request.args.getlist('condition')
    if not selected_conditions:
        logger.warning("No conditions selected")
        return jsonify({'error': 'No conditions selected'}), 400
    result = get_scan_results_internal(selected_conditions)
    response = make_response(jsonify(result))
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def get_scan_results_internal(selected_conditions):
    global scan_results
    try:
        logger.info(f"Selected conditions: {selected_conditions}")
        all_results = {}
        name_variations = {
            "STRONG STOCKS": "STRONG STOCKS POSITIVE",
            "STRONG STOCKS POSITIVE": "STRONG STOCKS POSITIVE"
        }
        if scan_results is None:
            logger.warning("scan_results is None, attempting to fetch data")
            fetch_data()
        for condition in selected_conditions:
            if condition == 'on':
                continue
            normalized_condition = name_variations.get(condition, condition)
            stocks = scan_results.get(normalized_condition, [])
            logger.info(f"Condition: {normalized_condition}, Stocks found: {len(stocks)}")
            if stocks:
                all_results[normalized_condition] = stocks
        if not all_results:
            logger.warning("No stocks found for any selected conditions")
        return all_results
    except Exception as e:
        logger.error(f"Error in get_scan_results_internal: {e}", exc_info=True)
        return {'error': str(e)}

DB_FILE = 'db.json'

def get_default_settings():
    """Get default settings structure"""
    return {
        "mute_status": False,
        'app_selected': 'app',
        'conditions': [c['name'] for c in conditions],
        'browser': '0',
        'app': '1'
    }

@app.route('/db.json')
def serve_db_json():
    return send_from_directory('.', 'db.json')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/')
def index():
    fetch_data()  # Ensure latest data is fetched
    settings = load_settings()
    selected_conditions = settings.get('conditions', [])

    # If no conditions are selected, show a message to select conditions
    if not selected_conditions:
        flash_message = {
            'type': 'info',
            'icon': 'fa-info-circle',
            'title': 'No Conditions Selected',
            'message': 'Please select one or more conditions from the Conditions menu to view stock data.'
        }
    else:
        flash_message = None

    # Categorize stocks into Buy/Sell
    buy_suggestions, sell_suggestions = categorize_stocks()

    # Only include selected conditions
    conditions_with_stocks = [
        {**condition, "stocks": scan_results.get(condition["name"], [])}
        for condition in conditions
        if condition["name"] in selected_conditions
    ]

    return render_template(
        'index.html',
        conditions=conditions_with_stocks,
        flash_message=flash_message,
        buy_suggestions=buy_suggestions,
        sell_suggestions=sell_suggestions
    )

@app.route('/get-settings')
def get_settings():
    """Get current application settings"""
    try:
        settings = load_settings()
        return jsonify(settings)
    except Exception as e:
        logger.error(f"Error in get_settings: {str(e)}")
        return jsonify(get_default_settings())

@app.route('/update-settings', methods=['POST'])
def update_settings():
    """Update application settings"""
    try:
        data = request.get_json()
        current_settings = load_settings()
        
        # Update only allowed fields
        if 'conditions' in data:
            current_settings['conditions'] = data['conditions']
        
        if 'selected_option' in data:
            current_settings['app_selected'] = data['selected_option']
            current_settings['browser'] = '1' if data['selected_option'] == 'browser' else '0'
            current_settings['app'] = '1' if data['selected_option'] == 'app' else '0'
        
        # Save clean settings
        with open(DB_FILE, 'w') as f:
            # Lock the file for writing
            # msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                json.dump(current_settings, f, indent=4)
            finally:
                # Always unlock the file
                # msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                pass
        
        return jsonify({'success': True, 'message': 'Settings updated successfully'}), 200
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Instead of creating a separate route, you can directly use this conditions list
# in other parts of your application where you need to reference these screening conditions

@app.route('/conditions')
def get_conditions():
    # Simply return the predefined conditions list
    return jsonify(conditions)

@app.route('/nifty-data')
def fetch_nifty_data():
    """
    Fetch Nifty indices data from NSE's official API
    
    Returns:
    JSON response of Nifty indices with their current values, changes, and percentage changes
    """
    try:
        nifty_data = get_nifty_data()
        return jsonify(nifty_data)
    except Exception as e:
        logger.error(f"Error in nifty-data route: {str(e)}")
        return jsonify({}), 500

def get_nifty_data():
    """
    Fetch Nifty indices data from NSE's official API
    
    Returns:
    dict: A dictionary of Nifty indices with their current values, changes, and percentage changes
    """
    url = "https://www.nseindia.com/api/allIndices"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/"
    }
    
    # Specific indices in the EXACT order you specified
    tracked_indices = [
        'NIFTY 50', 
        'NIFTY 100', 
        'NIFTY 200', 
        'NIFTY 500', 
        'NIFTY ALPHA 50',
        'NIFTY BANK', 
        'NIFTY ENERGY', 
        'NIFTY FMCG', 
        'NIFTY HIGH BETA 50', 
        'NIFTY HOUSING', 
        'NIFTY METAL', 
        'NIFTY PRIVATE BANK', 
        'NIFTY PSE', 
        'NIFTY PSU BANK', 
        'NIFTY REALTY', 
        'NIFTY OIL & GAS',
        'NIFTY PHARMA'
    ]
    
    nifty_data = {}
    
    try:
        # Create a session to handle cookies and maintain connection
        session = requests.Session()
        
        # First, establish a session by visiting the main NSE website
        logger.debug("Establishing session with NSE website")
        pre_response = session.get("https://www.nseindia.com", headers=headers)
        logger.debug(f"Pre-session response status: {pre_response.status_code}")
        
        # Fetch indices data
        logger.debug(f"Fetching data from URL: {url}")
        response = session.get(url, headers=headers)
        
        # Log full response details for debugging
        logger.debug(f"Response status code: {response.status_code}")
        
        # Check if request was successful
        if response.status_code == 200:
            try:
                data = response.json()
            except ValueError as json_error:
                logger.error(f"JSON parsing error: {json_error}")
                logger.error(f"Response content: {response.text}")
                return {}
            
            # Create a mapping of uppercase index names to their original data
            index_map = {
                index_data.get('index', '').upper(): index_data 
                for index_data in data.get('data', [])
            }
            
            # Extract values for specified indices in the specified order
            for nse_index in tracked_indices:
                try:
                    # Get the index data from the map
                    index_data = index_map.get(nse_index)
                    if not index_data:
                        continue
                    
                    # Prepend 'Nifty' to the display name
                    display_name = f"Nifty {index_data['index'].replace('NIFTY ', '')}"
                    
                    # Calculate change as Last Price - Open Price
                    last_price = float(index_data.get('last', 0))
                    open_price = float(index_data.get('open', 0))
                    change = last_price - open_price
                    
                    # Calculate percentage change
                    pct_change = (change / open_price * 100) if open_price != 0 else 0
                    
                    nifty_data[display_name] = {
                        "change": f"{change:+.2f}",
                        "last": f"{last_price:,.2f}",
                        "open": f"{open_price:,.2f}",
                        "pChange": f"{pct_change:+.2f}"
                    }
                except Exception as parse_error:
                    logger.error(f"Error parsing index data for {nse_index}: {parse_error}")
            
            logger.info(f"Fetched Nifty data: {nifty_data}")
            return nifty_data
        
        else:
            logger.error(f"Failed to fetch indices. Status code: {response.status_code}")
            logger.error(f"Response content: {response.text}")
            return {}
    
    except requests.exceptions.RequestException as req_error:
        logger.error(f"Network error fetching NSE indices: {req_error}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error fetching NSE indices: {str(e)}")
        return {}

@app.route('/get_nifty_data')
def fetch_get_nifty_data():
    """
    Route to fetch Nifty data
    
    Returns:
    JSON response of Nifty indices with their current values, changes, and percentage changes
    """
    try:
        nifty_data = get_nifty_data()
        return jsonify(nifty_data)
    except Exception as e:
        logger.error(f"Error in get_nifty_data route: {str(e)}")
        return jsonify({}), 500

@app.route('/test_alert')
def test_alert():
    try:
        play_alert()
        return jsonify({"status": "success", "message": "Test alert triggered"})
    except Exception as e:
        logger.error(f"Error in test_alert: {e}")
        return jsonify({"status": "error", "message": str(e)})

@app.before_request
def before_request():
    """Start background thread before the first request if not already started"""
    global thread_started
    if not thread_started:
        start_background_thread()

def start_background_thread():
    """Start the background update thread"""
    global update_thread, running, thread_started
    if not thread_started:
        running = True
        update_thread = threading.Thread(target=update_data)
        update_thread.daemon = True
        update_thread.start()
        thread_started = True
        logger.info("Background thread started")

def get_nse_indices():
    """
    Fetch NSE indices values directly from NSE's official API
    
    Returns:
    dict: A dictionary of indices with their current values
    """
    url = "https://www.nseindia.com/api/allIndices"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/"
    }
    
    indices_data = {}
    
    try:
        # Create a session to handle cookies and maintain connection
        session = requests.Session()
        
        # First, establish a session by visiting the main NSE website
        logger.debug("Establishing session with NSE website")
        pre_response = session.get("https://www.nseindia.com", headers=headers)
        logger.debug(f"Pre-session response status: {pre_response.status_code}")
        
        # Fetch indices data
        logger.debug(f"Fetching data from URL: {url}")
        response = session.get(url, headers=headers)
        
        # Log full response details for debugging
        logger.debug(f"Response status code: {response.status_code}")
        
        # Check if request was successful
        if response.status_code == 200:
            try:
                data = response.json()
                # Log ALL indices in the response
                logger.info("ALL Indices in the response:")
                for index_data in data.get('data', []):
                    logger.info(f"Index: {index_data.get('index', 'N/A')}")
            except ValueError as json_error:
                logger.error(f"JSON parsing error: {json_error}")
                logger.error(f"Response content: {response.text}")
                return {}
            
            # Extract values for ALL indices
            for index_data in data.get('data', []):
                try:
                    # Skip indices containing BOND INDEX or EX-BANK
                    if any(forbidden in index_data.get('index', '').upper() for forbidden in ['BOND INDEX', 'EX-BANK','G-SEC','TOTAL MARKET', 'MOMENTUM QUALITY 100','TOTAL MARKET',' G-SEC','VOLATILITY']):
                        logger.info(f"Skipping index: {index_data.get('index', 'N/A')}")
                        continue
                    
                    # Prepend 'Nifty' to the display name
                    display_name = f"Nifty {index_data['index'].replace('NIFTY ', '')}"
                    
                    indices_data[display_name] = float(index_data['last'])
                except Exception as parse_error:
                    logger.error(f"Error parsing index data: {parse_error}")
            
            logger.info(f"Fetched indices data: {indices_data}")
            return indices_data
        
        else:
            logger.error(f"Failed to fetch indices. Status code: {response.status_code}")
            logger.error(f"Response content: {response.text}")
            return {}
    
    except requests.exceptions.RequestException as req_error:
        logger.error(f"Network error fetching NSE indices: {req_error}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error fetching NSE indices: {str(e)}")
        return {}

@app.route('/get-nse-indices')
def fetch_nse_indices():
    """API endpoint to get NSE indices"""
    try:
        indices = get_nse_indices()
        return app.response_class(
            response=json.dumps(indices, indent=4),
            status=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Error in fetch_nse_indices: {str(e)}")
        return app.response_class(
            response=json.dumps({'error': str(e)}, indent=4),
            status=500,
            mimetype='application/json'
        )

def get_nse_indices():
    """
    Fetch NSE indices values from NSE's official API
    
    Returns:
    dict: A dictionary of indices with their current values, changes, and percentage changes
    """
    url = "https://www.nseindia.com/api/allIndices"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/"
    }
    
    indices_data = {}
    
    try:
        # Create a session to handle cookies and maintain connection
        session = requests.Session()
        
        # First, establish a session by visiting the main NSE website
        logger.debug("Establishing session with NSE website")
        pre_response = session.get("https://www.nseindia.com", headers=headers)
        logger.debug(f"Pre-session response status: {pre_response.status_code}")
        
        # Fetch indices data
        logger.debug(f"Fetching data from URL: {url}")
        response = session.get(url, headers=headers)
        
        # Log full response details for debugging
        logger.debug(f"Response status code: {response.status_code}")
        
        # Check if request was successful
        if response.status_code == 200:
            try:
                data = response.json()
                # Log ALL indices in the response
                logger.info("ALL Indices in the response:")
                for index_data in data.get('data', []):
                    logger.info(f"Index: {index_data.get('index', 'N/A')}")
            except ValueError as json_error:
                logger.error(f"JSON parsing error: {json_error}")
                logger.error(f"Response content: {response.text}")
                return {}
            
            # Extract values for ALL indices
            for index_data in data.get('data', []):
                try:
                    # Skip indices containing BOND INDEX or EX-BANK
                    if any(forbidden in index_data.get('index', '').upper() for forbidden in ['BOND INDEX', 'EX-BANK']):
                        logger.info(f"Skipping index: {index_data.get('index', 'N/A')}")
                        continue
                    
                    # Prepend 'Nifty' to the display name
                    display_name = f"Nifty {index_data['index'].replace('NIFTY ', '')}"
                    
                    indices_data[display_name] = {
                        "last": f"{index_data['last']:,.2f}",
                        "change": f"{index_data['change']:+.2f}",
                        "pChange": f"{index_data['percentChange']:+.2f}"
                    }
                except Exception as parse_error:
                    logger.error(f"Error parsing index data: {parse_error}")
            
            logger.info(f"Fetched indices data: {indices_data}")
            return indices_data
        
        else:
            logger.error(f"Failed to fetch indices. Status code: {response.status_code}")
            logger.error(f"Response content: {response.text}")
            return {}
    
    except requests.exceptions.RequestException as req_error:
        logger.error(f"Network error fetching NSE indices: {req_error}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error fetching NSE indices: {str(e)}")
        return {}

@app.route('/get-refresh-interval')
def refresh_interval():
    interval = get_refresh_interval()
    logger.info(f"Sending refresh interval: {interval} seconds")
    return jsonify({'refresh_interval': interval})

@app.route('/get-mute-status', methods=['GET'])
def get_mute_status():
    return jsonify({'isMuted': is_muted})

if __name__ == '__main__':
    # Initialize and start the update thread
    update_thread = threading.Thread(target=update_data, daemon=True)
    update_thread.start()
    
    try:
        # Start the Flask app
        app.run(debug=True)
    except KeyboardInterrupt:
        # Handle keyboard interrupt gracefully
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        # Cleanup code if needed
        logger.info("Application stopped")