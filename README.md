# Weather Tracker for Newcastle, AU

This script fetches and displays historical weather data for Newcastle, Australia, divided into morning, afternoon, and evening periods.

## Features

- Fetches historical weather data for the previous day
- Divides weather information into three periods (morning, afternoon, evening)
- Shows temperature, feels-like temperature, humidity, wind speed, and weather conditions
- Uses OpenWeatherMap API for reliable weather data
- Implements proper error handling and security best practices

## Setup

1. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Sign up for a free API key at [OpenWeatherMap](https://openweathermap.org/api)

3. Create a `.env` file in the project root with your API key:
   ```
   OPENWEATHER_API_KEY=your_api_key_here
   ```

## Usage

Run the script:

```bash
python weather_tracker.py
```

The script will display a weather report for the previous day, showing:

- Average temperature
- "Feels like" temperature
- Humidity percentage
- Wind speed
- Weather conditions

## Note

The free tier of OpenWeatherMap API has a limit of 60 calls per minute. The script makes one API call per run.
