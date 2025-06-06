-- Create weather_data table
create table weather_data (
    id bigint generated by default as identity primary key,
    date date not null,
    location text not null,
    period text not null,
    temperature decimal(4,1) not null,
    humidity decimal(4,1) not null,
    wind_speed decimal(4,1) not null,
    weather_condition text not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Create an index on date for faster queries
create index weather_data_date_idx on weather_data(date);

-- Add RLS (Row Level Security) policies
alter table weather_data enable row level security;

-- Create policy to allow authenticated users to insert data
create policy "Allow authenticated users to insert weather data"
    on weather_data for insert
    to authenticated
    with check (true);

-- Create policy to allow authenticated users to read data
create policy "Allow authenticated users to read weather data"
    on weather_data for select
    to authenticated
    using (true); 