import os
from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Football Data API Configuration
FOOTBALL_DATA_API_KEY = os.environ.get('FOOTBALL_DATA_API_KEY', '')
FOOTBALL_DATA_BASE_URL = 'https://api.football-data.org/v4'

# League codes mapping
LEAGUES = {
    'CL': 2001,  # UEFA Champions League
    'PL': 2021,  # Premier League
    'PD': 2014,  # La Liga (Primera Division)
    'BL1': 2002,  # Bundesliga
    'EC': 2018   # European Championship
}

def get_headers():
    """Get headers for Football Data API requests"""
    return {
        'X-Auth-Token': FOOTBALL_DATA_API_KEY
    }

def get_demo_matches(league_code=None):
    """
    Generate demo matches for demonstration purposes
    """
    from datetime import datetime, timedelta
    
    teams_by_league = {
        'CL': [
            ('Real Madrid', 'Bayern Munich'),
            ('Manchester City', 'Paris Saint-Germain'),
            ('Barcelona', 'Inter Milan'),
            ('Liverpool', 'AC Milan')
        ],
        'PL': [
            ('Manchester United', 'Chelsea'),
            ('Arsenal', 'Liverpool'),
            ('Manchester City', 'Tottenham'),
            ('Newcastle', 'Aston Villa')
        ],
        'PD': [
            ('Real Madrid', 'Barcelona'),
            ('Atletico Madrid', 'Sevilla'),
            ('Valencia', 'Real Sociedad'),
            ('Villarreal', 'Athletic Bilbao')
        ],
        'BL1': [
            ('Bayern Munich', 'Borussia Dortmund'),
            ('RB Leipzig', 'Bayer Leverkusen'),
            ('Eintracht Frankfurt', 'VfL Wolfsburg'),
            ('SC Freiburg', 'Union Berlin')
        ],
        'EC': [
            ('Spain', 'Germany'),
            ('France', 'England'),
            ('Italy', 'Portugal'),
            ('Netherlands', 'Belgium')
        ]
    }
    
    league_names = {
        'CL': 'UEFA Champions League',
        'PL': 'Premier League',
        'PD': 'La Liga',
        'BL1': 'Bundesliga',
        'EC': 'European Championship'
    }
    
    matches = []
    leagues_to_show = [league_code] if league_code and league_code in teams_by_league else list(teams_by_league.keys())
    
    for i, league in enumerate(leagues_to_show):
        for j, (home, away) in enumerate(teams_by_league[league][:4]):
            match_date = datetime.now() + timedelta(days=i, hours=j*3)
            matches.append({
                'id': 1000 + len(matches),
                'utcDate': match_date.isoformat() + 'Z',
                'status': 'SCHEDULED',
                'homeTeam': {'name': home, 'id': 100 + len(matches)},
                'awayTeam': {'name': away, 'id': 200 + len(matches)},
                'competition': {'name': league_names[league], 'code': league},
                'score': {'fullTime': {'home': None, 'away': None}}
            })
    
    return matches

def get_matches(league_code=None, date_from=None, date_to=None):
    """
    Fetch matches from Football Data API or use demo data
    
    Args:
        league_code: League code (CL, PL, PD, BL1, EC)
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
    
    Returns:
        List of matches
    """
    try:
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
        
        response = requests.get(url, headers=get_headers(), params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            if matches:
                return matches
            else:
                print("No matches from API, using demo data")
                return get_demo_matches(league_code)
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return get_demo_matches(league_code)
    except Exception as e:
        print(f"Error fetching matches: {e}, using demo data")
        return get_demo_matches(league_code)

def generate_prediction(match):
    """
    Generate predictions for a match based on team statistics
    
    This is a simplified prediction model. In a production system,
    this would use machine learning models trained on historical data.
    
    Args:
        match: Match data from API
    
    Returns:
        Dictionary with predictions
    """
    import random
    
    home_team = match.get('homeTeam', {}).get('name', 'Home Team')
    away_team = match.get('awayTeam', {}).get('name', 'Away Team')
    
    # Simple prediction logic (would be replaced with ML model)
    # For demonstration purposes, generating random but realistic predictions
    
    # Score prediction (most common scores in football)
    possible_scores = [
        (1, 0), (2, 0), (2, 1), (1, 1), (0, 0),
        (3, 0), (3, 1), (0, 1), (1, 2), (0, 2)
    ]
    home_score, away_score = random.choice(possible_scores)
    
    # Result prediction
    if home_score > away_score:
        result = f'{home_team} wins'
        probability = 0.45
    elif home_score < away_score:
        result = f'{away_team} wins'
        probability = 0.30
    else:
        result = 'Draw'
        probability = 0.25
    
    prediction = {
        'match_id': match.get('id'),
        'home_team': home_team,
        'away_team': away_team,
        'date': match.get('utcDate'),
        'competition': match.get('competition', {}).get('name', 'Unknown'),
        'predicted_score': f'{home_score}-{away_score}',
        'predicted_result': result,
        'confidence': f'{int(probability * 100)}%',
        'goals_prediction': {
            'total_goals': home_score + away_score,
            'over_2_5': (home_score + away_score) > 2.5,
            'both_teams_score': home_score > 0 and away_score > 0
        },
        'stats_prediction': {
            'corners': random.randint(8, 14),
            'fouls': random.randint(12, 25),
            'yellow_cards': random.randint(2, 6),
            'possession_home': random.randint(40, 60)
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
    predictions = [generate_prediction(match) for match in matches[:10]]  # Limit to 10 matches
    
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
    predictions = [generate_prediction(match) for match in matches]
    
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
    predictions = [generate_prediction(match) for match in matches]
    
    return render_template('league.html',
                         predictions=predictions,
                         league_code=league_code,
                         league_name=next(
                             (k for k, v in LEAGUES.items() if v == LEAGUES[league_code]),
                             league_code
                         ),
                         leagues=LEAGUES)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
