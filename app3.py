import atexit
from datetime import datetime, date, timezone
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
import winsound
import os

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
import os
import json
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
import os
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or os.urandom(24).hex()

# Configure session to be permanent and set timeout
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour in seconds
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configure Flask-Login
app.config['REMEMBER_COOKIE_DURATION'] = 3600  # 1 hour in seconds
app.config['REMEMBER_COOKIE_HTTPONLY'] = True
app.config['REMEMBER_COOKIE_SECURE'] = False  # Set to True in production with HTTPS

# Initialize Bcrypt
bcrypt = Bcrypt(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

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
            import traceback
            traceback.print_exc()
            return None
            
    except Exception as e:
        print(f"❌ [get_user_data] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None

# Add get_user_data to template context
@app.context_processor
def utility_processor():
    def get_user_data_processor(user_id):
        return get_user_data(user_id)
    return dict(get_user_data=get_user_data_processor)

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
        # Try to convert to integer for database query
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
            print(f"❌ [load_user] Invalid user_id format: {user_id}")
            return None
            
        # Get database cursor
        cur = db.get_cursor()
        if not cur:
            print("❌ [load_user] Failed to get database cursor")
            return None
            
        try:
            # Query user data with explicit column selection
            cur.execute("""
                SELECT 
                    id::text as id,
                    user_data->'account'->>'username' as username,
                    user_data->'account'->>'password' as password,
                    COALESCE(
                        user_data->'account'->'profile'->>'email', 
                        user_data->'account'->>'email', 
                        ''
                    ) as email
                FROM users 
                WHERE id = %s
            """, (user_id_int,))
            
            # Get column names and convert to dictionary
            columns = [desc[0] for desc in cur.description] if cur.description else []
            row = cur.fetchone()
            
            if not row:
                print(f"❌ [load_user] No user found with ID: {user_id_int}")
                return None
                
            user_data = dict(zip(columns, row))
            print(f"✅ [load_user] Successfully loaded user: {user_data.get('username')} (ID: {user_data.get('id')})")
            
            # Ensure all required fields exist
            if not all(k in user_data for k in ['id', 'username', 'password']):
                print(f"❌ [load_user] Missing required user data fields: {user_data}")
                return None
                
            # Create and return user object
            return User(
                id=user_data['id'],
                username=user_data['username'],
                password=user_data['password'],
                email=user_data.get('email', '')
            )
            
        except Exception as query_error:
            print(f"❌ [load_user] Database query failed: {query_error}")
            import traceback
            traceback.print_exc()
            return None
            
    except Exception as e:
        print(f"❌ [load_user] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return None
        return None

# Hardcoded admin credentials for development (REMOVE IN PRODUCTION)
HARDCODED_ADMINS = {
    'imjjrobo': 'ccc',
    'indianplans': 'ccc',
    'rahi': 'ccc'
}

def authenticate_user(username, password):
    try:
        print(f"🔍 Attempting to authenticate user: {username}")
        
        # Check hardcoded admin credentials first (for development only)
        if username in HARDCODED_ADMINS and HARDCODED_ADMINS[username] == password:
            print(f"✅ Authenticated as hardcoded admin: {username}")
            # Return a mock admin user with ID 1
            return User(id=1, username=username, password=password, email=f"{username}@example.com")
            
        # Proceed with database authentication for non-hardcoded users
        cur = db.get_cursor()
        
        # First, let's check if the user exists
        cur.execute("""
            SELECT id, 
                   user_data->'account'->>'username' as username,
                   user_data->'account'->>'password' as password_hash,
                   COALESCE(user_data->'account'->'profile'->>'email', 
                           user_data->'account'->>'email', '') as email
            FROM users 
            WHERE user_data->'account'->>'username' = %s
        """, (username,))
        user_data = cur.fetchone()
        
        if not user_data:
            print(f"❌ User '{username}' not found in database")
            return None
            
        # Convert to dictionary if it's not already
        if not isinstance(user_data, dict):
            columns = [desc[0] for desc in cur.description]
            user_data = dict(zip(columns, user_data))
            
        print(f"✅ Found user: {user_data['username']} (ID: {user_data['id']})")
        print(f"🔑 Password hash: {user_data['password_hash'][:20]}...")
        
        # Check if this is an admin user (IDs 1, 2, 3) with plain text password
        is_admin_user = user_data['id'] in [1, 2, 3]
        
        if is_admin_user:
            # For admin users, use plain text password comparison
            print(f"🔑 Admin user ID: {user_data['id']}, Username: {user_data['username']}")
            print(f"🔑 Using plain text password check for admin user")
            password_matches = (user_data['password_hash'] == password)
            print(f"🔑 Password check result: {password_matches}")
        else:
            # For regular users, use bcrypt hash verification
            if not user_data['password_hash']:
                print("❌ No password hash found for user")
                return None
            print(f"🔑 Using bcrypt hash verification for regular user")
            password_matches = bcrypt.check_password_hash(user_data['password_hash'], password)
            print(f"🔑 Password check result: {password_matches}")
        
        if password_matches:
            print(f"✅ Authentication successful for user: {username}")
            return User(id=user_data['id'],
                      username=user_data['username'],
                      password=user_data['password_hash'],
                      email=user_data['email'])
        else:
            print("❌ Password does not match")
            return None
            
    except Exception as e:
        import traceback
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
        
        # Insert new user
        cur.execute("""
            INSERT INTO users (username, user_data)
            VALUES (%s, %s)
            RETURNING id
        """, (username, json.dumps(user_data)))
        
        user_id = cur.fetchone()[0]
        db.conn.commit()
        return str(user_id)
        
    except Exception as e:
        print(f"Error saving user: {e}")
        if 'db' in locals() and hasattr(db, 'conn'):
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
def format_number(value, column_type='default'):
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

from user_manager import user_manager

# Global variable to store conditions cache
_conditions_cache = {
    'all_users': None,
    'users': {}
}

def load_user_conditions(user_id=None):
    """
    Load user conditions from the PostgreSQL database
    Returns list of conditions for the specified user
    """
    global _conditions_cache
    
    # Skip loading during app initialization (before first request)
    from flask import has_request_context
    if not has_request_context() and not _conditions_cache['all_users']:
        return []
        
    try:
        print(f"🔍 [DEBUG] load_user_conditions called with user_id: {user_id}")
        
        if user_id is None:
            # Check cache first
            if _conditions_cache['all_users'] is not None:
                return _conditions_cache['all_users']
                
            # This is a special case - get all conditions from all users
            print("⚠️ [DEBUG] No user_id provided, fetching all conditions from all users")
            all_conditions = []
            try:
                cur = db.get_cursor()
                cur.execute("""
                    SELECT user_data->'account'->'conditions' as conditions 
                    FROM users 
                    WHERE user_data->'account'->'conditions' IS NOT NULL
                """)
                
                for row in cur.fetchall():
                    if row['conditions']:
                        all_conditions.extend(row['conditions'])
                
                # Update cache
                _conditions_cache['all_users'] = all_conditions
                print(f"🔍 [DEBUG] Total conditions found across all users: {len(all_conditions)}")
                return all_conditions
                
            except Exception as e:
                error_msg = f"Error fetching all user conditions: {e}"
                logger.error(error_msg, exc_info=True)
                print(f"❌ [DEBUG] {error_msg}")
                return []
        
        # Get conditions for specific user
        print(f"🔍 [DEBUG] Getting conditions for user_id: {user_id} from PostgreSQL")
        try:
            cur = db.get_cursor()
            
            # First, let's see what the user data actually looks like
            cur.execute("""
                SELECT user_data, id, username 
                FROM users 
                WHERE id = %s
            """, (user_id,))
            
            result = cur.fetchone()
            if not result:
                print(f"🔍 [DEBUG] No user found with id {user_id}")
                return []
                
            print(f"🔍 [DEBUG] Raw user data for {result['username']} (ID: {result['id']}): {result['user_data']}")
            
            # Now try to get conditions from the expected path
            cur.execute("""
                SELECT user_data->'account'->'conditions' as conditions 
                FROM users 
                WHERE id = %s
            """, (user_id,))
            
            result = cur.fetchone()
            if not result or not result['conditions']:
                print(f"🔍 [DEBUG] No conditions found in the expected path for user {user_id}")
                return []
                
            conditions = result['conditions']
            print(f"🔍 [DEBUG] Found {len(conditions)} conditions for user {user_id}")
            if conditions:
                print(f"🔍 [DEBUG] First condition: {conditions[0]}")
            return conditions
            
        except Exception as e:
            error_msg = f"Error fetching conditions for user {user_id}: {e}"
            logger.error(error_msg, exc_info=True)
            print(f"❌ [DEBUG] {error_msg}")
            return []
            
    except Exception as e:
        error_msg = f"Unexpected error in load_user_conditions: {e}"
        logger.error(error_msg, exc_info=True)
        print(f"❌ [DEBUG] {error_msg}")
        import traceback
        traceback.print_exc()
        return []
        return []

def save_user_conditions(user_id, conditions_list):
    """
    Save user conditions to the user's account in users.json
    Uses the UserManager for safe, atomic operations
    """
    try:
        return user_manager.save_user_conditions(user_id, conditions_list)
    except Exception as e:
        logger.error(f"Error saving user conditions: {e}", exc_info=True)
        return False

def clean_duplicate_users():
    """Clean up any duplicate user entries in users.json"""
    try:
        if not os.path.exists('users.json'):
            return
            
        with open('users.json', 'r', encoding='utf-8') as f:
            users_data = json.load(f)
        
        # Find and remove any duplicate user entries (keeping the one with the most data)
        clean_data = {}
        for key, value in users_data.items():
            if not key.startswith('user_'):
                continue
                
            user_num = key.replace('user_', '')
            if user_num.isdigit():
                clean_key = f'user_{user_num}'
                if clean_key not in clean_data:
                    clean_data[clean_key] = value
                else:
                    # Keep the one with more data (simple heuristic: more keys in account)
                    if isinstance(clean_data[clean_key], dict) and isinstance(clean_data[clean_key].get('account', {}), dict):
                        if len(str(value.get('account', {}))) > len(str(clean_data[clean_key].get('account', {}))):
                            clean_data[clean_key] = value
        
        # Only write back if we made changes
        if clean_data != users_data:
            with open('users.json', 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, indent=2, ensure_ascii=False, sort_keys=True)
                
    except Exception as e:
        logger.error(f"Error cleaning duplicate users: {e}", exc_info=True)
        
        return True
        
    except Exception as e:
        logger.error(f"Error saving user conditions: {e}", exc_info=True)
        return False

def load_settings():
    """
    Load settings from JSON file
    """
    # Create default settings with built-in conditions
    default_settings = {
        "mute_status": False,
        'app_selected': 'app',
        'conditions': [c['name'] for c in admin_conditions],
        'refresh_interval': 120,
        'filter_stocks': True,
        'filter_threshold': 0.5,
        'browser': '0',
        'app': '1'
    }
    
    # Try to add user conditions if they exist
    try:
        user_conditions = load_user_conditions()
        if user_conditions:
            # Add user condition names to default selected conditions
            for user_condition in user_conditions:
                if user_condition['name'] not in default_settings['conditions']:
                    default_settings['conditions'].append(user_condition['name'])
    except Exception as e:
        logger.error(f"Error adding user conditions to settings: {e}")

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
        
        header = {"x-csrf-token": meta["content"]}
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
    return jsonify({
        'interval': countdown_timer,
        'next_refresh_in': countdown_timer
    })

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
            logger.error(f"Error in _update_with_context: {e}", exc_info=True)
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
    print("\n=== Login Attempt ===")
    print(f"Current user authenticated: {current_user.is_authenticated}")
    
    # Redirect if already logged in
    if current_user.is_authenticated:
        print(f"User {current_user.username} already authenticated, redirecting to index")
        return redirect(url_for('index'))
    
    error = None
    
    # Handle POST request
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        print(f"🔑 Login attempt for user: {username}")
        
        try:
            # Authenticate user
            user = authenticate_user(username, password)
            
            if user and user.id is not None:
                # Log in the user using Flask-Login
                login_success = login_user(user)
                
                if login_success:
                    print(f"✅ Login successful for user: {user.username} (ID: {user.id})")
                    # Redirect to the next page or home
                    next_page = request.args.get('next')
                    if next_page and next_page.startswith('/'):
                        return redirect(next_page)
                    return redirect(url_for('index'))
                else:
                    error = 'Login failed. Please try again.'
            else:
                error = 'Invalid username or password'
                print(f"❌ Login failed for user: {username}")
        except Exception as e:
            error = 'An error occurred during login. Please try again.'
            print(f"❌ Error during login for user {username}: {str(e)}")
            import traceback
            traceback.print_exc()
    
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
                    
                    # Get the user ID and commit the transaction
                    user_id = cur.fetchone()[0]
                    conn.commit()
                    
                    # Log the user in with the hashed password
                    user = User(id=str(user_id), username=username, password=hashed_password, email=email)
                    login_user(user)
                    return redirect(url_for('index'))
                
            except Exception as e:
                if 'conn' in locals() and conn is not None:
                    conn.rollback()
                error = 'Error creating user. Please try again.'
                print(f"Registration error: {str(e)}")
                import traceback
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
        filename = secure_filename(file.filename)
        # Create a unique filename to prevent overwrites
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        unique_filename = f"user_{current_user.id}.{ext}"
        
        # Check for existing photo and delete it
        try:
            # Get current user's photo URL
            cur = db.get_cursor()
            cur.execute("""
                SELECT user_data->'account'->'profile'->>'photo_url' 
                FROM users 
                WHERE id = %s
            """, (current_user.id,))
            result = cur.fetchone()
            
            if result and result[0]:
                old_photo_url = result[0]
                # Don't delete default images
                if old_photo_url and 'default' not in old_photo_url:
                    relative_path = old_photo_url.lstrip('/static/')
                    old_photo_abs_path = os.path.join(app.static_folder, relative_path)
                    if os.path.exists(old_photo_abs_path):
                        os.remove(old_photo_abs_path)
        except Exception as e:
            logger.error(f"Error removing old photo: {e}")

        file_path = os.path.join(app.static_folder, 'user_photos', unique_filename)
        file.save(file_path)
        
        # Update user's photo_url in users.json
        try:
            with open('users.json', 'r') as f:
                users = json.load(f)
            users[str(current_user.id)]['account']['profile']['photo_url'] = f"/static/user_photos/{unique_filename}"
            with open('users.json', 'w') as f:
                json.dump(users, f, indent=4)
            flash('Profile picture updated successfully!', 'success')
        except Exception as e:
            flash('Error updating profile picture.', 'danger')
            logger.error(f"Error updating photo url in users.json: {e}")

    return redirect(url_for('dash'))

@app.route('/remove-photo', methods=['POST'])
@login_required
def remove_photo():
    try:
        with open('users.json', 'r') as f:
            users = json.load(f)
        
        profile_data = users.get(str(current_user.id), {}).get('account', {}).get('profile', {})
        if profile_data and profile_data.get('photo_url'):
            old_photo_url = profile_data['photo_url']
            if old_photo_url and 'default' not in old_photo_url:
                relative_path = old_photo_url.lstrip('/static/')
                old_photo_abs_path = os.path.join(app.static_folder, relative_path)
                if os.path.exists(old_photo_abs_path):
                    os.remove(old_photo_abs_path)
            
            users[str(current_user.id)]['account']['profile']['photo_url'] = ""
            with open('users.json', 'w') as f:
                json.dump(users, f, indent=4)
            flash('Profile picture removed.', 'success')
    except Exception as e:
        flash('Error removing profile picture.', 'danger')
        logger.error(f"Error removing photo: {e}")
        
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
                with open('users.json', 'r') as f:
                    users = json.load(f)
                
                profile = users[str(current_user.id)]['account']['profile']
                profile['email'] = request.form.get('email', profile.get('email'))
                profile['name'] = request.form.get('name', profile.get('name'))
                profile['dob'] = request.form.get('dob', profile.get('dob'))
                profile['gender'] = request.form.get('gender', profile.get('gender'))
                profile['bio'] = request.form.get('bio', profile.get('bio'))
                
                with open('users.json', 'w') as f:
                    json.dump(users, f, indent=4)
                success = 'Profile updated successfully!'
            except Exception as e:
                error = 'Error updating profile'
                print(f"Error updating profile: {e}")
        
        # Handle password change
        elif 'current_password' in request.form and 'new_password' in request.form:
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            try:
                with open('users.json', 'r') as f:
                    users = json.load(f)
                
                user_data = users[str(current_user.id)]
                if user_data.get('password') == current_password:  # Direct comparison for plain text
                    users[str(current_user.id)]['password'] = new_password  # Store new password in plain text
                    with open('users.json', 'w') as f:
                        json.dump(users, f, indent=2)
                    success = 'Password updated successfully!'
                else:
                    error = 'Current password is incorrect'
            except Exception as e:
                error = 'Error changing password'
                print(f"Error changing password: {e}")
    
    # Load current user data
    try:
        with open('users.json') as f:
            users = json.load(f)
            user_data = users.get(str(current_user.id), {}).get('account', {})
            profile_data = user_data.get('profile', {})
    except (FileNotFoundError, json.JSONDecodeError):
        user_data = {}
        profile_data = {}

    today_str = date.today().strftime('%Y-%m-%d')
    
    return render_template('dash.html', 
                         username=current_user.username,
                         email=profile_data.get('email', ''),
                         refresh_interval=user_data.get('refresh_interval', 120),
                         profile=profile_data,
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
            'type': 'info',
            'icon': 'fa-info-circle',
            'title': 'No Conditions Selected',
            'message': 'Please select one or more conditions from the Conditions menu to view stock data.'
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

    # Render the template with the settings
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
        #Pushing this old code as working code
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
        print(f"🔍 [DEBUG] Getting conditions for user: {current_user.id} ({current_user.username})")
        # Load conditions for the current user
        conditions = load_user_conditions(current_user.id)
        print(f"🔍 [DEBUG] Found {len(conditions)} conditions for user {current_user.id}")
        if conditions:
            print("🔍 [DEBUG] First condition:", conditions[0])
        else:
            print("ℹ️ [DEBUG] No conditions found for user")
        return jsonify({
            'status': 'success',
            'user_conditions': conditions,
            'count': len(conditions)
        })
    except Exception as e:
        error_msg = f"Error getting user conditions: {str(e)}"
        logger.error(error_msg)
        print(f"❌ [ERROR] {error_msg}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': error_msg
        }), 500
        return jsonify({"error": "Failed to load user conditions"}), 500

@app.route('/api/user-conditions', methods=['POST'])
@login_required
def add_user_condition():
    """Add a new user condition"""
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'scan_clause' not in data:
            return jsonify({"error": "Name and scan_clause are required"}), 400
            
        # Get current user's conditions
        conditions = load_user_conditions(current_user.id)
        
        # Add a default link if not provided
        if 'link' not in data:
            data['link'] = "#"
        
        # Generate a new ID (increment from the highest existing ID)
        max_id = max([int(c['id'].split('_')[-1]) for c in conditions] + [0])
        data['id'] = f"user_condition_{max_id + 1}"
        
        # Add to beginning of list (newest first)
        conditions.insert(0, data)
        
        if save_user_conditions(current_user.id, conditions):
            return jsonify({"message": "Condition added successfully", "id": data['id']}), 201
        else:
            return jsonify({"error": "Failed to save condition"}), 500
            
    except Exception as e:
        logger.error(f"Error adding user condition: {e}")
        return jsonify({"error": "Failed to add user condition"}), 500

@app.route('/api/user-conditions/<condition_id>', methods=['PUT'])
@login_required
def update_user_condition(condition_id):
    """Update an existing user condition"""
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'scan_clause' not in data:
            return jsonify({"error": "Name and scan_clause are required"}), 400
            
        # Get current user's conditions
        conditions = load_user_conditions(current_user.id)
        condition_found = False
        
        for condition in conditions:
            if condition.get('id') == condition_id:
                condition.update({
                    'name': data['name'],
                    'scan_clause': data['scan_clause'],
                    'link': data.get('link', '#')
                })
                condition_found = True
                break
                
        if not condition_found:
            return jsonify({"error": "Condition not found"}), 404
            
        if save_user_conditions(current_user.id, conditions):
            return jsonify({"message": "Condition updated successfully"})
        else:
            return jsonify({"error": "Failed to update condition"}), 500
            
    except Exception as e:
        logger.error(f"Error updating user condition: {e}")
        return jsonify({"error": "Failed to update user condition"}), 500

@app.route('/api/user-conditions/<condition_id>', methods=['DELETE'])
@login_required
def delete_user_condition(condition_id):
    """Delete a user condition"""
    try:
        # Get current user's conditions
        conditions = load_user_conditions(current_user.id)
        initial_count = len(conditions)
        
        # Remove the condition with matching ID
        conditions = [c for c in conditions if c.get('id') != condition_id]
        
        if len(conditions) == initial_count:
            return jsonify({"error": "Condition not found"}), 404
            
        if save_user_conditions(current_user.id, conditions):
            return jsonify({"message": "Condition deleted successfully"})
        else:
            return jsonify({"error": "Failed to delete condition"}), 500
            
    except Exception as e:
        logger.error(f"Error deleting user condition: {e}")
        return jsonify({"error": "Failed to delete user condition"}), 500

if __name__ == '__main__':
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

    # Start threads immediately when run directly
    start_threads_once()
    
    # Run the Flask app in standalone mode if this file is executed directly
    app.run(host='0.0.0.0', port=5000, debug=True)

def cleanup():
    pass