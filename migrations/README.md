# Database Migrations

This directory contains SQL migration files for the Supabase database.

## Migration Files

- `001_create_weather_data_table.sql`: Creates the initial weather_data table with necessary indexes and security policies.
- `002_add_user_id_column.sql`: Adds user_id column and updates security policies to be user-specific.

## How to Apply Migrations

1. Go to your Supabase project dashboard
2. Navigate to the SQL Editor
3. Copy the contents of the migration file
4. Paste into the SQL Editor
5. Click "Run" to execute the migration

## Migration Order

Migrations should be applied in order, as indicated by their numeric prefixes. Always check the migration history in your database before applying new migrations to avoid conflicts.

## Table Structure

The `weather_data` table includes the following columns:

- `id`: Auto-incrementing primary key
- `date`: The date of the weather data
- `location`: The location (e.g., "Newcastle, Australia")
- `period`: The period of the day (morning, afternoon, evening)
- `temperature`: Average temperature in Celsius
- `humidity`: Average humidity percentage
- `wind_speed`: Average wind speed in km/h
- `weather_condition`: The weather condition text
- `user_id`: UUID of the user who created the record (references auth.users)
- `created_at`: Timestamp of when the record was created

## Security

The table has Row Level Security (RLS) enabled with the following policies:

- Users can only insert weather data with their own user_id
- Users can only read their own weather data
- The user_id column is indexed for better query performance

## Indexes

- `weather_data_date_idx`: Index on the date column
- `weather_data_user_id_idx`: Index on the user_id column
