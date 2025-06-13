from flask import Flask, render_template, jsonify, make_response, send_from_directory
import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
import time
from datetime import datetime
import threading
import queue
import logging
import os
import pygame

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_url_path='/static', static_folder='static')

# Define the scan conditions
conditions = [
    {
        "name": "DeepSeek",
        "link": "https://www.example.com/deep-seek-news",
        "scan_clause": """( {57960} ( 
            latest close > latest ema( latest close , 9 ) and 
            latest close > latest ema( latest close , 21 ) and 
            latest ema( latest close , 9 ) > latest ema( latest close , 21 ) and 
            latest close > greatest( 1 day ago high, 5 ) and 
            latest volume >= ( latest sma( latest volume , 20 ) * 1.5 ) and 
            latest rsi( 14 ) < 70 and
            latest close >= 10 and 
            latest close <= 2000  
        ) )"""
    },
    {
        "name": "KHAIZER",
        "link": "https://www.example.com/khaizer-news",
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
            latest close <= 2000 
        ) )"""
    },
    {
        "name": "CROSSED",
        "link": "https://www.example.com/crossed-news",
        "scan_clause": """( {57960} ( 
            latest open > latest ema( latest close , 21 ) and 
            1 day ago open <= 1 day ago ema( latest close , 21 ) and 
            latest close > latest open * 1.025 and 
            latest close >= 10 and 
            latest close <= 2000 and 
            latest close >= 1 day ago high 
        ) )"""
    },
    {
        "name": "15 MIN Breakout",
        "link": "https://www.example.com/15-min-breakout-news",
        "scan_clause": """( {57960} ( 
            [0] 15 minute close > [-1] 15 minute max( 20 , [0] 15 minute close ) and 
            [0] 15 minute volume > [0] 15 minute sma( volume , 20 ) and 
            latest close > 1 day ago high and 
            latest close > latest ema( latest close , 21 ) and 
            latest close > latest open * 1.025 and 
            latest close > latest supertrend( 10 , 1.5 ) and 
            latest close <= 2000 
        ) )"""
    },
    {
        "name": "STRONG STOCKS",
        "link": "https://www.example.com/strong-stocks-news",
        "scan_clause": """( {57960} ( 
            latest close > 20 and 
            latest close <= 2000 
        ) )""",
    },
    {
        "name": "ATR STOCKS",
        "link": "https://www.example.com/atr-stocks-news",
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
        "link": "https://www.example.com/multi-timeframe-scan-news",
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

            latest close >= 20 and latest close <= 2500
        ) )"""
    },
    {
        "name": "HARSH SELL STOCKS",
        "link": "https://www.example.com/harsh-sell-stocks-news",
        "scan_clause": """( ( {57960} ( [=1] 10 minute open > [=1] 10 minute close and( {57960} ( [=1] 10 minute "close - 1 candle ago close / 1 candle ago close * 100" < -2 ) ) and( {166311} not( latest close > 0 ) ) and( {136699} not( latest close > 0 ) ) and( {136699} not( latest close > 0 ) ) and( {167068} not( latest close > 0 ) ) and latest close > 20 and latest close <= 2000 ) ) )"""
    },
    {
        "name": "HARSH BUY STOCKS",
        "link": "https://www.example.com/harsh-buy-stocks-news",
        "scan_clause": """( {57960} ( [=1] 10 minute open < [=1] 10 minute close and ( {57960} ( [=1] 10 minute "close - 1 candle ago close / 1 candle ago close * 100" < 2 ) ) and ( {166311} not ( latest close > 0 ) ) and ( {136699} not ( latest close > 0 ) ) and ( {136699} not ( latest close > 0 ) ) and ( {167068} not ( latest close > 0 ) ) and latest close > 20 and latest close <= 2000 ) )"""
    },
    
]

# Global variables
data_queue = queue.Queue()
last_update_time = None
update_thread = None
running = True
thread_started = False
scan_results = {}

def fetch_and_process_data(session):
    """Fetch and process stock data using the provided session"""
    url = "https://chartink.com/screener/process"
    all_scans = {}

    try:
        # Get CSRF token
        logger.info("Fetching CSRF token...")
        r_data = session.get(url)
        r_data.raise_for_status()
        soup = bs(r_data.content, "lxml")
        meta = soup.find("meta", {"name": "csrf-token"})
        if not meta:
            logger.error("Could not find CSRF token")
            return {"error": "Could not find CSRF token"}
        
        header = {"x-csrf-token": meta["content"]}
        logger.info("CSRF token obtained successfully")

        stocks_found = False
        for cond in conditions:
            if not running:
                return

            try:
                logger.info(f"Processing scan: {cond['name']}")
                response = session.post(url, headers=header, data={"scan_clause": cond["scan_clause"]})
                response.raise_for_status()
                
                data = response.json()
                stock_list = pd.DataFrame(data["data"])

                if not stock_list.empty:
                    stocks_found = True
                    stock_list["per_chg"] = pd.to_numeric(stock_list["per_chg"])
                    stock_list["potential_score"] = stock_list["per_chg"] * stock_list["close"]
                    
                    if cond["name"] == "STRONG":
                        sorted_stock_list = stock_list.sort_values(by="potential_score", ascending=False).head(10)
                        
                    elif cond["name"] == "HARSH SELL STOCKS":
                        sorted_stock_list = stock_list.sort_values(by="potential_score", ascending=True)  # Sort by potential_score ascending
                    
                    else:
                        sorted_stock_list = stock_list.sort_values(by="potential_score", ascending=False)
                    
                    # Convert DataFrame to dict for JSON serialization
                    all_scans[cond["name"]] = sorted_stock_list.head(10).to_dict('records')
                    logger.info(f"Found {len(all_scans[cond['name']])} stocks for {cond['name']}")
                else:
                    logger.info(f"No stocks found for {cond['name']}")
                    all_scans[cond["name"]] = []

            except Exception as e:
                logger.error(f"Error processing {cond['name']}: {str(e)}")
                all_scans[cond["name"]] = {"error": str(e)}

        if stocks_found:
            play_beep()
            logger.info("Found stocks - played beep")

        return all_scans

    except Exception as e:
        logger.error(f"Error in fetch_and_process_data: {str(e)}")
        return {"error": str(e)}

def fetch_data():
    """Fetch data from all scan conditions"""
    global scan_results, last_update_time
    
    try:
        with requests.Session() as session:
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            })
            all_results = fetch_and_process_data(session)
            scan_results = all_results
            last_update_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return True
    except Exception as e:
        logger.error(f"Error in fetch_data: {str(e)}")
        return False

def update_data():
    """Background thread function to update data periodically"""
    global running
    while running:
        fetch_data()
        time.sleep(120)

pygame.mixer.init()

def play_beep():
    """Play alert sound from alert.mp3"""
    try:
        logger.info("Playing alert sound...")
        pygame.mixer.music.load('sounds/alert.mp3')
        pygame.mixer.music.play(loops=0)  # Play once
        while pygame.mixer.music.get_busy():  # Wait for music to finish playing
            time.sleep(5)
        logger.info("Alert sound played")
    except Exception as e:
        logger.error(f"Error playing alert sound: {e}")

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/')
def index():
    fetch_data()  # Ensure data is fetched before rendering
    # Add stock data inside each condition
    conditions_with_stocks = [
        {**condition, "stocks": scan_results.get(condition["name"], [])}
        for condition in conditions
    ]
    return render_template('index.html', conditions=conditions_with_stocks)

@app.route('/api/scan_results')
def get_scan_results():
    """API endpoint to get scan results"""
    # Force a fresh data fetch on each request
    fetch_data()
    
    # Create response with no-cache headers
    response = make_response(jsonify({
        'results': scan_results,
        'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }))
    
    # Set headers to prevent caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@app.route('/static/hyperlink.svg')
def serve_svg():
    return send_from_directory('static', 'hyperlink.svg')

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

@app.before_request
def before_request():
    """Start background thread before the first request if not already started"""
    global thread_started
    if not thread_started:
        start_background_thread()

if __name__ == '__main__':
    print("\a" * 2)  # Initial beep when starting
    app.run(debug=True)  # Disabled debug mode to avoid double threading