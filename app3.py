import atexit
from datetime import datetime, date, timezone, timedelta
import json
import base64
from postgres_db import db
import logging
import math
import os
from pathlib import Path
import platform 
import queue
import random
import re
import sys
import tempfile
import threading
import time
import traceback
import uuid
import winsound
from werkzeug.exceptions import HTTPException

class AppTemporarilyUnavailable(HTTPException):
    code = 503
    description = 'The application is currently unavailable. Please try again in a few minutes. If the problem persists, please contact our service team for assistance.'

from bs4 import BeautifulSoup as bs
import pandas as pd
import pygame
import requests
import psycopg2
from flask import Flask, render_template, jsonify, make_response, send_from_directory, request, flash, abort, redirect, url_for, session, current_app
from flask_wtf import FlaskForm
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from functools import wraps
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

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Generate a secure secret key if not exists, or use environment variable
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or os.urandom(24).hex()

# Configure session to expire after 2 hours (7200 seconds)
app.config['PERMANENT_SESSION_LIFETIME'] = 7200  # 2 hours in seconds
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_REFRESH_EACH_REQUEST'] = True  # Refresh session on each request

# Configure Flask-Login
app.config['REMEMBER_COOKIE_DURATION'] = 7200  # 2 hours in seconds
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['REMEMBER_COOKIE_REFRESH_EACH_REQUEST'] = True  # Refresh remember token on each request

# Initialize Bcrypt
bcrypt = Bcrypt(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = 'login'  # type: ignore

@app.before_request
def make_session_permanent():
    if hasattr(current_user, 'is_authenticated') and current_user.is_authenticated:
        session.permanent = True  # type: ignore[attr-defined]

def get_user_data(user_id):
    """
    Fetch user data from the database by user ID.
    
    Args:
        user_id: The ID of the user to fetch data for
        
    Returns:
        dict: User data if found, None otherwise
    """
    if not user_id:
        print("❌ [get_user_data] No user_id provided")
        return None
        
    try:
        # Convert user_id to integer
        try:
            user_id_int = int(user_id)
            print(f"🔍 [get_user_data] Fetching data for user ID: {user_id_int} (type: {type(user_id_int)})")
        except (ValueError, TypeError) as e:
            print(f"❌ [get_user_data] Invalid user_id format: {user_id} (type: {type(user_id)})")
            return None
            
        # Get database cursor
        cur = db.get_cursor()
        if not cur:
            print("❌ [get_user_data] Failed to get database cursor")
            return None
            
        try:
            # Execute query to get user data
            cur.execute("""
                SELECT user_data 
                FROM users 
                WHERE id = %s
            """, (user_id_int,))
            
            # Fetch the result (using RealDictCursor)
            result = cur.fetchone()
            
            # Check if we got a result and it has the user_data field
            if result and 'user_data' in result and result['user_data']:
                print(f"✅ [get_user_data] Successfully fetched data for user ID: {user_id_int}")
                return result['user_data']
            else:
                print(f"❌ [get_user_data] No data found for user ID: {user_id_int}")
                return None
                
        except Exception as query_error:
            print(f"❌ [get_user_data] Database query failed: {query_error}")
            traceback.print_exc()
            return None
            
    except Exception as e:
        print(f"❌ [get_user_data] Unexpected error: {e}")
        traceback.print_exc()
        return None

# Add get_user_data to template context
@app.context_processor
def utility_processor():
    def get_user_data_processor(user_id):
        return get_user_data(user_id)
    return dict(get_user_data=get_user_data_processor)

@app.context_processor
def inject_profile():
    if current_user.is_authenticated:
        user_data = get_user_data(current_user.id)
        profile = user_data.get('account', {}).get('profile', {}) if user_data else {}
        return dict(profile=profile)
    return dict(profile={})

# User class with proper type handling
class User(UserMixin):
    def __init__(self, id, username, password, email=''):
        # Store ID as string to avoid conversion issues
        try:
            self.id = int(id) if id is not None and str(id).strip() not in ['', 'id'] else None
        except (ValueError, TypeError, AttributeError):
            print(f"⚠️ Warning: Invalid ID format: {id} (type: {type(id)}), using None")
            self.id = None
            
        self.username = username
        self.password = password
        self.email = email
        self._user_data = None
        
        # Debug logging
        print(f"🔍 Created User - ID: {self.id} (type: {type(self.id)}), Username: {self.username}")

    def get_id(self):
        # Return string representation as required by Flask-Login
        return str(self.id) if self.id is not None else None
        
    @property
    def user_data(self):
        if self._user_data is None and self.id is not None:
            try:
                self._user_data = get_user_data(self.id)
            except Exception as e:
                print(f"❌ Error loading user data: {e}")
                self._user_data = {}
        return self._user_data or {}
        
    def get_auth_token(self):
        """
        Generate a secure token for 'remember me' functionality
        """
        data = [str(self.id), self.password]
        return base64.b64encode(":".join(data).encode('utf-8')).decode('utf-8')

def get_user(user_id):
    try:
        cur = db.get_cursor()
        cur.execute("""
            SELECT id, user_data->'account'->>'username' as username,
                   user_data->'account'->>'password' as password,
                   COALESCE(user_data->'account'->'profile'->>'email', 
                           user_data->'account'->>'email', '') as email
            FROM users 
            WHERE id = %s
        """, (user_id,))
        user_data = cur.fetchone()
        if user_data:
            return User(id=user_data[0], 
                      username=user_data[1],
                      password=user_data[2],
                      email=user_data[3])
    except Exception as e:
        print(f"Error getting user: {e}")
    return None

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID. This is called by Flask-Login to get the user object.
    
    Args:
        user_id: The user ID from the session (should be a string as per Flask-Login)
    """
    if not user_id:
        print("❌ [load_user] No user_id provided")
        return None
    
    print(f"🔍 [load_user] Loading user with ID: {user_id} (type: {type(user_id)})")
    
    try:
        # First, try to get the user data from the database
        user_data = get_user_data(user_id)
        if not user_data:
            print(f"❌ [load_user] No user data found for ID: {user_id}")
            return None
            
        # Extract account information
        account = user_data.get('account', {})
        profile = account.get('profile', {})
        
        # Get required fields
        user_id = str(user_id)  # Ensure user_id is a string for Flask-Login
        username = account.get('username')
        password = account.get('password')
        email = profile.get('email', account.get('email', ''))
        
        # Validate required fields
        if not all([user_id, username, password]):
            print(f"❌ [load_user] Missing required user data fields. ID: {user_id}, Username: {username}")
            return None
            
        print(f"✅ [load_user] Successfully loaded user: {username} (ID: {user_id})")
        
        # Create and return user object
        return User(
            id=user_id,
            username=username,
            password=password,
            email=email
        )
        
    except Exception as e:
        print(f"❌ [load_user] Error loading user: {e}")
        traceback.print_exc()
        return None
        return None

def authenticate_user(username, password):
    try:
        print(f"🔍 Attempting to authenticate user: {username}")
        
        # Proceed with database authentication for non-hardcoded users
        cur = db.get_cursor()
        if not cur:
            print("❌ Database connection error")
            return None
        
        # First, let's check if the user exists and get their data
        cur.execute("""
            SELECT 
                id, 
                user_data->'account'->>'username' as username,
                user_data->'account'->>'password' as password_hash,
                COALESCE(
                    user_data->'account'->'profile'->>'email', 
                    user_data->'account'->>'email', 
                    ''
                ) as email,
                user_data->'account' as account_data
            FROM users 
            WHERE user_data->'account'->>'username' = %s
        """, (username,))
        
        user_data = cur.fetchone()
        
        if not user_data:
            print(f"❌ User '{username}' not found in database")
            return None
            
        # Convert to dictionary if it's not already
        if not isinstance(user_data, dict):
            if cur.description:  # Add null check
                columns = [desc[0] for desc in cur.description]
                user_data = dict(zip(columns, user_data))
        
        # Debug print user data (without password hash for security)
        print(f"✅ Found user: {user_data.get('username')} (ID: {user_data.get('id')})")
        
        # Get password hash
        password_hash = user_data.get('password_hash')
        if not password_hash:
            print("❌ No password found for user")
            return None
            
        # For all users, check bcrypt hash
        print(f"🔑 User ID: {user_data.get('id')}, Username: {user_data.get('username')}")
        try:
            # Verify the password using the existing bcrypt instance
            password_matches = bcrypt.check_password_hash(password_hash, password)
            print(f"🔑 Password check result: {password_matches}")
            
            if not password_matches:
                print("❌ Incorrect password")
                return None
                
            # If we get here, password is correct
            print(f"✅ Password verified for user: {username}")
                
        except Exception as e:
            print(f"❌ Error verifying password: {str(e)}")
            traceback.print_exc()
            return None
                
        if password_matches:
            print(f"✅ Authentication successful for user: {username}")
            return User(
                id=user_data.get('id'),
                username=user_data.get('username'),
                password=password_hash,
                email=user_data.get('email', '')
            )
        else:
            print("❌ Password does not match")
            return None
            
    except Exception as e:
        print(f"❌ Error authenticating user: {e}")
        traceback.print_exc()
        return None
        print(f"❌ Error authenticating user: {str(e)}")
        print("Stack trace:")
        traceback.print_exc()
    return None

def save_user(username, password, email=''):
    try:
        # Check if username already exists
        cur = db.get_cursor()
        cur.execute("""
            SELECT id FROM users 
            WHERE user_data->'account'->>'username' = %s
        """, (username,))
        if cur.fetchone():
            print(f"❌ Username '{username}' already exists")
            return None
            
        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        print(f"🔑 Generated password hash for new user: {hashed_password[:20]}...")
        
        # Create new user data structure
        user_data = {
            'account': {
                'username': username,
                'password': hashed_password,
                'email': email,
                'profile': {
                    'name': username,
                    'email': email,
                    'premium': 'no',
                    'gender': 'Prefer not to say'
                },
                'conditions': []
            }
        }
        
        # Insert new user with password_hash
        cur.execute("""
            INSERT INTO users (username, password_hash, user_data)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (username, hashed_password, json.dumps(user_data)))
        
        result = cur.fetchone()
        if result:
            user_id = result[0]
            if db.conn is not None:
                db.conn.commit()
            return str(user_id)
        else:
            print("❌ Failed to get user ID after insert")
            return None
        
    except Exception as e:
        print(f"Error saving user: {e}")
        if 'db' in locals() and hasattr(db, 'conn') and db.conn is not None:
            db.conn.rollback()
        return None

# Initialize pygame mixer with error handling
try:
    pygame.mixer.quit()  # Ensure clean state
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=4096)
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
def format_number_with_type(value, column_type='default'):
    if value is None:
        return '-'
    
    try:
        num = float(value)
        
        # Format Close with two decimal places
        if column_type == 'close':
            formatted_value = f"{num:.2f}"
            return formatted_value  

        # Format Change % with two decimal places and add percentage sign
        if column_type == 'change_percent':
            formatted_value = f"{num:.2f}%"  # Ensure two decimal places
            return formatted_value  

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
app.jinja_env.filters['format_number'] = format_number_with_type

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
admin_conditions = [
    {
    "name": "DeepSeek",
    "type": "admin",
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
    "name": "AN Kumar NIFTY500 ✅",
    "link": "https://chartink.com/screener/ank-1073",
    "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:729e8670d63135d95c4d928c801e6a3e&timeframe=15_minute&symbol=",
    "scan_clause": """( {57960} ( 
        ( ( latest close - 1 day ago close ) / ( greatest( 2, latest high ) - least( 2, latest low ) ) ) * 
        ( latest volume + 1 day ago volume ) / 2 > 0.5 and 
        latest close > 25 and 
        latest close < 2250 
    ) )"""
    },
    {
    "name": "AN Kumar Cash",
    "type": "admin",
    "link": "https://chartink.com/screener/ank-1073",
    "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:729e8670d63135d95c4d928c801e6a3e&timeframe=15_minute&symbol=",
    "scan_clause": """( {cash} ( 
        ( ( latest close - 1 day ago close ) / ( greatest( 2, latest high ) - least( 2, latest low ) ) ) * 
        ( latest volume + 1 day ago volume ) / 2 > 0.5 and 
        latest close > 25 and 
        latest close < 2250 
    ) )"""
    },
    {
        "name": "KHAIZER",
        "type": "admin",
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
        "type": "admin",
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
        "type": "admin",
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
        "type": "admin",
        "link": "https://chartink.com/screener/copy-strong-stocks-22395",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:7302638654ee1d6e47747b50291acf65&timeframe=daily&symbol=", 
        "scan_clause": """( {57960} ( 
            latest close > 20 and 
            latest close <= 2250 
        ) )""",
    },
    {
        "name": "ATR STOCKS",
        "type": "admin",    
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
        "name": "Deep Seek Volume & Range Break ✅",
        "type": "admin",   
        "link": "https://chartink.com/screener/ds-2206",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:9eadb2a72344cf751b91a835fc23e4a0&timeframe=daily&symbol=",
        "scan_clause": """( {cash} ( 
        latest close > 50 and 
        latest close < 2250 and 
        latest volume > latest sma( latest volume , 5 ) * 2.5 and 
        latest volume > 1 day ago volume * 1.8 and 
        latest volume > latest sma( latest volume , 20 ) * 2 and 
        latest close > latest open and 
        latest high - latest low > latest sma( latest high - latest low , 5 ) * 1.5 and 
        latest close > latest ema( latest close , 20 ) and 
        latest close > latest max( 20 , latest vwap ) and 
        [=1] 5 minute close < [=1] 5 minute open * 1.03 
    ) )"""
    },
    {
        "name": "MULTI TIMEFRAME SCAN",
        "type": "admin",
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
        "scan_clause": """( {57960} ( [=1] 10 minute open > [=1] 10 minute close and ( {57960} ( [=1] 10 minute "close - 1 candle ago close / 1 candle ago close * 100" < -2 ) ) and ( {166311} not ( latest close > 0 ) ) and ( {136699} not ( latest close > 0 ) ) and ( {136699} not ( latest close > 0 ) ) and ( {167068} not ( latest close > 0 ) ) and latest close > 20 and latest close <= 2250 ) )"""
    },
    {
    "name": "VOLUME SHOCKER ✅",
    "type": "admin",
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
    "type": "admin",
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
        "type": "admin",
        "link": "https://chartink.com/screener/copy-volume-rahim",
        "chart_link": "https://chartink.com/stocks-new?symbol=",
        "scan_clause": """( {cash} ( 
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
        "type": "admin",
        "link": "https://chartink.com/screener/harsh-645",
        "scan_clause": """( {57960} ( [=1] 10 minute open < [=1] 10 minute close and ( {57960} ( [=1] 10 minute "close - 1 candle ago close / 1 candle ago close * 100" < 2 ) ) and ( {166311} not ( latest close > 0 ) ) and ( {136699} not ( latest close > 0 ) ) and ( {136699} not ( latest close > 0 ) ) and ( {167068} not ( latest close > 0 ) ) and latest close > 20 and latest close <= 2250 ) )"""
    },
    {
        "name": "EMA 11 CHANU",
        "link": "https://chartink.com/screener/ema-22-271",
        "scan_clause": """( {57960} ( [0] 15 minute ema ( [0] 15 minute close , 11 ) > [0] 15 minute ema ( [0] 15 minute close , 22 ) and [ -1 ] 15 minute ema ( [0] 15 minute close , 11 )<= [ -1 ] 15 minute ema ( [0] 15 minute close , 22 ) and latest adx ( 14 ) >= 20 ) ) """
    },
    {
        "name": "Smart Cash Flow - Chanu",
        "type": "admin",
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
        "name": "30min Volume Spike",
        "link": "https://chartink.com/screener/30min-volume-spike",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:99b7045b2e7fc79cc51b0d0ae46e7fac&timeframe=30_minute&symbol=",
        "scan_clause": """( {cash} ( 
            [=0] 30 minute volume > [0] 30 minute sma( [0] 30 minute volume , 30 ) * 3 
        ) )"""
    },
    {
    "name": "Rahim Volume Surge 🔍",
    "type": "admin",
    "link": "https://chartink.com/screener/rahim-ds-80",
    "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:279b7c20292d4250387c8dbfa32ac199&timeframe=5_minute&symbol=",
    "scan_clause": """( {cash} ( 
        latest volume > latest sma( latest volume , 5 ) * 1.5 and 
        latest close >= 50 and 
        latest close < 2250 and 
        latest volume > 1 day ago volume * 1 and 
        latest volume > latest sma( latest volume , 20 ) * 2 and 
        latest close > latest open and 
        latest high - latest low > latest sma( latest high - latest low , 5 ) * 1.5 and 
        latest close > latest ema( latest close , 20 ) and 
        latest close > latest max( 20 , latest vwap ) and 
        [=1] 5 minute close < [=1] 5 minute open * 1.03 and 
        latest volume > latest sma( latest volume , 20 ) and 
        latest max( 10 , latest high ) > latest min( 10 , latest low ) * 1.05 and 
        latest max( 50 , latest high ) / latest min( 50 , latest low ) >= 1.35 and 
        ( 
            ( [0] 15 minute close - [-1] 15 minute close ) / 
            ( greatest( 2, [0] 15 minute high ) - least( 2, [0] 15 minute low ) ) * 
            ( [0] 15 minute volume + [-1] 15 minute volume ) / 2 
        ) > 0.5 
    ) )"""
    },
    {
        "name": "CHANU VOLATILITY SPIKE ",
        "type": "admin",
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
        "name": "Vijay Thakkar",
        "type": "admin",
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
        "name": "Only Cash ✅",
        "link": "https://chartink.com/screener/vijay-thakkar-27107",
        "chart_link": "https://chartink.com/stocks-new?from_scan=1&scan_link=scanlink:db8c18083f5668803c52fcae01bc1b8d&timeframe=daily&symbol=",
        "scan_clause": """( {cash} ( 
        ( {57960} not ( 
            latest close > 0 
        ) ) and 
        ( {cash} ( 
            latest close > 25 and 
            latest close < 2250 and 
            latest volume > latest sma( latest volume , 5 ) * 2.5 and 
            latest volume > 1 day ago volume * 1.8 and 
            latest volume > latest sma( latest volume , 20 ) * 2 and 
            latest close > latest open and 
            latest high - latest low > latest sma( latest high - latest low , 5 ) * 1.5 and 
            latest close > latest ema( latest close , 20 ) and 
            latest close > latest max( 20 , latest vwap ) and 
            [=1] 5 minute close < [=1] 5 minute open * 1.03 
        ) ) 
    ) )"""
    },
    {
    "name": "MAGIC FILTER RAHIM",
    "link": "https://chartink.com/screener/che-68",
    "scan_clause": """({57960}([0] 5 minute close > [0] 5 minute vwap and [0] 5 minute close > [-1] 5 minute vwap and [0] 5 minute close > [-2] 5 minute vwap and [0] 5 minute close > [0] 5 minute supertrend(10,1) and [0] 5 minute close > [-1] 5 minute supertrend(10,1) and [0] 5 minute close > [-2] 5 minute supertrend(10,1) and [0] 5 minute ema([0] 5 minute close,9) > [0] 5 minute supertrend(10,1) and [0] 5 minute close > 20 and [0] 5 minute close <= 2250 and latest close > latest open * 1.02))"""
    },
    {
        "name": "STRONG STOCKS NEGATIVE",
        "type": "admin",
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
        "type": "admin",
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
        "type": "admin",
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
        "type": "admin",
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
    "type": "admin",
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
    {
        "name": "DEEP High Momentum ✅",
        "type": "admin",
        "link": "https://chartink.com/screener/cash-price-volume-surge",
        "chart_link": "https://chartink.com/stocks-new?symbol=",
        "scan_clause": """( {cash} ( 
        latest volume > latest sma( latest volume , 20 ) * 1.5 and 
        latest close > latest vwap and 
        latest close > latest open and 
        latest close >= latest high * 0.98 and 
        latest close > latest ema( latest close , 20 ) and 
        latest close > 50 and 
        latest volume > 100000 and 
        [=1] 5 minute close < [=1] 5 minute open * 1.03 and 
        [=1] 5 minute close > [=1] 5 minute open * 0.97 
    ) )"""
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

# Global variable to store conditions cache
_conditions_cache = {
    'all_users': None,
    'users': {}
}

def load_user_conditions(user_id=None):
    """
    Load user conditions from the PostgreSQL database
    Returns list of conditions for the specified user, or empty list if none found
    """
    global _conditions_cache
    
    logger.info(f"[DEBUG] load_user_conditions called with user_id: {user_id}")
    
    # Skip loading during app initialization (before first request)
    from flask import has_request_context
    if not has_request_context() and not _conditions_cache['all_users']:
        logger.info("[DEBUG] No request context, returning empty list")
        return []
    
    # If no user_id provided, return admin conditions
    if user_id is None:
        logger.info("[DEBUG] No user_id provided, loading all conditions")
        if _conditions_cache['all_users'] is not None:
            logger.info(f"[DEBUG] Returning {len(_conditions_cache['all_users'])} conditions from cache")
            return _conditions_cache['all_users']
            
        try:
            logger.info("[DEBUG] Querying database for all conditions")
            cur = db.get_cursor()
            if not cur:
                logger.error("[DEBUG] Failed to get database cursor")
                return []
                
            cur.execute("""
                SELECT id, user_data->'account'->'conditions' as conditions 
                FROM users 
                WHERE user_data->'account'->'conditions' IS NOT NULL
                  AND jsonb_array_length(user_data->'account'->'conditions') > 0
            """)
            
            all_conditions = []
            for row in cur.fetchall():
                if row['conditions']:
                    logger.info(f"[DEBUG] Found {len(row['conditions'])} conditions for user {row['id']}")
                    all_conditions.extend(row['conditions'])
            
            _conditions_cache['all_users'] = all_conditions
            logger.info(f"[DEBUG] Loaded total {len(all_conditions)} conditions from database")
            return all_conditions
            
        except Exception as e:
            logger.error(f"[DEBUG] Error loading all conditions: {e}", exc_info=True)
            return []
    
    # For specific user
    try:
        user_id_int = int(user_id)  # Ensure user_id is an integer for the cache key
        
        # Try to get from cache first
        if user_id_int in _conditions_cache['users']:
            cached = _conditions_cache['users'][user_id_int]
            logger.info(f"[DEBUG] Returning {len(cached)} conditions from cache for user {user_id_int}")
            return cached
            
        # Query the database for user's conditions
        logger.info(f"[DEBUG] Querying database for conditions for user {user_id_int}")
        cur = db.get_cursor()
        if not cur:
            logger.error("[DEBUG] Failed to get database cursor")
            return []
            
        cur.execute("""
            SELECT user_data->'account'->'conditions' as conditions 
            FROM users 
            WHERE id = %s
              AND user_data->'account'->'conditions' IS NOT NULL
              AND jsonb_array_length(user_data->'account'->'conditions') > 0
        """, (user_id_int,))
        
        result = cur.fetchone()
        if not result or not result['conditions']:
            logger.info(f"[DEBUG] No conditions found for user {user_id_int}")
            return []
            
        # Cache the result
        _conditions_cache['users'][user_id_int] = result['conditions']
        logger.info(f"[DEBUG] Loaded {len(result['conditions'])} conditions for user {user_id_int}")
        return result['conditions']
        
    except Exception as e:
        logger.error(f"[DEBUG] Error loading conditions for user {user_id}: {e}", exc_info=True)
        return []

def save_user_conditions(user_id, conditions_list):
    """
    Save user conditions to the database for the specified user.
    
    Args:
        user_id: The ID of the user
        conditions_list: List of conditions to save
        
    Returns:
        bool: True if save was successful, False otherwise
    """
    logger.info(f"[DEBUG] Starting save_user_conditions for user_id: {user_id}")
    logger.info(f"[DEBUG] Conditions to save: {json.dumps(conditions_list, indent=2)}")
    cur = None
    
    try:
        # Validate conditions_list
        if not isinstance(conditions_list, list):
            logger.error("conditions_list must be a list")
            return False
            
        logger.info("[DEBUG] Validated conditions_list")
            
        # Remove duplicates based on condition name
        unique_conditions = []
        seen_names = set()
        
        for condition in conditions_list:
            if isinstance(condition, dict) and 'name' in condition:
                if condition['name'] not in seen_names:
                    seen_names.add(condition['name'])
                    unique_conditions.append(condition)
        
        if len(unique_conditions) < len(conditions_list):
            logger.warning(f"Removed {len(conditions_list) - len(unique_conditions)} duplicate conditions")
        
        logger.info(f"[DEBUG] Processed {len(unique_conditions)} unique conditions")
        
        # Convert user_id to integer if it's a string
        try:
            user_id_int = int(user_id)
            logger.info(f"[DEBUG] Converted user_id to int: {user_id_int}")
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid user_id format: {user_id}", exc_info=True)
            return False
            
        # Get a database cursor
        cur = db.get_cursor()
        if not cur:
            logger.error("Failed to get database cursor")
            return False
            
        logger.info("[DEBUG] Successfully got database cursor")
            
        # Update user's conditions in the database
        query = """
            UPDATE users 
            SET user_data = jsonb_set(
                COALESCE(user_data, '{}'::jsonb),
                '{account,conditions}'::text[],
                %s::jsonb,
                true
            )
            WHERE id = %s
            RETURNING id;
        """
        
        # Convert conditions to JSON string
        try:
            conditions_json = json.dumps(unique_conditions, ensure_ascii=False, default=str)
            logger.info(f"[DEBUG] Converted conditions to JSON")
        except (TypeError, ValueError) as e:
            logger.error(f"Error encoding conditions to JSON: {e}", exc_info=True)
            return False
        
        # Execute the update
        try:
            logger.info("[DEBUG] Executing database update query")
            logger.info(f"[DEBUG] Query: {query}")
            logger.info(f"[DEBUG] Params: {conditions_json}, {user_id_int}")
            
            cur.execute(query, (conditions_json, user_id_int))
            logger.info("[DEBUG] Query executed successfully")
            
            # Commit the transaction
            if db.conn is not None:
                db.conn.commit()
            logger.info("[DEBUG] Transaction committed successfully")
            
            # Check if update was successful
            if cur.rowcount == 0:
                logger.error(f"No user found with ID: {user_id_int}")
                return False
                
            logger.info(f"[DEBUG] Successfully updated {cur.rowcount} rows")
            logger.info(f"Successfully saved {len(unique_conditions)} conditions for user {user_id_int}")
            return True
            
        except Exception as e:
            logger.error(f"[DEBUG] Error executing query: {e}", exc_info=True)
            if 'db' in locals() and hasattr(db, 'conn') and db.conn is not None:
                db.conn.rollback()
                logger.info("[DEBUG] Transaction rolled back")
            raise
            
    except Exception as e:
        logger.error(f"Error in save_user_conditions: {e}", exc_info=True)
        if 'db' in locals() and hasattr(db, 'conn') and db.conn is not None:
            db.conn.rollback()
        return False
    finally:
        # Make sure to close the cursor
        if cur is not None:
            try:
                cur.close()
            except Exception as e:
                logger.error(f"Error closing cursor: {e}", exc_info=True)
                pass

def ensure_app_settings_table():
    """
    Ensure the app_settings table exists in the database
    """
    logger.info("Checking if app_settings table exists...")
    try:
        # Get a new cursor
        cur = db.get_cursor()
        if not cur:
            logger.error("Failed to get database cursor")
            return False
            
        try:
            # First, try to query the table directly
            cur.execute("""
                SELECT to_regclass('public.app_settings') IS NOT NULL;
            """)
            
            # Handle the result safely
            result = cur.fetchone()
            table_exists = False
            
            if result:
                # Handle both dictionary and tuple results
                if hasattr(result, 'keys') and result:  # It's a dictionary
                    # Get the first value from the dictionary
                    table_exists = list(result.values())[0]
                elif isinstance(result, (tuple, list)) and len(result) > 0:  # It's a tuple or list
                    table_exists = result[0]
                
                # Ensure boolean value
                table_exists = bool(table_exists)
            
            if not table_exists:
                logger.info("app_settings table does not exist, creating...")
                # Create the table
                cur.execute("""
                    CREATE TABLE app_settings (
                        id SERIAL PRIMARY KEY,
                        settings JSONB NOT NULL DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create the function and trigger in a separate transaction
                cur.execute("""
                    CREATE OR REPLACE FUNCTION update_modified_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """)
                
                cur.execute("""
                    CREATE TRIGGER update_app_settings_modtime
                    BEFORE UPDATE ON app_settings
                    FOR EACH ROW
                    EXECUTE FUNCTION update_modified_column();
                """)
                
                # Insert default settings
                default_settings = {
                    'refresh_interval': 20,
                    'mute_status': False,
                    'auto_refresh': True,
                    'theme': 'light',
                    'conditions': [],
                    'selected_conditions': [],
                    'user_conditions': [],
                    'notifications': True,
                    'sound_alert': True,
                    'volume': 0.5,
                    'last_update': None,
                    'version': '1.0.0'
                }
                
                cur.execute("""
                    INSERT INTO app_settings (id, settings) 
                    VALUES (1, %s)
                """, (json.dumps(default_settings),))
                
                logger.info("Created app_settings table and inserted default settings")
                
                # Commit the transaction
                if db.conn is not None:
                    db.conn.commit()
                
            return True
            
        except Exception as e:
            logger.error(f"Error in ensure_app_settings_table: {e}", exc_info=True)
            if 'db' in locals() and hasattr(db, 'conn') and db.conn is not None:
                db.conn.rollback()
            return False
            
    except Exception as e:
        logger.error(f"Error getting database connection: {e}", exc_info=True)
        return False
    finally:
        if 'cur' in locals() and cur:
            try:
                cur.close()
            except:
                pass

def load_settings():
    """
    Load settings from the database
    """
    default_settings = {
        'refresh_interval': 20,
        'mute_status': False,
        'conditions': [],
        'selected_conditions': [],
        'user_conditions': [],
        'auto_refresh': True,
        'theme': 'light',
        'notifications': True,
        'sound_alert': True,
        'volume': 0.5,
        'last_update': None,
        'version': '1.0.0'
    }
    try:
        if not ensure_app_settings_table():
            logger.error("Failed to ensure app_settings table exists")
            return default_settings
            
        logger.info("Loading settings from database...")
        cur = db.get_cursor()
        if not cur:
            logger.error("Failed to get database cursor")
            return default_settings
        
        try:
            # Try to get settings from the database
            cur.execute("""
                SELECT settings FROM app_settings 
                WHERE id = 1  -- Using a single row for settings
            """)
            
            result = cur.fetchone()
            
            # Handle both dictionary and tuple results
            if not result:
                logger.warning("No settings found in database, using default settings")
                return default_settings
                
            # Get the settings from the result (handling both dict and tuple)
            if isinstance(result, dict):
                settings = result.get('settings')
            else:  # tuple
                settings = result[0] if len(result) > 0 else None
                
            if not settings:
                logger.warning("Empty settings in database, using default settings")
                return default_settings
                
            # Ensure settings is a dictionary
            if not isinstance(settings, dict):
                logger.warning("Invalid settings format in database, using default settings")
                return default_settings
            
            if not isinstance(settings, dict):
                logger.warning("Invalid settings format in database, using default settings")
                return default_settings
                
            logger.info("Successfully loaded settings from database")
            
            # Ensure all default settings are present
            for key, value in default_settings.items():
                if key not in settings:
                    settings[key] = value
                    logger.info(f"Added missing setting {key} with default value {value}")
            
            # Ensure 'conditions' exists for backward compatibility
            if 'conditions' not in settings and 'selected_conditions' in settings:
                settings['conditions'] = settings['selected_conditions']
                logger.info("Migrated 'selected_conditions' to 'conditions'")
            
            return settings
            
        except Exception as e:
            logger.error(f"Error loading settings: {e}", exc_info=True)
            return default_settings
            
        finally:
            if 'cur' in locals() and cur:
                try:
                    cur.close()
                except:
                    pass
                    
    except Exception as e:
        logger.error(f"Unexpected error in load_settings: {e}", exc_info=True)
        return default_settings

def save_settings(settings):
    """
    Save settings to the database
    """
    try:
        logger.info("Getting database cursor...")
        cur = db.get_cursor()
        if not cur:
            logger.error("Failed to get database cursor")
            return False
        
        # Ensure settings is a dictionary
        if not isinstance(settings, dict):
            logger.error(f"Invalid settings type: {type(settings)}, expected dict")
            return False
            
        # Ensure required fields exist
        if 'conditions' not in settings:
            settings['conditions'] = []
        if 'selected_conditions' not in settings:
            settings['selected_conditions'] = settings.get('conditions', [])
            
        logger.info(f"Saving settings to database: {settings}")
            
        # Upsert settings into the database
        cur.execute("""
            INSERT INTO app_settings (id, settings)
            VALUES (1, %s)
            ON CONFLICT (id) 
            DO UPDATE SET settings = EXCLUDED.settings
            RETURNING id
        """, (json.dumps(settings),))
        
        # Verify the update
        result = cur.fetchone()
        if not result:
            logger.error("Failed to verify settings update")
            if db.conn is not None:
                db.conn.rollback()
            return False
            
        if db.conn is not None:
            db.conn.commit()
        logger.info("Successfully saved settings to database")
        return True
        
    except Exception as e:
        logger.error(f"Error saving settings: {e}", exc_info=True)
        if db.conn is not None:
            db.conn.rollback()
        return False

# Load existing settings on startup
# Load settings and ensure mute_status is properly set
app_settings = load_settings()
is_muted = app_settings.get('mute_status', False)  # Default to False if not set

@app.route('/clear_cache')
def clear_cache():
    # cache.clear()
    return "Cache cleared!"

@app.route('/update_mute_status', methods=['POST'])
def update_mute_status():
    global is_muted, app_settings
    data = request.get_json()
    is_muted = bool(data.get('isMuted', False))
    app_settings['mute_status'] = is_muted
    save_settings(app_settings)
    # logger.info(f"Mute status set to: {is_muted}")
    return jsonify({'status': 'success', 'isMuted': is_muted})

def fetch_and_process_data(session, condition, selected_conditions=None):
    """Fetch and process stock data using the provided session"""
    url = "https://chartink.com/screener/process"
    # Only log debug info if this is a selected condition
    if selected_conditions is None or condition['name'] in selected_conditions:
        # logger.info(f"Fetching data for condition: {condition['name']}")
        pass  # Add pass to create a valid indented block
    
    # Validate condition has required fields
    if 'scan_clause' not in condition or not condition['scan_clause']:
        logger.error(f"Missing scan_clause for condition: {condition['name']}")
        return []
    
    try:
        # Get CSRF token
        if selected_conditions is None or condition['name'] in selected_conditions:
            # logger.info("Fetching CSRF token...")
            pass
        r_data = session.get(url)
        r_data.raise_for_status()
        soup = bs(r_data.content, "lxml")
        meta = soup.find("meta", {"name": "csrf-token"})
        if not meta:
            logger.error("Could not find CSRF token")
            return {"error": "Could not find CSRF token"}
        
        header = {"x-csrf-token": meta["content"]}  # type: ignore
        # logger.info("CSRF token obtained successfully")

        try:
            # Format scan clause for API if needed
            scan_clause = condition["scan_clause"]
            
            # Log the actual request being sent
            if selected_conditions is None or condition['name'] in selected_conditions:
                # logger.info(f"Request URL: {url}")
                # logger.info(f"Request Headers: {header}")
                # logger.info(f"Request Data - scan_clause: {scan_clause[:100]}..." if len(scan_clause) > 100 else scan_clause)
                pass
            
            response = session.post(url, headers=header, data={"scan_clause": scan_clause})
            
            # Log response status
            if selected_conditions is None or condition['name'] in selected_conditions:
                # logger.info(f"Response Status for {condition['name']}: {response.status_code}")
                pass
            
            if response.status_code != 200:
                logger.error(f"Error response for {condition['name']}: {response.text[:200]}")
                return []
                
            response.raise_for_status()
            
            data = response.json()
            
            if 'scan_error' in data:
                logger.error(f"Scan error for {condition['name']}: {data['scan_error']}")
                logger.error(f"Condition that caused error: {scan_clause}")
                return []
            
            if 'data' not in data:
                logger.error(f"Invalid response format for {condition['name']}: {data}")
                return []
            
            # Log success
            if selected_conditions is None or condition['name'] in selected_conditions:
                # logger.info(f"Successfully fetched data for {condition['name']}, found {len(data['data'])} stocks")
                pass
            
            # Convert to DataFrame
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
                # Fetch data for built-in conditions
                for condition in admin_conditions:
                    stocks = fetch_and_process_data(session, condition)
                    if stocks:
                        new_scan_results[condition['name']] = stocks
                
                # Fetch data for user conditions
                user_conditions = load_user_conditions()
                for condition in user_conditions:
                    # Make sure the scan_clause is properly formatted for the API
                    if 'scan_clause' in condition and condition['scan_clause']:
                        # Format the scan clause properly for the API
                        if not condition['scan_clause'].strip().startswith('('):
                            # Wrap the scan clause in the required format if not already wrapped
                            formatted_scan_clause = f"( {{57960}} ( {condition['scan_clause']} ) )"
                            # logger.info(f"Formatted scan clause for {condition['name']}: {formatted_scan_clause}")
                    
                    # Debug log before fetching
                    # logger.info(f"Fetching data for user condition: {condition['name']}")
                    # logger.info(f"Scan clause: {condition.get('scan_clause', 'No scan clause')}")
                    
                    stocks = fetch_and_process_data(session, condition)
                    
                    # Debug log after fetching
                    if stocks:
                        if isinstance(stocks, list):
                            # logger.info(f"Found {len(stocks)} stocks for user condition: {condition['name']}")
                            new_scan_results[condition['name']] = stocks
                        else:
                            logger.error(f"Invalid stocks data for {condition['name']}: {stocks}")
                    else:
                        # logger.info(f"No stocks found for user condition: {condition['name']}")
                        # Initialize with empty list to ensure the condition appears in results
                        new_scan_results[condition['name']] = []

            # Update the global variables
            scan_results = new_scan_results
            
            # Load mute status from db.json
            settings = load_settings()
            is_muted = settings.get("mute_status", False)

                       
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

# Global session with custom user agent and retry logic
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'en-US,en;q=0.9',
    'Referer': 'https://chartink.com/screener/',
    'X-Requested-With': 'XMLHttpRequest'
})

def get_random_interval():
    """Return a random interval between 110 and 130 seconds"""
    return random.uniform(110, 130)

@app.route('/get-refresh-interval')
def get_refresh_interval():
    """Return the current refresh interval in seconds"""
    global countdown_timer
    
    # Get user's custom refresh interval if set
    custom_interval = None
    if current_user.is_authenticated:
        user_data = get_user_data(current_user.id)
        if user_data and 'account' in user_data and 'refresh_interval' in user_data['account']:
            custom_interval = user_data['account']['refresh_interval']
    
    return jsonify({
        'interval': custom_interval or countdown_timer,
        'next_refresh_in': countdown_timer,
        'is_custom': custom_interval is not None
    })

@app.route('/get-theme', methods=['GET'])
@login_required
def get_theme():
    """Return the user's saved theme preference ('dark' or 'light')"""
    user_data = get_user_data(current_user.id)
    theme = None
    if user_data and 'account' in user_data and 'profile' in user_data['account']:
        theme = user_data['account']['profile'].get('theme', 'light')
    return jsonify({'theme': theme or 'light'})

@app.route('/update-theme', methods=['POST'])
@login_required
def update_theme():
    """Update the user's theme preference ('dark' or 'light')"""
    try:
        data = request.get_json()
        theme = data.get('theme')
        if theme not in ('dark', 'light'):
            return jsonify({'success': False, 'message': 'Invalid theme'}), 400
        user_data = get_user_data(current_user.id)
        if not user_data:
            user_data = {'account': {'profile': {}}}
        if 'account' not in user_data:
            user_data['account'] = {}
        if 'profile' not in user_data['account']:
            user_data['account']['profile'] = {}
        user_data['account']['profile']['theme'] = theme
        cur = db.get_cursor()
        if not cur:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        cur.execute(
            "UPDATE users SET user_data = %s WHERE id = %s RETURNING id",
            (json.dumps(user_data), current_user.id)
        )
        db.conn.commit()
        return jsonify({'success': True, 'theme': theme})
    except Exception as e:
        if 'db' in locals() and hasattr(db, 'conn') and db.conn:
            db.conn.rollback()
        logger.error(f"Error updating theme: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/update-refresh-interval', methods=['POST'])
@login_required
def update_refresh_interval():
    """Update the user's refresh interval setting"""
    try:
        data = request.get_json()
        interval = data.get('interval')
        
        # Validate interval
        try:
            interval = int(interval)
            if interval < 30 or interval > 300:  # 30 seconds to 5 minutes
                return jsonify({'success': False, 'message': 'Interval must be between 30 and 300 seconds'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid interval value'}), 400
        
        # Update user's refresh interval in database
        user_data = get_user_data(current_user.id)
        if not user_data:
            user_data = {'account': {}}
        
        if 'account' not in user_data:
            user_data['account'] = {}
            
        user_data['account']['refresh_interval'] = interval
        
        # Save updated user data
        cur = db.get_cursor()
        if not cur:
            return jsonify({'success': False, 'message': 'Database error'}), 500
            
        cur.execute(
            "UPDATE users SET user_data = %s WHERE id = %s RETURNING id",
            (json.dumps(user_data), current_user.id)
        )
        db.conn.commit()
        
        return jsonify({
            'success': True,
            'message': 'Refresh interval updated successfully',
            'interval': interval
        })
        
    except Exception as e:
        if 'db' in locals() and hasattr(db, 'conn') and db.conn:
            db.conn.rollback()
        logger.error(f"Error updating refresh interval: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

def update_data():
    """
    Background thread function to update stock data with random intervals between 110-130 seconds
    
    This function:
    - Fetches fresh data with retry logic
    - Uses random intervals to avoid detection
    - Updates the countdown timer
    - Handles errors gracefully
    - Respects the running flag for clean shutdown
    """
    global running, countdown_timer, last_alert_time
    
    def _update_with_context():
        """Helper function to run with application context"""
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                with app.app_context():
                    # logger.info(f"Fetching data (attempt {attempt + 1}/{max_retries})")
                    fetch_data()
                    return True
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    logger.error("Max retries reached. Will retry after next interval.")
                    return False
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            except Exception as e:
                logger.error(f"Unexpected error in _update_with_context: {str(e)}", exc_info=True)
                return False
    
    while running:
        try:
            # Get the target time for the next update (110-130 seconds from now)
            next_update_time = time.time() + get_random_interval()
            
            # Run the update with application context
            success = _update_with_context()
            
            # Calculate actual time remaining until next update
            time_remaining = max(0, next_update_time - time.time())
            countdown_timer = int(time_remaining)
            last_alert_time = time.time()
            
            # logger.info(f"Update completed. Next update in {countdown_timer:.0f} seconds.")
            
            # Sleep in smaller intervals to allow for clean shutdown
            while time.time() < next_update_time and running:
                # Update remaining time
                time_remaining = max(0, next_update_time - time.time())
                countdown_timer = int(time_remaining)
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in update_data: {e}", exc_info=True)
            # On error, wait for a random time between 30-60 seconds before retrying
            error_wait = random.uniform(30, 60)
            # logger.info(f"Waiting {error_wait:.1f} seconds before retrying...")
            for _ in range(int(error_wait)):
                if not running:
                    break
                time.sleep(1)

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
    global scan_results
    
    try:
        # Get the selected conditions from settings
        settings = load_settings()
        selected_conditions = settings.get('conditions', [])
        
        # Load user conditions
        user_conditions = load_user_conditions()
        
        # Combine built-in and user conditions
        all_scan_conditions = admin_conditions.copy()
        all_scan_conditions.extend(user_conditions)
        
        # logger.info(f"Selected conditions: {selected_conditions}")
        # logger.info(f"User conditions: {[c['name'] for c in user_conditions]}")
        
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
        
        # If scan_results is None, fetch data first
        if scan_results is None:
            logger.warning("scan_results is None, attempting to fetch data")
            fetch_data()
            if scan_results is None:  # Still None after fetch attempt
                return jsonify({'error': 'Failed to fetch scan data'}), 500
        
        # Process user conditions if they're not already in scan_results
        with requests.Session() as session:
            for user_condition in user_conditions:
                try:
                    # Always process user conditions regardless of selection status
                    if user_condition['name'] in selected_conditions:
                        # logger.info(f"Processing user condition: {user_condition['name']}")
                        pass
                    
                    # Format scan clause if needed
                    if 'scan_clause' in user_condition and user_condition['scan_clause']:
                        if not user_condition['scan_clause'].strip().startswith('('):
                            # Wrap the scan clause in the required format if not already wrapped
                            formatted_clause = f"( {{57960}} ( {user_condition['scan_clause']} ) )"
                            # logger.info(f"Formatted scan clause for {user_condition['name']}: {formatted_clause}")
                            user_condition['scan_clause'] = formatted_clause
                    
                    if user_condition['name'] in selected_conditions:
                        # logger.info(f"Scan clause: {user_condition['scan_clause']}")
                        pass
                    data = fetch_and_process_data(session, user_condition, selected_conditions)
                    
                    if isinstance(data, pd.DataFrame) and not data.empty:
                        # Add to scan_results for future use
                        scan_results[user_condition['name']] = data.to_dict('records')
                        if user_condition['name'] in selected_conditions:
                            # logger.info(f"Found {len(data)} stocks for user condition: {user_condition['name']}")
                            pass
                    else:
                        # Initialize with empty list if no data
                        scan_results[user_condition['name']] = []
                        if user_condition['name'] in selected_conditions:
                            # logger.info(f"No stocks found for user condition: {user_condition['name']}")
                            pass
                except Exception as e:
                    logger.error(f"Error processing user condition {user_condition['name']}: {e}")
        
        # Now collect all results from scan_results
        for condition_name in selected_conditions:
            # Skip 'on' which is not a real condition
            if condition_name == 'on':
                continue
                
            # Check for name variations
            normalized_condition = name_variations.get(condition_name, condition_name)
            
            # Safely get stocks, default to empty list
            stocks = scan_results.get(normalized_condition, [])
            if not stocks:
                # Try with the original name if normalized didn't work
                stocks = scan_results.get(condition_name, [])
                
            # logger.info(f"Condition: {normalized_condition}, Stocks found: {len(stocks)}")
            
            if stocks:
                all_results[normalized_condition] = stocks
                found_stocks = True
        
        # If no stocks found, log a warning
        if not all_results:
            logger.warning("No stocks found for any selected conditions")
            return jsonify({'error': 'No stocks found for selected conditions'}), 404
        
        # Create response with no-cache headers
        response = make_response(jsonify(all_results))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
        
    except Exception as e:
        logger.error(f"Error in get_scan_results: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

DB_FILE = 'db.json'

def get_default_settings():
    """Get default settings structure"""
    return {
        "mute_status": False,
        'app_selected': 'app',
        'conditions': [c['name'] for c in admin_conditions],
        'browser': '0',
        'app': '1'
    }

@app.route('/db.json')
def serve_db_json():
    return send_from_directory('.', 'db.json')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# Authentication Routes

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login with proper session management."""
    logger.info("Login endpoint called")
    
    # Redirect if already logged in
    if current_user.is_authenticated:
        logger.info(f"User {current_user.username} already authenticated, redirecting to index")
        return redirect(url_for('index'))
    
    error = None
    
    # Handle POST request
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', 'true').lower() == 'true'
        
        logger.info(f"Login attempt for user: {username}, remember_me: {remember}")
        
        try:
            # Authenticate user
            user = authenticate_user(username, password)
            
            if user and user.id is not None:
                # Log in the user using Flask-Login with remember me
                login_success = login_user(user, remember=remember)
                
                if login_success:
                    # Configure session
                    session.permanent = True  # type: ignore
                    app.permanent_session_lifetime = timedelta(minutes=7)
                    
                    logger.info(f"Login successful for user: {user.username} (ID: {user.id})")
                    
                    # Create response
                    response = make_response(redirect(request.args.get('next') or url_for('index')))
                    
                    # Set remember me cookie if requested
                    if remember:
                        token = user.get_auth_token()
                        response.set_cookie(
                            'remember_token',
                            value=token,
                            max_age=420,  # 7 minutes
                            httponly=True,
                            samesite='Lax',
                            secure=app.config['SESSION_COOKIE_SECURE']
                        )
                        logger.debug(f"Set remember_token cookie for user {user.id}")
                    
                    return response
                else:
                    error = 'Login failed. Please try again.'
                    logger.warning(f"Login failed for user: {username}")
            else:
                error = 'Invalid username or password'
                logger.warning(f"Invalid credentials for user: {username}")
                
        except Exception as e:
            error = 'An error occurred during login. Please try again.'
            logger.error(f"Error during login for user {username}: {str(e)}", exc_info=True)
    
    return render_template('login.html', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email', '')
        name = request.form.get('name', username)
        phone = request.form.get('phone', '')
        address = request.form.get('address', '')
        
        # New profile fields
        premium = "yes"  # Default to "yes"
        dob = ""  # Default to empty string
        gender = "Prefer not to say"  # Default
        bio = "" # Default to empty string
        
        # You can add more fields as needed
        conditions = []  # Start with empty or default conditions
        misc1 = []
        misc2 = []
        misc3 = []
        misc4 = []
        misc5 = []
        misc6 = []
        misc7 = []
        misc8 = []
        misc9 = []
        misc10 = []
        
        if not username or not password:
            error = 'Username and password are required'
        else:
            # Create user data structure
            user_data = {
                'account': {
                    'username': username,
                    'password': password,
                    'email': email,
                    'profile': {
                        'name': name or username,
                        'phone': phone,
                        'address': address,
                        'premium': premium,
                        'dob': dob,
                        'gender': gender,
                        'bio': bio,
                        'photo_url': ''
                    },
                    'conditions': [],
                    'misc1': [],
                    'misc2': [],
                    'misc3': [],
                    'misc4': [],
                    'misc5': [],
                    'misc6': [],
                    'misc7': [],
                    'misc8': [],
                    'misc9': [],
                    'misc10': []
                }
            }
            
            # Get a new cursor for this transaction
            conn = db.conn
            cur = None
            try:
                # Start a new transaction
                conn = psycopg2.connect(
                    dbname="pitk",
                    user="pitk_user",
                    password="N63uWAQkpdSDg8SFvoggKxCDw5OY1aPx",
                    host="dpg-d1efmamuk2gs73allkt0-a.singapore-postgres.render.com",
                    port="5432"
                )
                conn.autocommit = False
                cur = conn.cursor()
                
                # Check if username already exists
                cur.execute("""
                    SELECT id FROM users 
                    WHERE user_data->'account'->>'username' = %s
                """, (username,))
                
                if cur.fetchone():
                    error = 'Username already exists'
                else:
                    # Hash the password before storing
                    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                    
                    # Update user_data with hashed password
                    user_data['account']['password'] = hashed_password
                    
                    # Insert new user into PostgreSQL with hashed password
                    cur.execute("""
                        INSERT INTO users (username, password_hash, user_data)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (username, hashed_password, json.dumps(user_data)))
                    
                    result = cur.fetchone()
                    if result:
                        user_id = result[0]
                        conn.commit()
                        
                        # Log the user in with the hashed password
                        user = User(id=str(user_id), username=username, password=hashed_password, email=email)
                        login_user(user)
                        return redirect(url_for('index'))
                    else:
                        print("❌ Failed to get user ID after insert")
                        error = 'Error creating user. Please try again.'
                
            except Exception as e:
                if 'conn' in locals() and conn is not None:
                    conn.rollback()
                error = 'Error creating user. Please try again.'
                print(f"Registration error: {str(e)}")
                traceback.print_exc()
            finally:
                if 'cur' in locals() and cur is not None:
                    cur.close()
                if 'conn' in locals() and conn is not None and conn.closed == 0:
                    conn.close()
    
    return render_template('register.html', error=error)

@app.route('/upload-photo', methods=['POST'])
@login_required
def upload_photo():
    if 'photo' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('dash'))
    file = request.files['photo']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('dash'))
    
    if file:
        try:
            # Create uploads directory if it doesn't exist
            upload_folder = os.path.join(app.static_folder or '.', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            
            # Generate a secure filename
            filename = secure_filename(file.filename or '')
            unique_filename = f"{uuid.uuid4()}_{filename}"
            filepath = os.path.join(upload_folder, unique_filename)
            
            # Save the file
            file.save(filepath)
            
            # Update the database with the relative path
            relative_path = f"/static/uploads/{unique_filename}"
            cur = db.get_cursor()
            if not cur:
                flash('Database connection error', 'danger')
                return redirect(url_for('dash'))
            
            # Update the user's photo path in the database
            query = """
                UPDATE users 
                SET user_data = jsonb_set(
                    COALESCE(user_data, '{}'::jsonb),
                    '{account,profile,photo_path}',
                    %s::jsonb
                )
                WHERE id = %s
                RETURNING id
            """
            
            cur.execute(query, (json.dumps(relative_path), current_user.id))
            
            if cur.rowcount == 0:
                flash('User not found', 'danger')
            else:
                if db.conn is not None:
                    db.conn.commit()
                flash('Profile picture updated successfully!', 'success')
                
        except Exception as e:
            if db.conn is not None:
                db.conn.rollback()
            # Clean up the file if there was an error
            if 'filepath' in locals() and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up file after error: {cleanup_error}")
            flash('Error updating profile picture.', 'danger')
            logger.error(f"Error updating photo: {e}")

    return redirect(url_for('dash'))

@app.route('/remove-photo', methods=['POST'])
@login_required
def remove_photo():
    try:
        cur = db.get_cursor()
        if not cur:
            flash('Database connection error', 'danger')
            print('[DEBUG] No database cursor')
            return redirect(url_for('dash'))
        
        # First, get the current photo path to delete the file
        get_photo_query = """
            SELECT user_data->'account'->'profile'->>'photo_path' as photo_path
            FROM users 
            WHERE id = %s
        """
        
        cur.execute(get_photo_query, (current_user.id,))
        result = cur.fetchone()
        print(f'[DEBUG] DB result for photo_path: {result}')
        
        if result and result.get('photo_path'):
            photo_path = result['photo_path'].lstrip('/')  # Remove leading slash for os.path
            print(f'[DEBUG] photo_path to remove: {photo_path}')
            
            # Delete the photo file if it exists
            try:
                file_exists = os.path.exists(photo_path)
                print(f'[DEBUG] File exists: {file_exists}')
                if file_exists:
                    os.remove(photo_path)
                    print('[DEBUG] File removed successfully')
                else:
                    print('[DEBUG] File does not exist, skipping removal')
            except Exception as e:
                logger.error(f"Error removing photo file: {e}")
                print(f'[DEBUG] Exception removing file: {e}')
                # Don't fail if file is already missing
        else:
            print('[DEBUG] No photo_path found in DB')
        
        # Remove the photo data from the database
        update_query = """
            WITH updated AS (
                SELECT id, user_data #- '{account,profile,photo_path}'::text[] as new_data
                FROM users
                WHERE id = %s
            )
            UPDATE users u
            SET user_data = updated.new_data
            FROM updated
            WHERE u.id = updated.id
            RETURNING u.id
        """
        
        cur.execute(update_query, (current_user.id,))
        print(f'[DEBUG] DB update rowcount: {cur.rowcount}')
        
        if cur.rowcount > 0:
            if db.conn is not None:
                db.conn.commit()
            flash('Profile picture removed successfully!', 'success')
            print('[DEBUG] DB commit successful')
        else:
            flash('No profile picture found to remove.', 'info')
            print('[DEBUG] No DB row updated')
            
    except Exception as e:
        logger.error(f"Error in remove_photo: {e}", exc_info=True)
        print(f'[DEBUG] Exception in remove_photo: {e}')
        if db.conn is not None:
            try:
                db.conn.rollback()
                print('[DEBUG] DB rollback successful')
            except Exception as rollback_err:
                logger.error(f"Error during rollback: {rollback_err}")
                print(f'[DEBUG] Exception during rollback: {rollback_err}')
        flash('Error removing profile picture.', 'danger')
    
    return redirect(url_for('dash'))

@app.route('/dash', methods=['GET', 'POST'])
@login_required
def dash():
    error = None
    success = None
    
    if request.method == 'POST':
        # Handle profile update
        if 'email' in request.form:
            try:
                # Get the current user ID
                user_id = current_user.id
                
                # Get the user's current data from PostgreSQL
                cur = db.get_cursor()
                if not cur:
                    logger.error("Failed to get database cursor")
                    return jsonify({'error': 'Database connection error'}), 500
                
                # Get current user data
                cur.execute("""
                    SELECT user_data FROM users WHERE id = %s
                """, (user_id,))
                
                result = cur.fetchone()
                if not result:
                    logger.error(f"User {user_id} not found in database")
                    return jsonify({'error': 'User not found'}), 404
                
                # Update the profile data
                # Handle both dictionary and tuple results
                if isinstance(result, dict):
                    user_data = result.get('user_data')
                else:  # tuple
                    user_data = result[0] if len(result) > 0 else None
                
                if not user_data:
                    logger.error(f"No user_data found for user {user_id}")
                    return jsonify({'error': 'User data not found'}), 404
                
                if 'account' not in user_data:
                    user_data['account'] = {}
                if 'profile' not in user_data['account']:
                    user_data['account']['profile'] = {}
                
                profile = user_data['account']['profile']
                
                # Update all profile fields from the form
                profile['email'] = request.form.get('email', profile.get('email', ''))
                profile['name'] = request.form.get('name', profile.get('name', ''))
                profile['dob'] = request.form.get('dob', profile.get('dob', ''))
                profile['gender'] = request.form.get('gender', profile.get('gender', 'Prefer not to say'))
                profile['bio'] = request.form.get('bio', profile.get('bio', ''))
                
                # Save the updated data back to PostgreSQL
                cur.execute("""
                    UPDATE users 
                    SET user_data = %s
                    WHERE id = %s
                    RETURNING id
                """, (json.dumps(user_data), user_id))
                
                if cur.rowcount == 0:
                    logger.error(f"Failed to update user {user_id} profile")
                    return jsonify({'error': 'Failed to update profile'}), 500
                
                if db.conn is not None:
                    db.conn.commit()
                success = 'Profile updated successfully!'
                
            except Exception as e:
                logger.error(f"Error updating profile: {e}", exc_info=True)
                if db.conn is not None:
                    db.conn.rollback()
                error = 'Error updating profile'
        
        # Handle password change
        elif 'current_password' in request.form and 'new_password' in request.form:
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            try:
                # Get the current user ID
                user_id = current_user.id
                
                # Update the user's password in the database
                try:
                    cur = db.get_cursor()
                    if not cur:
                        return jsonify({'error': 'Database connection error'}), 500
                    
                    # Hash the new password before storing
                    hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                    
                    # Update the user's password in the database
                    query = """
                        UPDATE users 
                        SET password_hash = %s
                        WHERE id = %s
                        RETURNING id
                    """
                    
                    cur.execute(query, (hashed_password, user_id))
                    
                    if cur.rowcount == 0:
                        return jsonify({'error': 'User not found'}), 404
                    if db.conn is not None:
                        db.conn.commit()
                    success = 'Password updated successfully!'
                except Exception as e:
                    logger.error(f"Database error updating user password: {e}")
                    if db.conn is not None:
                        db.conn.rollback()
                    error = 'Error changing password'
            except Exception as e:
                logger.error(f"Error changing password: {e}")
    
    # Load current user data
    try:
        # Get the current user ID
        user_id = current_user.id
        
        # Get the user's data from the database
        try:
            cur = db.get_cursor()
            if not cur:
                return jsonify({'error': 'Database connection error'}), 500
            
            # Get the user's data from the database
            query = """
                SELECT user_data 
                FROM users 
                WHERE id = %s
            """
            
            cur.execute(query, (user_id,))
            
            user_data = cur.fetchone()
            
            if not user_data:
                return jsonify({'error': 'User not found'}), 404
            
            # Handle both dictionary and tuple results
            if isinstance(user_data, dict):
                user_data = user_data.get('user_data')
            else:  # tuple
                user_data = user_data[0] if len(user_data) > 0 else None
            
            if not user_data:
                logger.error(f"No user_data found for user {user_id}")
                user_data = {}
                profile_data = {}
            else:
                profile_data = user_data.get('account', {}).get('profile', {})
        except Exception as e:
            logger.error(f"Database error getting user data: {e}")
            user_data = {}
            profile_data = {}
    
    except Exception as e:
        logger.error(f"Error getting user data: {e}")
        user_data = {}
        profile_data = {}

    today_str = date.today().strftime('%Y-%m-%d')
    
    # Set photo_url for template usage
    photo_path = profile_data.get('photo_path')
    if photo_path:
        profile_data['photo_url'] = photo_path
    else:
        profile_data['photo_url'] = None
    
    # Get refresh interval from user data if it exists
    refresh_interval = user_data.get('account', {}).get('refresh_interval')
    if refresh_interval is not None:
        profile_data['refresh_interval'] = refresh_interval
    # Get theme from user data if it exists
    theme = user_data.get('account', {}).get('profile', {}).get('theme', 'light')
    profile_data['theme'] = theme
    
    return render_template('dash.html', 
                         username=current_user.username,
                         email=profile_data.get('email', ''),
                         profile=profile_data,
                         theme=theme,
                         error=error,
                         success=success,
                         today=today_str)

# Test Endpoint
@app.route('/test')
def test():
    """Simple test endpoint to verify the server is working"""
    return jsonify({
        'status': 'success',
        'message': 'Server is running!',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }), 200

# Error Handlers

@app.errorhandler(AppTemporarilyUnavailable)
def handle_app_unavailable(error):
    """Handle application unavailability by showing the error page"""
    return render_template('error.html', error_message=error.description), error.code

# Main Application Routes

@app.route('/')
@login_required
def index():
    """Render the main index page"""
    # Start the background thread if not already started
    global threads_started
    if not threads_started:
        try:
            # start_background_thread()
            # logger.info("Background update_data thread started after first / visit.")
            pass
        except Exception as e:
            logger.error(f"Error starting background thread: {e}")
    
    # Ensure latest data is fetched
    try:
        fetch_data()
    except Exception as e:
        logger.error(f"Error in fetch_data: {e}")
    
    settings = load_settings()
    selected_conditions = settings.get('conditions', [])

    # If no conditions are selected, show a message to select conditions
    if not selected_conditions:
        flash_message = {
            'type': 'danger',
            'icon': 'fa-exclamation-triangle',
            'title': 'No Conditions Selected',
            'message': 'Please select conditions from Admin Conditions or create your own user conditions to view stock data.',
            'style': 'background-color: rgba(220, 53, 69, 0.2); border-left: 4px solid #dc3545; padding: 10px; border-radius: 4px;'
        }
    else:
        flash_message = None
    
    # Load user conditions and combine with built-in conditions
    user_conditions = load_user_conditions(current_user.id) if current_user.is_authenticated else []
    all_conditions = admin_conditions.copy()
    all_conditions.extend(user_conditions)
    
    # Categorize stocks into Buy/Sell
    buy_suggestions, sell_suggestions = categorize_stocks()

    # Debug log for scan results
    # logger.info(f"Scan results keys: {list(scan_results.keys() if scan_results else [])}")
    
    # Prepare conditions with their stocks
    conditions_with_stocks = []
    
    # First, add all user conditions regardless of selection status
    # This ensures they're always visible in the UI
    for condition in user_conditions:
        # Get stocks for this condition, default to empty list
        stocks = scan_results.get(condition["name"], [])
        if condition["name"] in selected_conditions:
            # logger.info(f"Adding user condition {condition['name']} with {len(stocks)} stocks")
            pass
        # Add condition with its stocks to the list
        conditions_with_stocks.append({**condition, "stocks": stocks, "is_custom": True})
    
    # Then add selected built-in conditions
    for condition in admin_conditions:
        # Check if this condition is selected
        if condition["name"] in selected_conditions:
            # Get stocks for this condition, default to empty list
            stocks = scan_results.get(condition["name"], [])
            # logger.info(f"Adding built-in condition {condition['name']} with {len(stocks)} stocks")
            # Add condition with its stocks to the list
            conditions_with_stocks.append({**condition, "stocks": stocks, "is_custom": False})
    
    # Debug log for conditions being displayed
    # logger.info(f"Conditions being displayed: {[c['name'] for c in conditions_with_stocks]}")
    
    # Make sure all selected conditions are included, even if they don't have stocks
    selected_condition_names = [c['name'] for c in conditions_with_stocks]
    for condition_name in selected_conditions:
        if condition_name not in selected_condition_names and condition_name != 'on':
            # Find the condition in all_conditions
            for condition in all_conditions:
                if condition['name'] == condition_name:
                    # logger.info(f"Adding missing condition: {condition_name}")
                    conditions_with_stocks.append({**condition, "stocks": []})
                    break

    # Get user data for the template
    user_data = None
    theme = 'light'
    if current_user.is_authenticated:
        user_data = get_user_data(current_user.id)
        if user_data and 'account' in user_data and 'profile' in user_data['account']:
            theme = user_data['account']['profile'].get('theme', 'light')
    return render_template('index.html',
                           user_data=user_data,
                           theme=theme,
                           conditions=conditions_with_stocks,
                           flash_message=flash_message,
                           buy_suggestions=buy_suggestions,
                           sell_suggestions=sell_suggestions)


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
        logger.info(f"Received update settings request: {data}")
        
        # Load current settings
        current_settings = load_settings()
        
        # Update only allowed fields
        if 'conditions' in data:
            logger.info(f"Updating conditions: {data['conditions']}")
            current_settings['conditions'] = data['conditions']
            current_settings['selected_conditions'] = data['conditions']  # Keep both for backward compatibility
        
        if 'selected_option' in data:
            logger.info(f"Updating selected option: {data['selected_option']}")
            current_settings['app_selected'] = data['selected_option']
            current_settings['browser'] = '1' if data['selected_option'] == 'browser' else '0'
            current_settings['app'] = '1' if data['selected_option'] == 'app' else '0'
        
        # Save settings to database
        logger.info("Saving settings to database...")
        if not save_settings(current_settings):
            logger.error("Failed to save settings to database")
            return jsonify({'success': False, 'error': 'Failed to save settings to database'}), 500
        
        logger.info("Settings saved successfully")
        return jsonify({
            'success': True, 
            'message': 'Settings updated successfully',
            'settings': current_settings
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}", exc_info=True)
        return jsonify({
            'success': False, 
            'error': f'Failed to update settings: {str(e)}'
        }), 500

@app.route('/conditions')
def get_conditions():
    # Combine built-in and user conditions
    all_conditions = admin_conditions.copy()
    
    # Add user conditions
    try:
        user_conditions = load_user_conditions()
        all_conditions.extend(user_conditions)
    except Exception as e:
        logger.error(f"Error loading user conditions: {e}")
    
    return jsonify(all_conditions)

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
        # logger.debug("Establishing session with NSE website")
        pre_response = session.get("https://www.nseindia.com", headers=headers)
        # logger.debug(f"Pre-session response status: {pre_response.status_code}")
        
        # Fetch indices data
        # logger.debug(f"Fetching data from URL: {url}")
        response = session.get(url, headers=headers)
        
        # Log full response details for debugging
        # logger.debug(f"Response status code: {response.status_code}")
        
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
            
            # logger.info(f"Fetched Nifty data: {nifty_data}")
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

def app3_logic():
    """
    Main logic for App3 that will be called by the Flask API.
    This function should return the data you want to send to the frontend.
    """
    try:
        # You can call any of your existing functions here
        # For example, to get Nifty indices data:
        data = get_nifty_data()
        return {
            'status': 'success',
            'data': data,
            'message': 'App3 data fetched successfully'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error in App3: {str(e)}'
        }

from flask import jsonify
from flask_cors import CORS

# Enable CORS for all routes
CORS(app)

@app.route('/app3')
def app3_output():
    try:
        # Test with simple data first
        test_data = {
            'status': 'success',
            'message': 'App3 is working!',
            'data': 'This is a test response from /app3'
        }
        return jsonify(test_data), 200, {'Content-Type': 'application/json'}
    except Exception as e:
        error_msg = f"Error in /app3: {str(e)}"
        logger.error(error_msg)
        return jsonify({'status': 'error', 'message': error_msg}), 500, {'Content-Type': 'application/json'}

@app.route('/api/user-conditions', methods=['GET'])
@login_required
def get_user_conditions():
    """Get all user conditions for the current user"""
    try:
        logger.info(f"Fetching conditions for user: {current_user.id}")
        
        # Load conditions for the current user
        conditions = load_user_conditions(current_user.id)
        
        if not isinstance(conditions, list):
            logger.warning(f"Invalid conditions format for user {current_user.id}, initializing empty list")
            conditions = []
            
        logger.debug(f"Found {len(conditions)} conditions for user {current_user.id}")
        
        return jsonify({
            'success': True,
            'status': 'success',
            'user_conditions': conditions,
            'count': len(conditions)
        })
        
    except Exception as e:
        error_msg = f"Error getting user conditions: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'success': False,
            'status': 'error',
            'message': 'Failed to load user conditions',
            'error': str(e)
        }), 500

@app.route('/api/user-conditions', methods=['POST'])
@login_required
def add_user_condition():
    """Add a new user condition"""
    try:
        # Validate request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'status': 'error',
                'error': 'No data provided'
            }), 400
            
        # Validate required fields
        required_fields = ['name', 'scan_clause']
        missing_fields = [field for field in required_fields if field not in data or not str(data[field]).strip()]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'status': 'error',
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'missing_fields': missing_fields
            }), 400
        
        # Get current user's conditions
        conditions = load_user_conditions(current_user.id)
        if not isinstance(conditions, list):
            conditions = []
            
        # Check for duplicate name (case-insensitive)
        name = str(data['name']).strip()
        if any(str(c.get('name', '')).lower() == name.lower() for c in conditions):
            return jsonify({
                'success': False,
                'status': 'error',
                'error': 'A condition with this name already exists'
            }), 400
        
        # Prepare condition data with defaults
        condition_data = {
            'id': f"user_condition_{int(time.time() * 1000)}",  # Use timestamp for unique ID
            'name': name,
            'scan_clause': str(data['scan_clause']).strip(),
            'link': str(data.get('link', '')).strip() or '#',
            'chart_link': str(data.get('chart_link', '')).strip() or ''
        }
        
        # If chart_link is empty, use link as fallback
        if not condition_data['chart_link'] and condition_data['link'] != '#':
            condition_data['chart_link'] = condition_data['link']
        
        # Add to conditions list
        conditions.insert(0, condition_data)
        
        # Save to database
        if save_user_conditions(current_user.id, conditions):
            logger.info(f"Added new condition '{condition_data['name']}' for user {current_user.id}")
            return jsonify({
                'success': True,
                'status': 'success',
                'message': 'Condition added successfully',
                'id': condition_data['id'],
                'condition': condition_data
            }), 201
        else:
            raise Exception("Failed to save condition to database")
            
    except Exception as e:
        error_msg = f"Error adding user condition: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'success': False,
            'status': 'error',
            'error': 'Failed to add condition',
            'message': str(e)
        }), 500

@app.route('/api/user-conditions/<condition_id>', methods=['PUT'])
@login_required
def update_user_condition(condition_id):
    """Update an existing user condition"""
    try:
        if not condition_id:
            return jsonify({
                'success': False,
                'status': 'error',
                'error': 'Condition ID is required'
            }), 400
            
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'status': 'error',
                'error': 'No data provided'
            }), 400
            
        # Validate required fields
        required_fields = ['name', 'scan_clause']
        missing_fields = [field for field in required_fields if field not in data or not str(data[field]).strip()]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'status': 'error',
                'error': f'Missing required fields: {", ".join(missing_fields)}',
                'missing_fields': missing_fields
            }), 400
            
        # Get current user's conditions
        conditions = load_user_conditions(current_user.id)
        if not isinstance(conditions, list):
            conditions = []
        
        # Check for duplicate name (case-insensitive, excluding current condition)
        name = str(data['name']).strip()
        if any(str(c.get('name', '')).lower() == name.lower() 
               for c in conditions 
               if c.get('id') != condition_id):
            return jsonify({
                'success': False,
                'status': 'error',
                'error': 'A condition with this name already exists'
            }), 400
        
        # Find and update the condition
        updated = False
        updated_condition = None
        
        for condition in conditions:
            if str(condition.get('id')) == str(condition_id):
                # Update fields
                condition.update({
                    'name': name,
                    'scan_clause': str(data['scan_clause']).strip(),
                    'link': str(data.get('link', condition.get('link', ''))).strip() or '#',
                    'chart_link': str(data.get('chart_link', condition.get('chart_link', ''))).strip()
                })
                
                # If chart_link is empty, use link as fallback
                if not condition['chart_link'] and condition['link'] != '#':
                    condition['chart_link'] = condition['link']
                    
                updated_condition = condition
                updated = True
                break
        
        if not updated:
            return jsonify({
                'success': False,
                'status': 'error',
                'error': 'Condition not found'
            }), 404
        
        # Save to database
        if save_user_conditions(current_user.id, conditions):
            logger.info(f"Updated condition '{condition_id}' for user {current_user.id}")
            return jsonify({
                'success': True,
                'status': 'success',
                'message': 'Condition updated successfully',
                'condition': updated_condition
            })
        else:
            raise Exception("Failed to update condition in database")
            
    except Exception as e:
        error_msg = f"Error updating user condition: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'success': False,
            'status': 'error',
            'error': 'Failed to update condition',
            'message': str(e)
        }), 500

@app.route('/api/user-conditions/<condition_id>', methods=['DELETE'])
@login_required
def delete_user_condition(condition_id):
    """Delete a user condition"""
    try:
        if not condition_id or not str(condition_id).strip():
            return jsonify({
                'success': False,
                'status': 'error',
                'error': 'Condition ID is required'
            }), 400
            
        condition_id = str(condition_id).strip()
        logger.info(f"Deleting condition {condition_id} for user {current_user.id}")
        
        # Get current user's conditions
        conditions = load_user_conditions(current_user.id)
        if not isinstance(conditions, list):
            conditions = []
        
        # Find and remove the condition
        initial_count = len(conditions)
        updated_conditions = [
            c for c in conditions 
            if str(c.get('id', '')).strip() != condition_id
        ]
        
        if len(updated_conditions) == initial_count:
            return jsonify({
                'success': False,
                'status': 'error',
                'error': 'Condition not found'
            }), 404
        
        # Save to database
        if save_user_conditions(current_user.id, updated_conditions):
            logger.info(f"Deleted condition {condition_id} for user {current_user.id}")
            return jsonify({
                'success': True,
                'status': 'success',
                'message': 'Condition deleted successfully'
            })
        else:
            raise Exception("Failed to delete condition from database")
            
    except Exception as e:
        error_msg = f"Error deleting user condition: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'success': False,
            'status': 'error',
            'error': 'Failed to delete condition',
            'message': str(e)
        }), 500

@app.route('/reset-profile', methods=['POST'])
@login_required
def reset_profile():
    """Reset user profile data to default values except username. Also delete the user's uploaded profile image if it exists."""
    try:
        # Get the current user ID
        user_id = current_user.id
        
        # Get the user's current data from PostgreSQL
        cur = db.get_cursor()
        if not cur:
            logger.error("Failed to get database cursor")
            return jsonify({'success': False, 'error': 'Database connection error'}), 500
        
        # Get current user data
        cur.execute("""
            SELECT user_data FROM users WHERE id = %s
        """, (user_id,))
        
        result = cur.fetchone()
        if not result:
            logger.error(f"User {user_id} not found in database")
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Handle both dictionary and tuple results
        if isinstance(result, dict):
            user_data = result.get('user_data')
        else:  # tuple
            user_data = result[0] if len(result) > 0 else None
        
        if not user_data:
            logger.error(f"No user_data found for user {user_id}")
            return jsonify({'success': False, 'error': 'User data not found'}), 404
        
        # Ensure account and profile structure exists
        if 'account' not in user_data:
            user_data['account'] = {}
        if 'profile' not in user_data['account']:
            user_data['account']['profile'] = {}
        
        profile = user_data['account']['profile']
        # Delete the user's uploaded photo if it exists
        photo_path = profile.get('photo_path', '')
        if photo_path and '/static/uploads/' in photo_path:
            # Remove leading slash for os.path
            file_path = photo_path.lstrip('/')
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted user profile image: {file_path}")
                except Exception as e:
                    logger.error(f"Error deleting user profile image: {e}")
        
        # Get current username and premium status to preserve them
        current_username = user_data['account'].get('username', '')
        current_premium = user_data['account'].get('profile', {}).get('premium', 'no')
        
        # Reset profile fields to default values
        user_data['account']['profile'] = {
            'name': '',  # Reset to empty (not username)
            'email': '',  # Reset to empty
            'premium': current_premium,  # Preserve premium status
            'dob': '',  # Reset to empty
            'gender': 'Prefer not to say',  # Reset to default
            'bio': '',  # Reset to empty
            'photo_path': '',  # Reset to empty (will remove photo)
            'photo_url': ''  # Reset to empty
        }
        
        # Save the updated data back to PostgreSQL
        cur.execute("""
            UPDATE users 
            SET user_data = %s
            WHERE id = %s
            RETURNING id
        """, (json.dumps(user_data), user_id))
        
        if cur.rowcount == 0:
            logger.error(f"Failed to update user {user_id} profile")
            return jsonify({'success': False, 'error': 'Failed to update profile'}), 500
        
        if db.conn is not None:
            db.conn.commit()
        
        logger.info(f"Successfully reset profile for user {user_id}")
        return jsonify({'success': True, 'message': 'Profile reset successfully'})
        
    except Exception as e:
        logger.error(f"Error resetting profile: {e}", exc_info=True)
        if db.conn is not None:
            db.conn.rollback()
        return jsonify({'success': False, 'error': 'Error resetting profile'}), 500

def start_threads_once():
    """Start all background threads if they're not already running"""
    global update_thread
    try:
        if not hasattr(start_threads_once, '_has_run'):
            update_thread = threading.Thread(target=update_data, daemon=True)
            update_thread.start()
            start_threads_once._has_run = True
    except Exception as e:
        logger.error(f"Error starting threads: {e}")

def cleanup():
    pass

# Main execution
if __name__ == '__main__':
    # Ensure database tables exist
    if not ensure_app_settings_table():
        print("❌ Failed to verify/create app_settings table")
    
    # Start threads immediately when run directly
    start_threads_once()
    
    # Run the Flask app in standalone mode if this file is executed directly
    app.run(host='0.0.0.0', port=5000, debug=True)