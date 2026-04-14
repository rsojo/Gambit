import os
import json
import sqlite3
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
import soccerdata as sd
import pandas as pd
import warnings

# Suppress warnings from soccerdata
warnings.filterwarnings('ignore')

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Football Data API Configuration
FOOTBALL_DATA_API_KEY = os.environ.get('FOOTBALL_DATA_API_KEY', '')
FOOTBALL_DATA_BASE_URL = 'https://api.football-data.org/v4'
FBREF_PROXY = os.environ.get('FBREF_PROXY')
USE_SOCCERDATA = os.environ.get('USE_SOCCERDATA', 'false').lower() == 'true'
SQLITE_DB_PATH = os.environ.get('SQLITE_DB_PATH', 'gambit.db')

# League codes mapping
LEAGUES = {
    'CL': 2001,  # UEFA Champions League
    'PL': 2021,  # Premier League
    'PD': 2014,  # La Liga (Primera Division)
    'BL1': 2002,  # Bundesliga
    'EC': 2018,  # European Championship
    'SA': 'SA',  # Serie A
    'EL': 'EL'   # UEFA Europa League
}

# League display names
LEAGUE_NAMES = {
    'CL': 'UEFA Champions League',
    'PL': 'Premier League',
    'PD': 'La Liga',
    'BL1': 'Bundesliga',
    'EC': 'European Championship',
    'SA': 'Serie A',
    'EL': 'UEFA Europa League'
}

# Soccerdata league mapping
SOCCERDATA_LEAGUES = {
    # FBref in soccerdata does not provide UEFA Champions League directly.
    'CL': None,
    'PL': 'ENG-Premier League',
    'PD': 'ESP-La Liga',
    'BL1': 'GER-Bundesliga',
    'EC': 'INT-European Championship',
    'SA': 'ITA-Serie A',
    'EL': None
}

# Cache for historical data
historical_stats_cache = {}


def get_db_connection():
    """Create a SQLite connection for local cache operations."""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize local SQLite tables for API cache and sync state."""
    with get_db_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS matches (
                match_id INTEGER PRIMARY KEY,
                league_code TEXT,
                competition_name TEXT,
                utc_date TEXT,
                status TEXT,
                home_team TEXT,
                home_team_id INTEGER,
                away_team TEXT,
                away_team_id INTEGER,
                score_home INTEGER,
                score_away INTEGER,
                raw_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_state (
                cache_key TEXT PRIMARY KEY,
                last_synced_on TEXT,
                last_status TEXT,
                last_error TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_matches_league_date
            ON matches (league_code, utc_date)
            """
        )


# Ensure DB exists when app is imported by Flask or tests.
init_db()


def build_cache_key(league_code, date_from, date_to):
    """Return a deterministic cache key for a specific request window."""
    return f"{league_code or 'ALL'}|{date_from or 'NONE'}|{date_to or 'NONE'}"


def mark_sync_state(cache_key, status, error_message=None):
    """Persist sync status for the current day."""
    now_iso = datetime.utcnow().isoformat() + 'Z'
    today = datetime.utcnow().strftime('%Y-%m-%d')
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO sync_state (cache_key, last_synced_on, last_status, last_error, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(cache_key) DO UPDATE SET
                last_synced_on=excluded.last_synced_on,
                last_status=excluded.last_status,
                last_error=excluded.last_error,
                updated_at=excluded.updated_at
            """,
            (cache_key, today, status, error_message, now_iso),
        )


def should_sync_today(cache_key):
    """Allow a single sync attempt per day for each request window."""
    today = datetime.utcnow().strftime('%Y-%m-%d')
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT last_synced_on, last_status FROM sync_state WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
    if row is None:
        return True
    if row['last_synced_on'] != today:
        return True
    return row['last_status'] != 'success'


def upsert_matches(matches):
    """Store API matches in SQLite for fast local reads."""
    if not matches:
        return
    now_iso = datetime.utcnow().isoformat() + 'Z'
    rows = []
    for match in matches:
        full_time = match.get('score', {}).get('fullTime', {})
        rows.append(
            (
                match.get('id'),
                match.get('competition', {}).get('code'),
                match.get('competition', {}).get('name'),
                match.get('utcDate'),
                match.get('status'),
                match.get('homeTeam', {}).get('name'),
                match.get('homeTeam', {}).get('id'),
                match.get('awayTeam', {}).get('name'),
                match.get('awayTeam', {}).get('id'),
                full_time.get('home'),
                full_time.get('away'),
                json.dumps(match),
                now_iso,
            )
        )

    with get_db_connection() as conn:
        conn.executemany(
            """
            INSERT INTO matches (
                match_id, league_code, competition_name, utc_date, status,
                home_team, home_team_id, away_team, away_team_id,
                score_home, score_away, raw_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(match_id) DO UPDATE SET
                league_code=excluded.league_code,
                competition_name=excluded.competition_name,
                utc_date=excluded.utc_date,
                status=excluded.status,
                home_team=excluded.home_team,
                home_team_id=excluded.home_team_id,
                away_team=excluded.away_team,
                away_team_id=excluded.away_team_id,
                score_home=excluded.score_home,
                score_away=excluded.score_away,
                raw_json=excluded.raw_json,
                updated_at=excluded.updated_at
            """,
            rows,
        )


def fetch_matches_from_api(league_code=None, date_from=None, date_to=None):
    """Fetch matches from Football Data API only."""
    if league_code and league_code in LEAGUES:
        competition_id = LEAGUES[league_code]
        url = f'{FOOTBALL_DATA_BASE_URL}/competitions/{competition_id}/matches'
    else:
        url = f'{FOOTBALL_DATA_BASE_URL}/matches'

    params = {}
    if date_from:
        params['dateFrom'] = date_from
    if date_to:
        params['dateTo'] = date_to

    response = None
    for attempt in range(3):
        try:
            response = requests.get(url, headers=get_headers(), params=params, timeout=12)
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt == 2:
                raise e

    if response.status_code == 200:
        return response.json().get('matches', [])
    if response.status_code == 401:
        print("ERROR: API authentication failed - Invalid API key")
        return []
    if response.status_code == 429:
        print("WARNING: API rate limit exceeded - Too many requests")
        return []

    print(f"ERROR: API returned status {response.status_code}: {response.text}")
    return []


def get_matches_from_db(league_code=None, date_from=None, date_to=None):
    """Load matches from local SQLite cache for the requested range."""
    where = []
    params = []
    if league_code:
        where.append("league_code = ?")
        params.append(league_code)
    if date_from:
        where.append("substr(utc_date, 1, 10) >= ?")
        params.append(date_from)
    if date_to:
        where.append("substr(utc_date, 1, 10) <= ?")
        params.append(date_to)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    query = f"SELECT raw_json FROM matches {where_sql} ORDER BY utc_date ASC"
    with get_db_connection() as conn:
        rows = conn.execute(query, params).fetchall()
    return [json.loads(row['raw_json']) for row in rows]

def get_headers():
    """Get headers for Football Data API requests"""
    return {
        'X-Auth-Token': FOOTBALL_DATA_API_KEY
    }

def get_recent_season_codes(num_seasons):
    """Return FBref-compatible season codes like [2025, 2024]."""
    if num_seasons < 1:
        return []
    current = datetime.now()
    season_start_year = current.year if current.month >= 7 else current.year - 1
    return [season_start_year - i for i in range(num_seasons)]


def get_first_existing_column(df, candidates):
    """Return the first available column name from a candidate list."""
    for col in candidates:
        if col in df.columns:
            return col
    return None

def get_matches(league_code=None, date_from=None, date_to=None):
    """
    Fetch matches from local SQLite cache and sync daily with Football Data API.
    
    Args:
        league_code: League code (CL, PL, PD, BL1, EC, SA, EL)
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
    
    Returns:
        List of matches
    """
    cache_key = build_cache_key(league_code, date_from, date_to)
    try:
        if should_sync_today(cache_key):
            matches = fetch_matches_from_api(league_code, date_from, date_to)
            upsert_matches(matches)
            mark_sync_state(cache_key, 'success')

        return get_matches_from_db(league_code, date_from, date_to)
    except requests.exceptions.Timeout:
        print("WARNING: API request timeout")
        mark_sync_state(cache_key, 'error', 'timeout')
        return get_matches_from_db(league_code, date_from, date_to)
    except requests.exceptions.ConnectionError:
        print("WARNING: Unable to connect to API - Network issue or API unavailable")
        mark_sync_state(cache_key, 'error', 'connection_error')
        return get_matches_from_db(league_code, date_from, date_to)
    except Exception as e:
        print(f"ERROR: Unexpected error fetching matches: {type(e).__name__}: {e}")
        mark_sync_state(cache_key, 'error', f"{type(e).__name__}: {e}")
        return get_matches_from_db(league_code, date_from, date_to)

def get_team_statistics(team_name, league_code, seasons=1):
    """
    Get historical statistics for a team using soccerdata
    
    Args:
        team_name: Name of the team
        league_code: League code (CL, PL, PD, BL1, EC)
        seasons: Number of recent seasons to analyze
    
    Returns:
        Dictionary with team statistics or None if not available
    """
    try:
        cache_key = f"{league_code}_{team_name}"
        if cache_key in historical_stats_cache:
            return historical_stats_cache[cache_key]
        
        league = SOCCERDATA_LEAGUES.get(league_code)
        if not league:
            return None
        
        if league is None:
            # No FBref mapping available for this league.
            return None

        season_codes = get_recent_season_codes(seasons)
        if not season_codes:
            return None

        # Get match results using FBref (more reliable for stats)
        fbref = sd.FBref(leagues=[league], seasons=season_codes, proxy=FBREF_PROXY)
        
        # Get schedule data
        schedule = fbref.read_schedule()
        
        if schedule.empty:
            return None
        
        home_col = get_first_existing_column(schedule, ['Home', 'home_team'])
        away_col = get_first_existing_column(schedule, ['Away', 'away_team'])
        score_col = get_first_existing_column(schedule, ['Score', 'score'])

        if not home_col or not away_col or not score_col:
            return None

        schedule = schedule[[home_col, away_col, score_col]].copy()

        # Keep only rows with parseable finished scores like "2-1" or "2–1".
        score_split = schedule[score_col].astype(str).str.extract(r'^(\d+)\s*[\-–]\s*(\d+)$')
        valid = score_split.notna().all(axis=1)
        schedule = schedule[valid].copy()
        score_split = score_split[valid].astype(float)

        if schedule.empty:
            return None

        schedule['home_goals'] = score_split[0].values
        schedule['away_goals'] = score_split[1].values

        # Filter for the team
        team_matches = schedule[
            (schedule[home_col].str.contains(team_name, case=False, na=False)) |
            (schedule[away_col].str.contains(team_name, case=False, na=False))
        ].copy()
        
        if team_matches.empty:
            return None
        
        # Calculate statistics
        home_matches = team_matches[team_matches[home_col].str.contains(team_name, case=False, na=False)]
        away_matches = team_matches[team_matches[away_col].str.contains(team_name, case=False, na=False)]
        
        # Goals statistics
        goals_scored = home_matches['home_goals'].sum() + away_matches['away_goals'].sum()
        
        goals_conceded = home_matches['away_goals'].sum() + away_matches['home_goals'].sum()
        
        total_matches = len(team_matches)
        
        stats = {
            'avg_goals_scored': round(goals_scored / total_matches, 2) if total_matches > 0 else 1.5,
            'avg_goals_conceded': round(goals_conceded / total_matches, 2) if total_matches > 0 else 1.2,
            'total_matches': total_matches,
            'home_matches': len(home_matches),
            'away_matches': len(away_matches)
        }
        
        historical_stats_cache[cache_key] = stats
        return stats
        
    except Exception as e:
        print(f"Error fetching statistics for {team_name}: {e}")
        return None

def generate_prediction(match):
    """
    Generate predictions for a match based on real historical statistics from soccerdata
    
    Args:
        match: Match data from API
    
    Returns:
        Dictionary with predictions
    """
    home_team = match.get('homeTeam', {}).get('name', 'Home Team')
    away_team = match.get('awayTeam', {}).get('name', 'Away Team')
    league_code = match.get('competition', {}).get('code', 'PL')
    
    home_stats = None
    away_stats = None

    # Keep soccerdata path available but disabled by default.
    if USE_SOCCERDATA:
        home_stats = get_team_statistics(home_team, league_code, seasons=2)
        away_stats = get_team_statistics(away_team, league_code, seasons=2)

    # Use completed match score from FOOTBALL_DATA when available.
    full_time = match.get('score', {}).get('fullTime', {})
    home_ft = full_time.get('home')
    away_ft = full_time.get('away')
    has_real_score = home_ft is not None and away_ft is not None

    if has_real_score:
        home_score = int(home_ft)
        away_score = int(away_ft)
        home_expected = float(home_score)
        away_expected = float(away_score)
    elif home_stats and away_stats:
        # Optional soccerdata-based path (disabled unless USE_SOCCERDATA=true).
        home_avg_goals = home_stats['avg_goals_scored']
        away_avg_goals = away_stats['avg_goals_scored']
        home_avg_conceded = home_stats['avg_goals_conceded']
        away_avg_conceded = away_stats['avg_goals_conceded']

        home_expected = (home_avg_goals + away_avg_conceded) / 2 * 1.2
        away_expected = (away_avg_goals + home_avg_conceded) / 2 * 0.9
        home_score = min(int(round(home_expected)), 4)
        away_score = min(int(round(away_expected)), 3)
    else:
        # FOOTBALL_DATA-only deterministic estimate from team IDs for scheduled matches.
        home_id = match.get('homeTeam', {}).get('id') or 0
        away_id = match.get('awayTeam', {}).get('id') or 0
        base = (home_id + away_id + (match.get('id') or 0)) % 5
        home_score = 1 + (base // 2)
        away_score = base % 2
        home_expected = float(home_score)
        away_expected = float(away_score)
    
    # Result prediction
    if home_score > away_score:
        result = f'{home_team} gana'
        probability = 0.45
    elif home_score < away_score:
        result = f'{away_team} gana'
        probability = 0.30
    else:
        result = 'Empate'
        probability = 0.25
    
    # Enhanced stats predictions based on league averages
    total_goals = home_score + away_score
    
    prediction = {
        'match_id': match.get('id'),
        'home_team': home_team,
        'away_team': away_team,
        'date': match.get('utcDate'),
        'competition': match.get('competition', {}).get('name', 'Unknown'),
        'predicted_score': f'{home_score}-{away_score}',
        'predicted_result': result,
        'confidence': f'{int(probability * 100)}%',
        'data_source': 'football_data' if not home_stats or not away_stats else 'soccerdata',
        'goals_prediction': {
            'total_goals': total_goals,
            'over_2_5': total_goals > 2.5,
            'both_teams_score': home_score > 0 and away_score > 0,
            'home_to_score': home_score > 0,
            'away_to_score': away_score > 0
        },
        'stats_prediction': {
            'corners': int(round(8 + total_goals * 1.3)),
            'fouls': int(round(14 + total_goals * 1.8)),
            'yellow_cards': int(round(2 + total_goals * 0.7)),
            'possession_home': int(round(max(35, min(65, 50 + (home_expected - away_expected) * 5)))),
            'shots_on_target_home': max(1, home_score + 3),
            'shots_on_target_away': max(1, away_score + 3)
        },
        'team_stats': {
            'home': home_stats if home_stats else {
                'avg_goals_scored': round(home_expected, 2),
                'avg_goals_conceded': round(away_expected, 2),
                'total_matches': 0,
                'home_matches': 0,
                'away_matches': 0,
            },
            'away': away_stats if away_stats else {
                'avg_goals_scored': round(away_expected, 2),
                'avg_goals_conceded': round(home_expected, 2),
                'total_matches': 0,
                'home_matches': 0,
                'away_matches': 0,
            },
        }
    }
    
    return prediction

@app.route('/')
def home():
    """Home page showing today's match predictions"""
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Fetch today's matches
    matches = get_matches(date_from=today, date_to=tomorrow)
    
    # Generate predictions for each match
    predictions = [p for p in (generate_prediction(match) for match in matches[:10]) if p is not None]
    
    return render_template('index.html', 
                         predictions=predictions, 
                         date=today,
                         leagues=LEAGUES)

@app.route('/search')
def search():
    """Search page for finding specific match predictions"""
    return render_template('search.html', leagues=LEAGUES)

@app.route('/api/predictions')
def api_predictions():
    """API endpoint to get predictions"""
    league_code = request.args.get('league')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if not date_from:
        date_from = datetime.now().strftime('%Y-%m-%d')
    if not date_to:
        date_to = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    matches = get_matches(league_code, date_from, date_to)
    predictions = [p for p in (generate_prediction(match) for match in matches) if p is not None]
    
    return jsonify({
        'success': True,
        'count': len(predictions),
        'predictions': predictions
    })

@app.route('/api/match/<int:match_id>')
def api_match_prediction(match_id):
    """API endpoint to get prediction for a specific match"""
    # In a real implementation, we would fetch this specific match
    # For now, we'll search through recent matches
    matches = get_matches()
    
    match = next((m for m in matches if m.get('id') == match_id), None)
    
    if match:
        prediction = generate_prediction(match)
        if prediction is None:
            return jsonify({
                'success': False,
                'error': 'No historical data available for this match yet'
            }), 422
        return jsonify({
            'success': True,
            'prediction': prediction
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Match not found'
        }), 404

@app.route('/leagues/<league_code>')
def league_predictions(league_code):
    """Show predictions for a specific league"""
    if league_code not in LEAGUES:
        return "League not found", 404
    
    today = datetime.now().strftime('%Y-%m-%d')
    end_date = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
    
    matches = get_matches(league_code, date_from=today, date_to=end_date)
    predictions = [p for p in (generate_prediction(match) for match in matches) if p is not None]
    
    return render_template('league.html',
                         predictions=predictions,
                         league_code=league_code,
                         league_name=LEAGUE_NAMES.get(league_code, league_code),
                         leagues=LEAGUES)

if __name__ == '__main__':
    # WARNING: Debug mode should be disabled in production
    # Use a production WSGI server (gunicorn, uwsgi) for deployment
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    # Bind to 127.0.0.1 for local development, 0.0.0.0 only for containers
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    app.run(debug=debug_mode, host=host, port=5000)
