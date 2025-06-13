import pandas as pd
import requests
from bs4 import BeautifulSoup as bs
import time
import winsound
from datetime import datetime
import sys
import signal

# Define the scan conditions
conditions = [
    {
        "name": "DeepSeek",
        "scan_clause": """( {57960} ( 
            latest close > latest ema( latest close , 9 ) and 
            latest close > latest ema( latest close , 21 ) and 
            latest ema( latest close , 9 ) > latest ema( latest close , 21 ) and 
            latest close > greatest( 1 day ago high, 5 ) and 
            latest volume >= ( latest sma( latest volume , 20 ) * 1.5 ) and 
            latest rsi( 14 ) < 70 
        ) )"""
    },
    {
        "name": "KHAIZER",
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
        "name": "STRONG",
        "scan_clause": """( {57960} ( 
            latest close > 20 and 
            latest close < 2000 
        ) )"""
    }
]

# Global flag for graceful shutdown
running = True

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\nShutting down gracefully...")
    running = False

def play_alert():
    """Play alert sound with error handling"""
    try:
        for _ in range(3):
            winsound.Beep(500, 500)
            time.sleep(0.1)
    except Exception as e:
        print(f"Could not play alert sound: {e}")

def fetch_and_process_data(session):
    """Fetch and process stock data using the provided session"""
    url = "https://chartink.com/screener/process"
    all_scans = []

    try:
        # Get CSRF token
        r_data = session.get(url)
        r_data.raise_for_status()
        soup = bs(r_data.content, "lxml")
        meta = soup.find("meta", {"name": "csrf-token"})
        if not meta:
            print("Error: Could not find CSRF token")
            return
        
        header = {"x-csrf-token": meta["content"]}

        for cond in conditions:
            if not running:  # Check if we should continue
                return

            try:
                response = session.post(url, headers=header, data={"scan_clause": cond["scan_clause"]})
                response.raise_for_status()
                
                data = response.json()
                stock_list = pd.DataFrame(data["data"])

                if not stock_list.empty:
                    stock_list["per_chg"] = pd.to_numeric(stock_list["per_chg"])
                    stock_list["potential_score"] = stock_list["per_chg"] * stock_list["close"]
                    
                    # For "STRONG" condition, only show top 10 based on potential_score
                    if cond["name"] == "STRONG":
                        sorted_stock_list = stock_list.sort_values(by="potential_score", ascending=False).head(10)
                    else:
                        sorted_stock_list = stock_list.sort_values(by="potential_score", ascending=False)
                    
                    top_stocks = sorted_stock_list.head(10)
                    all_scans.append((cond["name"], top_stocks))
                else:
                    all_scans.append((cond["name"], pd.DataFrame()))

            except requests.RequestException as e:
                print(f"Network error for {cond['name']}: {e}")
                all_scans.append((cond["name"], pd.DataFrame()))
            except Exception as e:
                print(f"Error processing {cond['name']}: {e}")
                all_scans.append((cond["name"], pd.DataFrame()))

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n--- Fetched at: {current_time} ---")

        stocks_found = False
        for scan_name, top_stocks in all_scans:
            print(f"\n--- {scan_name} Top Stocks ---")
            if not top_stocks.empty:
                print(top_stocks[["nsecode", "close", "per_chg", "volume", "potential_score"]])  # Show only relevant columns
                stocks_found = True
            else:
                print(f"No stocks found for {scan_name}.")

        if stocks_found:
            play_alert()

    except Exception as e:
        print(f"Error in main processing: {e}")

def main():
    """Main function to run the stock scanner"""
    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Starting stock scanner... Press Ctrl+C to exit.")
    
    # Create a session for better performance
    with requests.Session() as session:
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        
        while running:
            try:
                print("\nFetching data...")
                fetch_and_process_data(session)
                
                if running:  # Only sleep if we're still meant to be running
                    time.sleep(120)  # Wait 2 minutes before the next cycle
            except Exception as e:
                print(f"Error in main loop: {e}")
                if running:
                    time.sleep(30)  # Wait 30 seconds before retrying on error

if __name__ == "__main__":
    main()
