#!/usr/bin/env python3

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
from supabase import create_client, Client
import logging
import re
import pytz

class SensitiveDataFilter(logging.Filter):
    """Filter to remove sensitive information from log records."""
    
    def __init__(self):
        super().__init__()
        # Patterns to match and replace sensitive data
        self.patterns = [
            (r'https?://[^/]+\.supabase\.co', '[SUPABASE_URL]'),
            (r'user_id=eq\.[a-f0-9-]+', 'user_id=eq.[REDACTED]'),
            (r'[a-f0-9-]{36}', '[UUID]'),  # Matches UUIDs
            (r'Bearer [A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*', 'Bearer [REDACTED]'),
            (r'apikey=[A-Za-z0-9-_=]+', 'apikey=[REDACTED]'),
        ]

    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, replacement in self.patterns:
                record.msg = re.sub(pattern, replacement, record.msg)
        return True

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Disable HTTP request logging from urllib3 and requests
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)

# Get our application logger
logger = logging.getLogger(__name__)

# Add the sensitive data filter
sensitive_filter = SensitiveDataFilter()
logger.addFilter(sensitive_filter)

# Load environment variables from .env file if it exists (for local development)
load_dotenv()

# Get environment variables (works for both local .env and GitHub Actions secrets)
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
SUPABASE_USER_EMAIL = os.getenv('SUPABASE_USER_EMAIL')
SUPABASE_USER_PASSWORD = os.getenv('SUPABASE_USER_PASSWORD')

# Validate required environment variables
required_vars = {
    'WEATHER_API_KEY': WEATHER_API_KEY,
    'SUPABASE_URL': SUPABASE_URL,
    'SUPABASE_SERVICE_ROLE_KEY': SUPABASE_SERVICE_ROLE_KEY,
    'SUPABASE_USER_EMAIL': SUPABASE_USER_EMAIL,
    'SUPABASE_USER_PASSWORD': SUPABASE_USER_PASSWORD
}

missing_vars = [var for var, value in required_vars.items() if not value]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

class WeatherTracker:
    def __init__(self):
        # Weather API setup
        self.api_key = WEATHER_API_KEY
        if not self.api_key:
            logger.error("WEATHER_API_KEY not found in environment variables")
            raise ValueError("WEATHER_API_KEY not found in environment variables")
        
        self.base_url = "http://api.weatherapi.com/v1"
        self.city = "Newcastle"
        self.country = "Australia"
        self.lat = -32.9267
        self.lon = 151.7783

        # Supabase setup
        self.supabase_url = SUPABASE_URL
        self.supabase_key = SUPABASE_SERVICE_ROLE_KEY
        self.supabase_email = SUPABASE_USER_EMAIL
        self.supabase_password = SUPABASE_USER_PASSWORD
        
        if not all([self.supabase_url, self.supabase_key, self.supabase_email, self.supabase_password]):
            logger.error("Missing Supabase credentials in environment variables")
            raise ValueError("Missing Supabase credentials in environment variables")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.user_id = self._sign_in_supabase()

    def _sign_in_supabase(self):
        """Sign in to Supabase with email and password and return user ID."""
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": self.supabase_email,
                "password": self.supabase_password
            })
            logger.info("Successfully authenticated with Supabase")
            return response.user.id
        except Exception as e:
            logger.error(f"Error signing in to Supabase: {str(e)}")
            raise

    def _get_user_id(self):
        """Get the current user's ID (deprecated, now handled in _sign_in_supabase)."""
        try:
            user = self.supabase.auth.get_user()
            return user.user.id
        except Exception as e:
            logger.error(f"Error getting user ID: {str(e)}")
            raise

    def check_existing_data(self, date):
        """Check if weather data already exists for the given date and user."""
        try:
            result = self.supabase.table('weather_data')\
                .select('id')\
                .eq('date', date.strftime('%Y-%m-%d'))\
                .eq('user_id', self.user_id)\
                .execute()
            
            return len(result.data) > 0
        except Exception as e:
            logger.error("Error checking existing data")
            return False

    def get_historical_weather(self, date):
        """Get historical weather data for a specific date."""
        url = f"{self.base_url}/history.json"
        
        params = {
            'key': self.api_key,
            'q': f"{self.lat},{self.lon}",
            'dt': date.strftime('%Y-%m-%d'),
            'hour': '0-23'  # Get all hours
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching historical weather data: {str(e)}")
            return None

    def analyze_weather_periods(self, weather_data):
        """Analyze weather data and divide it into morning, afternoon, and evening periods."""
        if not weather_data or 'forecast' not in weather_data or 'forecastday' not in weather_data['forecast']:
            return None

        # Get the first (and only) forecast day
        day_data = weather_data['forecast']['forecastday'][0]
        
        periods = {
            'morning': {'hours': range(6, 12), 'data': []},
            'afternoon': {'hours': range(12, 18), 'data': []},
            'evening': {'hours': range(18, 24), 'data': []}
        }

        for hour_data in day_data['hour']:
            hour = int(hour_data['time'].split()[1].split(':')[0])
            for period, info in periods.items():
                if hour in info['hours']:
                    info['data'].append(hour_data)

        return periods

    def calculate_period_averages(self, periods):
        """Calculate average weather conditions for each period."""
        results = {}
        
        for period, data in periods.items():
            if not data['data']:
                continue

            temps = [hour['temp_c'] for hour in data['data']]
            feels_like = [hour['feelslike_c'] for hour in data['data']]
            humidity = [hour['humidity'] for hour in data['data']]
            wind_speed = [hour['wind_kph'] for hour in data['data']]
            
            # Get most common weather condition
            weather_conditions = [hour['condition']['text'] for hour in data['data']]
            most_common_weather = max(set(weather_conditions), key=weather_conditions.count)

            results[period] = {
                'avg_temp': sum(temps) / len(temps),
                'avg_feels_like': sum(feels_like) / len(feels_like),
                'avg_humidity': sum(humidity) / len(humidity),
                'avg_wind_speed': sum(wind_speed) / len(wind_speed),
                'weather_condition': most_common_weather
            }

        return results

    def store_weather_data(self, date, period_averages):
        """Store weather data in Supabase."""
        try:
            # Check if data already exists for this date and user
            if self.check_existing_data(date):
                logger.info(f"Weather data for {date.strftime('%Y-%m-%d')} already exists. Skipping insertion.")
                return

            logger.info("Starting data insertion...")
            for period, data in period_averages.items():
                logger.info(f"Processing {period} data...")
                weather_record = {
                    'date': date.strftime('%Y-%m-%d'),
                    'location': f"{self.city}, {self.country}",
                    'period': period,
                    'temperature': round(data['avg_temp'], 1),
                    'humidity': round(data['avg_humidity'], 1),
                    'wind_speed': round(data['avg_wind_speed'], 1),
                    'weather_condition': data['weather_condition'],
                    'user_id': self.user_id
                }
                
                # Insert data into Supabase
                logger.info(f"Inserting {period} data into Supabase...")
                result = self.supabase.table('weather_data').insert(weather_record).execute()
                
                if hasattr(result, 'error') and result.error:
                    logger.error("Error storing data")
                else:
                    logger.info(f"Successfully stored {period} data")
                    
        except Exception as e:
            logger.error("Error storing weather data")
        finally:
            logger.info("Data storage process completed.")

    def print_weather_report(self, date, period_averages):
        """Print a formatted weather report."""
        logger.info(f"\nWeather Report for Newcastle, AU - {date.strftime('%Y-%m-%d')}")
        logger.info("=" * 50)

        for period, data in period_averages.items():
            logger.info(f"\n{period.capitalize()}:")
            logger.info(f"Temperature: {data['avg_temp']:.1f}°C")
            logger.info(f"Feels like: {data['avg_feels_like']:.1f}°C")
            logger.info(f"Humidity: {data['avg_humidity']:.1f}%")
            logger.info(f"Wind Speed: {data['avg_wind_speed']:.1f} km/h")
            logger.info(f"Weather: {data['weather_condition']}")

    def cleanup(self):
        """Clean up resources and close connections."""
        try:
            if hasattr(self, 'supabase'):
                # Sign out from Supabase
                self.supabase.auth.sign_out()
                logger.info("Successfully signed out from Supabase")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def get_last_stored_date(self):
        """Get the most recent date for which weather data exists in the database."""
        try:
            result = self.supabase.table('weather_data')\
                .select('date')\
                .eq('user_id', self.user_id)\
                .order('date', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return datetime.strptime(result.data[0]['date'], '%Y-%m-%d').replace(tzinfo=pytz.timezone('Australia/Sydney'))
            return None
        except Exception as e:
            logger.error(f"Error getting last stored date: {str(e)}")
            return None

    def process_date(self, date):
        """Process weather data for a specific date."""
        try:
            # Check if data already exists
            if self.check_existing_data(date):
                logger.info(f"Weather data for {date.strftime('%Y-%m-%d')} already exists. Skipping.")
                return True

            # Get historical weather data
            logger.info(f"Fetching historical weather data for {date.strftime('%Y-%m-%d')}...")
            weather_data = self.get_historical_weather(date)
            if not weather_data:
                logger.error(f"Failed to fetch weather data for {date.strftime('%Y-%m-%d')}")
                return False

            # Analyze weather periods
            logger.info("Analyzing weather periods...")
            periods = self.analyze_weather_periods(weather_data)
            if not periods:
                logger.error("Failed to analyze weather periods")
                return False

            # Calculate averages
            logger.info("Calculating period averages...")
            period_averages = self.calculate_period_averages(periods)
            
            # Print report
            self.print_weather_report(date, period_averages)
            
            # Store data in Supabase
            logger.info("Storing data in Supabase...")
            self.store_weather_data(date, period_averages)
            return True

        except Exception as e:
            logger.error(f"Error processing date {date.strftime('%Y-%m-%d')}: {str(e)}")
            return False

def main():
    tracker = None
    try:
        # Set AEST timezone
        aest = pytz.timezone('Australia/Sydney')
        
        # Get current time in AEST
        current_time_aest = datetime.now(aest)
        
        # Get yesterday's date in AEST
        yesterday = current_time_aest - timedelta(days=1)
        
        # Initialize weather tracker
        logger.info("Initializing WeatherTracker...")
        tracker = WeatherTracker()
        
        # Get the last stored date
        last_stored_date = tracker.get_last_stored_date()
        
        if last_stored_date is None:
            # If no data exists, start from yesterday
            start_date = yesterday
        else:
            # Start from the day after the last stored date
            start_date = last_stored_date + timedelta(days=1)
        
        # Process all missing dates up to yesterday
        current_date = start_date
        while current_date <= yesterday:
            logger.info(f"\nProcessing date: {current_date.strftime('%Y-%m-%d')}")
            success = tracker.process_date(current_date)
            
            if not success:
                logger.error(f"Failed to process date {current_date.strftime('%Y-%m-%d')}")
                # Continue with next date even if current one fails
                
            current_date += timedelta(days=1)
        
        logger.info("Script execution completed successfully.")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        if tracker:
            logger.info("Cleaning up resources...")
            tracker.cleanup()
        logger.info("Script finished running.")

if __name__ == "__main__":
    main() 