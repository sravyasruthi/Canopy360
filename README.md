# Canopy360 - Smart Tree Care & Sustainability Platform

A web application for registering and caring for trees. Users can record trees with
photos and GPS locations, see them on a map, get weather-based watering advice,
estimate carbon absorption, schedule fertilizer, and download PDF and Excel reports.

Built as a college mini project with Python, Flask and MySQL.

## Features

- Public home page and secure login (passwords are hashed, forms are CSRF-protected)
- Each user sees only the trees they registered (admins see all trees)
- Tree management: add, view, edit, delete, search, filter, sort, photo upload
- Interactive map of tree locations (Folium / OpenStreetMap)
- Live weather (OpenWeather API) with demo data when the key is missing or fails
- Rule-based watering advice using temperature, humidity, rainfall, species and age
- Carbon calculator with a simplified formula; size can be estimated if unknown
- Fertilizer scheduler with automatic status (Upcoming, Due Today, Overdue, Completed)
- Reports page with charts, PDF report (ReportLab) and Excel export (openpyxl)
- Admin-only user management and a settings page with API and database status

## Technologies

Python, Flask, Flask-SQLAlchemy, Flask-WTF, MySQL (PyMySQL), HTML, CSS, JavaScript,
OpenWeather API, Folium, Matplotlib, ReportLab, pandas, openpyxl, Pillow.

## Project structure

```
Canopy360/
├── app.py               # starts the app, creates tables and the default admin
├── config.py            # settings read from .env
├── extensions.py        # database and CSRF objects
├── models.py            # database tables
├── requirements.txt
├── .env                 # your private settings (never share this file)
├── routes/              # one file per area: auth, home, dashboard, trees,
│                        #   weather, carbon, fertilizer, reports, users, settings
├── services/            # logic: weather, watering, carbon, charts, map, pdf, excel
├── templates/           # HTML pages
├── static/              # css, js, images, uploads (tree photos)
└── reports/             # generated PDF and Excel files
```

## Setup

1. Install Python 3.10 or newer and MySQL.
2. Create the database in MySQL:
   ```sql
   CREATE DATABASE canopy360;
   ```
3. In the project folder, create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate          (Windows)
   source venv/bin/activate       (Mac/Linux)
   ```
4. Install the packages:
   ```
   pip install -r requirements.txt
   ```
5. Create a file named `.env` in the project folder:
   ```
   SECRET_KEY=put_a_long_random_string_here
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=canopy360
   DB_USER=root
   DB_PASSWORD=your_mysql_password
   OPENWEATHER_API_KEY=your_openweather_api_key
   ```
   The OpenWeather key is optional. Without it the app shows demo weather.
6. Run the app:
   ```
   python app.py
   ```
7. Open http://127.0.0.1:5000

The tables and the default admin account are created automatically on the first run.

## Default login

| Email | Password |
|---|---|
| admin@canopy360.com | admin123 |

Change this password in **Settings** after the first login.
New users can register from the Register page. The admin can also add or manage users under Users.

## How it works (short notes)

- **Ownership:** every tree stores the id of the user who added it. Pages only load
  trees that belong to the logged-in user, and admins can see all trees.
- **Watering advice:** simple rules add or subtract waterings per week from a base of 3.
  No machine learning is used.
- **Carbon estimate:** biomass = 0.0509 x 0.6 x diameter^2 x height, carbon = biomass x 0.5,
  CO2 = carbon x 3.67, yearly value = CO2 / age. This is a simplified estimate for
  learning, not an exact scientific measurement. If diameter or height are unknown they
  are estimated from age and species, which makes the result less accurate.
- **Weather:** results are cached for 10 minutes. If the API key is missing or the service
  fails, demo data is shown with a clear message.

## Troubleshooting

| Problem | What to check |
|---|---|
| Access denied for user | `DB_PASSWORD` in `.env` is wrong |
| Unknown database | Run `CREATE DATABASE canopy360;` |
| Can't connect to MySQL | MySQL is not running |
| ModuleNotFoundError | Activate the virtual environment and run `pip install -r requirements.txt` |
| Weather shows demo data | Add `OPENWEATHER_API_KEY` to `.env` and restart (new keys can take a few hours) |
| Page has no styling | Hard refresh with Ctrl+F5 |

## Possible future improvements

- Public sign-up and password reset by email
- Maintenance task calendar
- Tree health tracking over time with photos
- Deployment on a hosting service with a production server and debug mode turned off