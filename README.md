# Weather Tracker

This project retrieves weather data for Newcastle, Australia, using the [WeatherAPI.com](https://www.weatherapi.com/) API. It calculates average weather conditions for the previous day, divided into morning, afternoon, and evening, and stores the data in a Supabase database.

## Features

- Fetches historical weather data from WeatherAPI.com.
- Calculates average temperature, humidity, wind speed, and weather conditions for different periods of the day.
- Stores the data in a Supabase database, preventing duplicate entries.

## Setup

1. Clone the repository.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```
   WEATHER_API_KEY=your_weather_api_key
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
   SUPABASE_USER_EMAIL=your_supabase_user_email
   SUPABASE_USER_PASSWORD=your_supabase_user_password
   ```
4. Run the script:
   ```bash
   python weather_tracker.py
   ```

## Dependencies

- Python 3.9+
- `requests`
- `python-dotenv`
- `supabase`

## License

This project is licensed under the MIT License.
