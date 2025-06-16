import atexit
from datetime import datetime
import json
import logging
import math
import os
import platform 
import queue
import re
import sys
import tempfile
import threading
import time
import winsound

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
countdown_timer = 0  # Initialize countdown timer (0 means no cooldown)
beep_interval = 30  # Beep every 30 seconds
beep_running = True  # Control the beep thread

def play_alert():
    """
    Play the alert sound from static/alert.mp3, but only if not muted.
    """
    global is_muted
    if is_muted:
        logger.info("Muted: alert sound not played")
        return False
    try:
        # Initialize pygame mixer if not already initialized
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        # Load and play the sound
        sound = pygame.mixer.Sound('static/alert.mp3')
        sound.play()
        logger.info("Played alert sound")
        return True
    except Exception as e:
        logger.error(f"Error playing alert sound: {e}")
        return False

def beep_worker():
    """
    Background thread that plays alert.mp3 every minute
    """
    last_alert_time = 0
    while beep_running:
        try:
            current_time = time.time()
            # Check if a minute has passed since last alert
            if current_time - last_alert_time >= 60:  # 60 seconds = 1 minute
                play_alert()
                last_alert_time = current_time
            time.sleep(1)  # Check every second
        except Exception as e:
            logger.error(f"Error in beep_worker: {e}")
            time.sleep(5)  # Wait 5 seconds before retrying on error

app = Flask(__name__, static_url_path='/static', static_folder='static')

#cache = Cache(app)
# Initialize pygame mixer with error handling
try:
    pygame.mixer.quit()  # Ensure clean state
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
    logger.info("Pygame mixer initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize pygame mixer: {e}")

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
        "name": "DeepSeek",
        "link": "https://chartink.com/screener/deepseek",
        "scan_clause": """( {57960} ( 
            latest close > latest ema( latest close , 9 ) and 
            latest close > latest ema( latest close , 21 ) and 
            latest ema( latest close , 9 ) > latest ema( latest close , 21 ) and 
            latest close > greatest( 1 day ago high, 5 ) and 
            latest volume >= ( latest sma( latest volume , 20 ) * 1.5 ) and 
            latest rsi( 14 ) < 70 and
            latest close >= 10 and 
            latest close <= 2250  
        ) )"""
    },
    {
        "name": "KHAIZER",
        "link": "https://chartink.com/screener/copy-khizir",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:78d1fc5151e3a3d90e6ae7786f63cca8&timeframe=daily&symbol=", 
        "scan_clause": """( {57960} ( 
            latest close > latest ema( latest close , 200 ) and 
            latest close > latest ema( latest close , 44 ) and 
            latest close >= latest ema( latest close , 20 ) and 
            latest close >= latest tma( latest close , 20 ) and 
            latest close >= latest wma( latest close , 20 ) and 
            latest close >= latest vwap and 
            latest close > latest open * 1.03 and 
            latest close > latest supertrend( 10 , 1.5 ) and 
            latest volume > 1 day ago volume * 1.5 and 
            latest macd line( 26 , 12 , 9 ) > latest macd signal( 26 , 12 , 9 ) and 
            latest close > 1 day ago high and 
            latest close > latest sma( latest close , 20 ) and 
            latest close > latest sma( latest close , 50 ) and 
            latest close > latest sma( latest close , 200 ) and 
            latest close >= 10 and 
            latest close <= 2250 
        ) )"""
    },
    {
        "name": "CROSSED",
        "link": "https://chartink.com/screener/crossed-92141",
        "scan_clause": """( {57960} ( 
            latest open > latest ema( latest close , 21 ) and 
            1 day ago open <= 1 day ago ema( latest close , 21 ) and 
            latest close > latest open * 1.025 and 
            latest close >= 10 and 
            latest close <= 2250 and 
            latest close >= 1 day ago high 
        ) )"""
    },
    {
        "name": "15 MIN Breakout",
        "link": "https://chartink.com/screener/copy-15-minute-stock-breakouts-34515559",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:d54b5e1d428ff9fd372e94622da24fa7&timeframe=15_minute&symbol=", 
        "scan_clause": """( {57960} ( 
            [0] 15 minute close > [-1] 15 minute max( 20 , [0] 15 minute close ) and 
            [0] 15 minute volume > [0] 15 minute sma( volume , 20 ) and 
            latest close > 1 day ago high and 
            latest close > latest ema( latest close , 21 ) and 
            latest close > latest open * 1.025 and 
            latest close > latest supertrend( 10 , 1.5 ) and 
            latest close <= 2250 
        ) )"""
    },
    {
        "name": "STRONG STOCKS POSITIVE",
        "link": "https://chartink.com/screener/copy-strong-stocks-22395",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:7302638654ee1d6e47747b50291acf65&timeframe=daily&symbol=", 
        "scan_clause": """( {57960} ( 
            latest close > 20 and 
            latest close <= 2250 
        ) )""",
    },
   
    {
        "name": "ATR STOCKS",
        "link": "https://chartink.com/screener/atr-stocks",
        "scan_clause": """( {57960} ( \
            latest close > ( latest close - ( 3 * latest avg true range( 5 ) ) ) and \
            latest close > 20 and \
            latest close <= 2500 and \
            latest sma( latest close , 50 ) > latest sma( latest close , 200 ) and \
            latest volume > latest sma( latest volume , 20 ) and \
            latest close > latest supertrend( 10 , 1.5 ) \
        ) )"""
    },
    {
        "name": "MULTI TIMEFRAME SCAN",
        "link": "https://chartink.com/screener/aaaaa-111468",
        "scan_clause": """( {57960} ( 
            [0] 30 minute close > [0] 30 minute sma( [0] 30 minute close , 21 ) and
            [0] 30 minute close > [0] 30 minute sma( [0] 30 minute close , 50 ) and
            [0] 30 minute close > [0] 30 minute sma( [0] 30 minute close , 200 ) and

            ( {57960} (
                [0] 15 minute close > [0] 15 minute sma( [0] 15 minute close , 21 ) and
                [0] 15 minute close > [0] 15 minute sma( [0] 15 minute close , 50 ) and
                [0] 15 minute close > [0] 15 minute sma( [0] 15 minute close , 200 )
            ) ) and

            ( {57960} (
                [0] 10 minute close > [0] 10 minute sma( [0] 10 minute close , 21 ) and
                [0] 10 minute close > [0] 10 minute sma( [0] 10 minute close , 50 ) and
                [0] 10 minute close > [0] 10 minute sma( [0] 10 minute close , 200 )
            ) ) and

            ( {57960} (
                [0] 5 minute close > [0] 5 minute sma( [0] 5 minute close , 21 ) and
                [0] 5 minute close > [0] 5 minute sma( [0] 5 minute close , 50 ) and
                [0] 5 minute close > [0] 5 minute sma( [0] 5 minute close , 200 )
            ) ) and

            latest close >= 20 and latest close <= 2250
        ) )"""
    },
    {
        "name": "HARSH SELL STOCKS",
        "link": "https://chartink.com/screener/harsh-sell-8",
        "scan_clause": """( {57960} ( [=1] 10 minute open > [=1] 10 minute close and( {57960} ( [=1] 10 minute "close - 1 candle ago close / 1 candle ago close * 100" < -2 ) ) and( {166311} not( latest close > 0 ) ) and( {136699} not( latest close > 0 ) ) and( {136699} not( latest close > 0 ) ) and( {167068} not( latest close > 0 ) ) and latest close > 20 and latest close <= 2250 ) )"""
    },
    {
    "name": "VOLUME SHOCKER ✅",
    "link": "https://chartink.com/screener/p45789",
    "chart_link": "https://chartink.com/stocks-new?symbol=",
    "scan_clause": """( {57960} ( 
        latest volume > 1 day ago volume and 
        1 day ago volume > 2 days ago volume and 
        latest close > 1 day ago close and 
        1 day ago close > 2 days ago close and 
        latest volume > 1000000 and 
        1 day ago volume > 500000 and 
        latest close > latest open * 1.03 and 
        latest open > 1 day ago close 
    ) )"""
    },
    {
    "name": "High Volume Spike",
    "link": "https://chartink.com/screener/shock-19",
    "chart_link": "https://chartink.com/stocks-new?symbol=",    
    "scan_clause": """( {57960} ( 
        latest volume > latest sma( latest volume , 5 ) * 2 and 
        latest close > 1 day ago close and 
        latest volume > 500000 
    ) )"""
    },
    {
        "name": "85 VOLUME SHOCK ✅",
        "link": "https://chartink.com/screener/copy-volume-rahim",
        "chart_link": "https://chartink.com/stocks-new?symbol=",
        "scan_clause": """( {57960} ( 
            latest volume > 1 day ago volume * 0.85 and 
            1 day ago volume > 2 days ago volume and 
            latest close > 1 day ago close and 
            1 day ago close > 2 days ago close and 
            latest volume > 1000000 and 
            1 day ago volume > 500000 and 
            latest close > latest open * 1.025 and 
            [=1] 5 minute close < [=1] 5 minute open * 1.03 and 
            latest open > 1 day ago close and 
            latest volume > latest sma( latest volume , 5 ) * 2 
        ) )"""
    },
    {
        "name": "HARSH BUY STOCKS",
        "link": "https://chartink.com/screener/harsh-645",
        "scan_clause": """( {57960} ( [=1] 10 minute open < [=1] 10 minute close and ( {57960} ( [=1] 10 minute "close - 1 candle ago close / 1 candle ago close * 100" < 2 ) ) and ( {166311} not ( latest close > 0 ) ) and ( {136699} not ( latest close > 0 ) ) and ( {136699} not ( latest close > 0 ) ) and ( {167068} not ( latest close > 0 ) ) and latest close > 20 and latest close <= 2250 ) )"""
    },
    {
        "name": "EMA 11 CHANU",
        "link": "https://chartink.com/screener/ema-22-271",
        "scan_clause": """( {57960} ( [0] 15 minute ema ( [0] 15 minute close , 11 ) > [0] 15 minute ema ( [0] 15 minute close , 22 ) and [ -1 ] 15 minute ema ( [0] 15 minute close , 11 )<= [ -1 ] 15 minute ema ( [0] 15 minute close , 22 ) and latest adx ( 14 ) >= 20 ) ) """
    },
    {
        "name": "Smart Cash Flow - Chanu 🟢 ",
        "link": "https://chartink.com/screener/copy-85-volume-shameem",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:e93d77e49e9b94220daecb5bae1e6ff8&timeframe=daily&symbol=",
        "scan_clause": """( {cash} ( 
            latest volume > 1 day ago volume * 0.85 and 
            latest close > 1 day ago close and 
            latest volume > 1000000 and 
            1 day ago volume > 500000 and 
            [=1] 5 minute close < [=1] 5 minute open * 1.03 
        ) )"""
    },
    {
        "name": "30min Volume Spike 🚀",
        "link": "https://chartink.com/screener/30min-volume-spike",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:99b7045b2e7fc79cc51b0d0ae46e7fac&timeframe=30_minute&symbol=",
        "scan_clause": """( {cash} ( 
            [=0] 30 minute volume > [0] 30 minute sma( [0] 30 minute volume , 30 ) * 3 
        ) )"""
    },
    {
        "name": "CHANU VOLATILITY SPIKE ",
        "link": "https://chartink.com/screener/copy-volume-shockers-stocks-with-rising-volumes-1111145289",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:c7fa7b37712fa79e1b96d4155e7d64d5&timeframe=daily&symbol=",
        "scan_clause": """( {57960} ( 
            latest volume > latest sma( volume , 10 ) * 2 and 
            ( {cash} ( 
                latest close > 1 day ago close * 1.05 or 
                latest close < 1 day ago close * 0.95 
            ) ) 
        ) )"""
    },
    {
        "name": "Vijay Thakkar 🟢",
        "link": "https://chartink.com/screener/vijay-thakkar-27107",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:db8c18083f5668803c52fcae01bc1b8d&timeframe=daily&symbol=",
        "scan_clause": """( {57960} ( 
            latest volume > latest sma( latest volume , 20 ) * 3 and 
            latest close > 100 and 
            ( ( latest close - 1 candle ago close ) / 1 candle ago close ) * 100 >= 3 and 
            latest sma( latest volume , 20 ) >= 25000 and 
            latest volume > 100000 
        ) )"""
    },
    {
    "name": "MAGIC FILTER RAHIM",
    "link": "https://chartink.com/screener/che-68",
    "scan_clause": """({57960}([0] 5 minute close > [0] 5 minute vwap and [0] 5 minute close > [-1] 5 minute vwap and [0] 5 minute close > [-2] 5 minute vwap and [0] 5 minute close > [0] 5 minute supertrend(10,1) and [0] 5 minute close > [-1] 5 minute supertrend(10,1) and [0] 5 minute close > [-2] 5 minute supertrend(10,1) and [0] 5 minute ema([0] 5 minute close,9) > [0] 5 minute supertrend(10,1) and [0] 5 minute close > 20 and [0] 5 minute close <= 2250 and latest close > latest open * 1.02))"""
},
{
        "name": "STRONG STOCKS NEGATIVE",
        "link": "https://chartink.com/screener/strong-stocks",
        "scan_clause": """( {57960} ( 
            latest close > 20 and 
            latest close <= 2250 and
            latest close < latest open and
            (latest open - latest close) / latest open * 100 > 1
        ) )""",
    },
    {
        "name": "RA Inventor BUY",
        "link": "https://chartink.com/screener/ra-score",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:24679f454fd1690bb64e19ac0d079642&timeframe=30_minute&symbol=", 
        "scan_clause": """( {57960} ( \
        [0]30 minute close * ([0]30 minute close - [-1] 30 minute close) / [-1] 30 minute close * 100 > 1500 and \
        latest close > 20 and \
        latest close <= 2250 \
    ) )"""
    },
    {
        "name": "RA Inventor SELL",
        "link": "https://chartink.com/screener/ra-score-sell",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:7a1d3e7c5afc5c6b1b8c4e0d6e4d1b2e&timeframe=30_minute&symbol=",
        "scan_clause": """( {57960} ( \
        [0]30 minute close * ([0]30 minute close - [-1] 30 minute close) / [-1] 30 minute close * 100 < -1500 and \
        latest close > 20 and \
        latest close <= 2250 \
    ) )"""
    },
    {
        "name": "RA Inventor 20 Candles BUY",
        "link": "https://chartink.com/screener/ra-score",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:c78aa5a902629463cf1605aef72c8c1c&timeframe=30_minute&symbol=",
        "scan_clause": """( {57960} ( \
        [0]5 minute close * ([0]5 minute close - [-1] 5 minute close) / [-1] 5 minute close * 100 > 1500 and \
        latest close > 20 and \
        latest close <= 2250 and \
        ( latest Close - latest Open ) > ( latest Sum ( latest Close - latest Open , 16 ) / 16 ) * 2 
        ) )"""
    },
    {
        "name": "DST BUY",  
        "link": "https://chartink.com/screener/stst-81",  
        "chart_link": "https://chartink.com/stocks-new?scan_link=scanlink:5a82d36a216278deb065b37eebc871a0&timeframe=5_minute&symbol=",
        "scan_clause": """(
        [0]5 minute supertrend(10,1) > [0]5 minute supertrend(10,3) and
        [0]5 minute close > [0]5 minute supertrend(10,1) and
        [0]5 minute close > [0]5 minute supertrend(10,3) and
        latest close > 20 and \
        latest close <= 2250 and \
        [0]5 minute wma([0]5 minute close, 21) > [0]5 minute sma([0]5 minute close, 21)
    )"""
    },
    {
    "name": "DST SELL",  
    "link": "https://chartink.com/screener/dst-sell-4",  
    "scan_clause": """(
        [0]5 minute supertrend(10,1) < [0]5 minute supertrend(10,3) and
        [0]5 minute close < [0]5 minute supertrend(10,1) and
        latest close > 20 and \
        latest close <= 2250 and \
        [0]5 minute close < [0]5 minute supertrend(10,3) and
        [0]5 minute wma([0]5 minute close, 21) < [0]5 minute sma([0]5 minute close, 21)
    )"""
},
]

# Global variables
data_queue = queue.Queue()
last_update_thread = None
beep_thread = None
threads_started = False
running = True
thread_started = False
scan_results = {}
previous_scores = {}  # Initialize previous_scores globally

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
# Load settings and ensure mute_status is properly set
settings = load_settings()
is_muted = settings.get('mute_status', False)  # Default to False if not set
logger.info(f"Initial mute status loaded: {is_muted}")

@app.route('/clear_cache')
def clear_cache():
    cache.clear()
    return "Cache cleared!"

@app.route('/update_mute_status', methods=['POST'])
def update_mute_status():
    global is_muted, settings
    data = request.get_json()
    is_muted = bool(data.get('isMuted', False))
    settings['mute_status'] = is_muted
    save_settings(settings)
    logger.info(f"Mute status set to: {is_muted}")
    return jsonify({'status': 'success', 'isMuted': is_muted})

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
    global scan_results, is_muted
    
    def _fetch_data_impl():
        """Implementation of fetch_data that assumes app context exists"""
        global scan_results, is_muted
        
        try:
            # Create a new dictionary to store results
            new_scan_results = {}
            with requests.Session() as session:
                for condition in conditions:
                    stocks = fetch_and_process_data(session, condition)
                    if stocks:
                        new_scan_results[condition['name']] = stocks

            # Update the global variables
            scan_results = new_scan_results
            
            # Load mute status from db.json
            settings = load_settings()
            is_muted = settings.get("mute_status", False)

            # Play alert sound only if unmuted
            if not is_muted:
                play_alert()
                
            return scan_results
            
        except Exception as e:
            logger.error(f"Error in _fetch_data_impl: {e}", exc_info=True)
            return None
    
    # Ensure we're in an application context
    if not 'current_app' in globals() or current_app is None:
        with app.app_context():
            return _fetch_data_impl()
    return _fetch_data_impl()

def filter_stocks(stocks, condition):
    if condition == "HARSH SELL STOCKS":
        # Filter for negative percentage change
        return [stock for stock in stocks if stock['per_chg'] < 0]
    elif condition == "STRONG STOCKS NEGATIVE":
        # Filter for negative percentage change
        return [stock for stock in stocks if stock['per_chg'] < 0]
    else:
        # Filter for positive percentage change
        return [stock for stock in stocks if stock['per_chg'] > 0]

def update_data():
    """
    Background thread function to update stock data every 2 minutes
    
    This function:
    - Fetches fresh data
    - Updates the countdown timer
    - Handles errors gracefully
    - Respects the running flag for clean shutdown
    """
    global running, countdown_timer, last_alert_time
    
    def _update_with_context():
        """Helper function to run with application context"""
        try:
            with app.app_context():
                fetch_data()
                return True
        except Exception as e:
            logger.error(f"Error in _update_with_context: {e}", exc_info=True)
            return False
    
    while running:
        try:
            logger.info("Starting background data update...")
            update_successful = _update_with_context()
            
            if update_successful:
                logger.info("Background data update completed successfully")
                # Play alert sound after successful update
                play_alert()
                # Reset the countdown timer
                countdown_timer = 120  # 2 minutes until next update
                
            else:
                logger.warning("Background data update completed with errors")
                # Don't reset the countdown timer on error, try again sooner
                countdown_timer = 30  # Try again in 30 seconds
            
            # Count down the timer every second
            while countdown_timer > 0 and running:
                time.sleep(1)
                countdown_timer -= 1
                
                # Countdown logging removed
                
        except Exception as e:
            logger.error(f"Error in update_data: {e}", exc_info=True)
            # Wait before retrying on error, but don't get stuck in a tight loop
            time.sleep(min(60, max(5, 60 - countdown_timer)))  # Wait at least 5 seconds

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

@app.route('/get-scan-results')
def get_scan_results():
    """Get scan results from all conditions and return as JSON"""
    def _get_scan_results_impl():
        global scan_results
        
        try:
            # Get the selected conditions from settings
            with open('db.json', 'r') as f:
                settings = json.load(f)
                selected_conditions = settings.get('conditions', [])
            
            logger.info(f"Selected conditions: {selected_conditions}")
            
            if not selected_conditions:
                logger.warning("No conditions selected")
                return jsonify({'error': 'No conditions selected'}), 400
            
            # Get scan results for selected conditions
            all_results = {}
            found_stocks = False
            
            # Create a mapping of potential name variations
            name_variations = {
                "STRONG STOCKS": "STRONG STOCKS POSITIVE",
                "STRONG STOCKS POSITIVE": "STRONG STOCKS POSITIVE"
            }
            
            # Ensure scan_results is not None
            if scan_results is None:
                logger.warning("scan_results is None, attempting to fetch data")
                fetch_data()
            
            for condition in selected_conditions:
                # Skip 'on' which is not a real condition
                if condition == 'on':
                    continue
                
                # Check for name variations
                normalized_condition = name_variations.get(condition, condition)
                
                # Safely get stocks, default to empty list
                stocks = scan_results.get(normalized_condition, [])
                logger.info(f"Condition: {normalized_condition}, Stocks found: {len(stocks)}")
                
                if stocks:
                    all_results[normalized_condition] = stocks
                    found_stocks = True
            
            # If no stocks found, log a warning
            if not all_results:
                logger.warning("No stocks found for any selected conditions")
            
            # Create response with no-cache headers
            response = make_response(jsonify(all_results))
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            return response
            
        except Exception as e:
            logger.error(f"Error in get_scan_results: {e}", exc_info=True)
            return jsonify({'error': str(e)}), 500
    
    # Ensure we're in an application context
    if not 'current_app' in globals() or current_app is None:
        with app.app_context():
            return _get_scan_results_impl()
    return _get_scan_results_impl()

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
    """Test endpoint to verify sound playback functionality"""
    try:
        logger.info("\n=== TEST ALERT TRIGGERED ===")
        
        # Get system info for debugging
        import platform
        import pygame as pg
        
        system_info = {
            'python_version': platform.python_version(),
            'system': platform.system(),
            'pygame_version': pg.version.ver,
            'sdl_version': ".".join(str(x) for x in pg.get_sdl_version())
        }
        logger.info(f"System info: {system_info}")
        
        # Try to play the sound with force_play=True to bypass mute and cooldown
        success = play_alert(force_play=True)
        
        # Get sound device info
        try:
            import pygame._sdl2.audio as sdl2_audio
            devices = [str(device) for device in sdl2_audio.get_audio_device_names()]
            system_info['audio_devices'] = devices
        except Exception as e:
            system_info['audio_devices_error'] = str(e)
        
        response = {
            'status': 'success' if success else 'error',
            'message': 'Playback successful' if success else 'Playback failed',
            'sound_file': 'alert.mp3',
            'muted': is_muted,
            'countdown_timer': countdown_timer,
            'system_info': system_info,
            'timestamp': time.time()
        }
        
        logger.info(f"Test alert response: {response}")
        return jsonify(response), 200
        
    except Exception as e:
        error_msg = f"Error in test_alert: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'status': 'error',
            'message': error_msg,
            'error_type': type(e).__name__
        }), 500
    return "Alert sound triggered!"  # Simple response to indicate the alert was triggered

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

def cleanup():
    """
    Cleanup function to stop background threads and release resources.
    This is registered with atexit to ensure it runs when the application exits.
    """
    global running, beep_running, update_thread, beep_thread
    
    try:
        logger.info("Initiating cleanup of background threads...")
        
        # Signal threads to stop
        running = False
        beep_running = False
        
        # Give threads a moment to notice the stop signal
        time.sleep(0.5)
        
        # Wait for threads to finish (with timeout)
        if update_thread and update_thread.is_alive():
            logger.info("Waiting for update thread to finish...")
            update_thread.join(timeout=2.0)
            
        if beep_thread and beep_thread.is_alive():
            logger.info("Waiting for beep thread to finish...")
            beep_thread.join(timeout=1.0)
            
        logger.info("Cleanup completed successfully")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {e}", exc_info=True)
    finally:
        # Ensure these are always set to False
        running = False
        beep_running = False

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
            except ValueError as json_error:
                logger.error(f"JSON parsing error: {json_error}")
                logger.error(f"Response content: {response.text}")
                return {}
            
            # Create a mapping of uppercase index names to their original data
            index_map = {
                index_data.get('index', '').upper(): index_data 
                for index_data in data.get('data', [])
            }
            
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

@app.route('/filter_stocks', methods=['POST'])
def filter_stocks():
    score_threshold = float(request.json.get('score', 0))  # Convert to float
    filtered_stocks = [stock for stocks in scan_results.values() for stock in stocks if stock['potential_score'] > score_threshold]
    logger.info(f"Filter button clicked")
    logger.info(f"Filtered stocks: {filtered_stocks}")
    return jsonify(filtered_stocks)

@app.route('/get-refresh-interval')
def refresh_interval():
    interval = get_refresh_interval()
    logger.info(f"Sending refresh interval: {interval} seconds")
    return jsonify({'refresh_interval': interval})

@app.route('/get-mute-status', methods=['GET'])
def get_mute_status():
    return jsonify({'isMuted': is_muted})

@app.route('/debug_sound')
def debug_sound():
    """Debug endpoint to test sound functionality"""
    global is_muted, countdown_timer
    
    # Get current state
    state = {
        'is_muted': is_muted,
        'countdown_timer': countdown_timer,
        'last_alert_time': last_alert_time,
        'time_since_last_alert': time.time() - last_alert_time if last_alert_time > 0 else 'Never',
        'pygame_mixer_initialized': pygame.mixer.get_init() is not None,
        'sound_file_exists': False
    }
    
    # Check sound file existence
    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, "static", "sounds", "alert.mp3"),
        os.path.join(base_dir, "sounds", "alert.mp3"),
        os.path.join(base_dir, "static", "alert.mp3"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            state['sound_file_exists'] = True
            state['sound_file_path'] = path
            break
    
    # Force play sound for testing
    force = request.args.get('force', 'false').lower() == 'true'
    if force:
        logger.info("Force playing sound for testing")
        temp_muted = is_muted
        temp_timer = countdown_timer
        
        # Temporarily override mute and timer for testing
        is_muted = False
        countdown_timer = 0
        
        try:
            play_alert()
            state['test_playback'] = 'Attempted to play sound'
        except Exception as e:
            state['test_playback_error'] = str(e)
        finally:
            # Restore original values
            is_muted = temp_muted
            countdown_timer = temp_timer
    
    return jsonify(state)

if __name__ == '__main__':
    # Register cleanup first to ensure it runs on all exit paths
    atexit.register(cleanup)

    def start_threads_once():
        global threads_started, update_thread, beep_thread, countdown_timer
        if not threads_started:
            logger.info("Starting background threads after first page load.")
            countdown_timer = 120  # Start countdown when user first loads the page
            update_thread = threading.Thread(target=update_data, daemon=True)
            beep_thread = threading.Thread(target=beep_worker, daemon=True)
            update_thread.start()
            beep_thread.start()
            threads_started = True

    # Patch the main route to start threads on first request
    from flask import request
    orig_index = app.view_functions.get('index')
    if orig_index:
        def wrapped_index(*args, **kwargs):
            start_threads_once()
            return orig_index(*args, **kwargs)
        app.view_functions['index'] = wrapped_index

    # Configure Flask to handle shutdown signals properly
    from werkzeug.serving import is_running_from_reloader
    if not is_running_from_reloader():
        # Only run the cleanup when not in debug mode reloader
        try:
            # Start the Flask app
            app.run(debug=True, use_reloader=False)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt. Shutting down...")
        except Exception as e:
            logger.error(f"Error in Flask app: {e}", exc_info=True)
        finally:
            cleanup()
    else:
        # In debug mode with reloader, just run normally
        app.run(debug=True)