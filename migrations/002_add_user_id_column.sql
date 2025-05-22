-- Add user_id column
alter table weather_data
add column user_id uuid references auth.users(id);

-- Update RLS policies to include user_id
drop policy if exists "Allow authenticated users to insert weather data" on weather_data;
drop policy if exists "Allow authenticated users to read weather data" on weather_data;

-- Create policy to allow users to insert their own data
create policy "Allow users to insert their own weather data"
    on weather_data for insert
    to authenticated
    with check (auth.uid() = user_id);

-- Create policy to allow users to read their own data
create policy "Allow users to read their own weather data"
    on weather_data for select
    to authenticated
    using (auth.uid() = user_id);

-- Create index on user_id for faster queries
create index weather_data_user_id_idx on weather_data(user_id); 