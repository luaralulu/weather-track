#!/usr/bin/env python3

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
from supabase import create_client, Client

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
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

class WeatherTracker:
    def __init__(self):
        # Weather API setup
        self.api_key = WEATHER_API_KEY
        if not self.api_key:
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
            print("Successfully authenticated with Supabase")
            return response.user.id
        except Exception as e:
            print(f"Error signing in to Supabase: {e}")
            raise

    def _get_user_id(self):
        """Get the current user's ID (deprecated, now handled in _sign_in_supabase)."""
        try:
            user = self.supabase.auth.get_user()
            return user.user.id
        except Exception as e:
            print(f"Error getting user ID: {e}")
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
            print(f"Error checking existing data: {e}")
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
            print(f"Error fetching historical weather data: {e}")
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
                print(f"Weather data for {date.strftime('%Y-%m-%d')} already exists. Skipping insertion.")
                return

            print("Starting data insertion...")
            for period, data in period_averages.items():
                print(f"Processing {period} data...")
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
                print(f"Inserting {period} data into Supabase...")
                result = self.supabase.table('weather_data').insert(weather_record).execute()
                
                if hasattr(result, 'error') and result.error:
                    print(f"Error storing {period} data: {result.error}")
                else:
                    print(f"Successfully stored {period} data")
                    
        except Exception as e:
            print(f"Error storing weather data: {e}")
        finally:
            print("Data storage process completed.")

    def print_weather_report(self, date, period_averages):
        """Print a formatted weather report."""
        print(f"\nWeather Report for Newcastle, AU - {date.strftime('%Y-%m-%d')}")
        print("=" * 50)

        for period, data in period_averages.items():
            print(f"\n{period.capitalize()}:")
            print(f"Temperature: {data['avg_temp']:.1f}°C")
            print(f"Feels like: {data['avg_feels_like']:.1f}°C")
            print(f"Humidity: {data['avg_humidity']:.1f}%")
            print(f"Wind Speed: {data['avg_wind_speed']:.1f} km/h")
            print(f"Weather: {data['weather_condition']}")

def main():
    try:
        # Get yesterday's date
        yesterday = datetime.now() - timedelta(days=1)
        
        # Initialize weather tracker
        print("Initializing WeatherTracker...")
        tracker = WeatherTracker()
        
        # Get historical weather data
        print("Fetching historical weather data...")
        weather_data = tracker.get_historical_weather(yesterday)
        if not weather_data:
            print("Failed to fetch weather data")
            return

        # Analyze weather periods
        print("Analyzing weather periods...")
        periods = tracker.analyze_weather_periods(weather_data)
        if not periods:
            print("Failed to analyze weather periods")
            return

        # Calculate averages
        print("Calculating period averages...")
        period_averages = tracker.calculate_period_averages(periods)
        
        # Print report
        tracker.print_weather_report(yesterday, period_averages)
        
        # Store data in Supabase
        print("Storing data in Supabase...")
        tracker.store_weather_data(yesterday, period_averages)
        print("Script execution completed successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        print("Script finished running.")

if __name__ == "__main__":
    main() 