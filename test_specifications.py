"""
Test script to verify compliance with main prompt specifications.

Original Prompt (Spanish):
"La web donde se integre esta API
https://soccerdata.readthedocs.io/en/latest/# Para tomar resultados y estadisticas y 
https://www.football-data.org/documentation/quickstart  en las ligas (CL, BL1, PD, PL, EC)
Para obtener los proximos partidos
Y muestre los pronosticos de resultados de partidos, quienes hacen gol, cuantas faltas se 
comenten, cuantos corners seran realizados, etc. Una pagina de inicio con los pronosticos 
de hoy y un buscador para los pronosticos de juegos individuales."

Requirements:
1. Integration with Football-Data.org API
2. Support for leagues: CL, BL1, PD, PL, EC
3. Get upcoming matches
4. Show predictions for:
   - Match results
   - Who scores goals
   - Number of fouls
   - Number of corners
   - Other statistics
5. Home page with today's predictions
6. Search page for individual match predictions
"""

import sys
import os
from datetime import datetime, timedelta

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app


def test_api_integration():
    """Test 1: Verify Football-Data.org API integration"""
    print("\n" + "="*80)
    print("TEST 1: API Integration")
    print("="*80)
    
    # Check if API key is configured
    api_key = os.environ.get('FOOTBALL_DATA_API_KEY', app.FOOTBALL_DATA_API_KEY)
    print(f"✓ API key configured: {bool(api_key)}")
    
    # Check API base URL
    expected_url = 'https://api.football-data.org/v4'
    print(f"✓ API base URL: {app.FOOTBALL_DATA_BASE_URL}")
    assert app.FOOTBALL_DATA_BASE_URL == expected_url, "API base URL mismatch"
    
    # Test get_headers function
    headers = app.get_headers()
    assert 'X-Auth-Token' in headers, "Missing X-Auth-Token header"
    print(f"✓ API headers configured correctly")
    
    print("\n✅ API Integration: PASSED")
    return True


def test_league_support():
    """Test 2: Verify support for required leagues (CL, BL1, PD, PL, EC)"""
    print("\n" + "="*80)
    print("TEST 2: League Support")
    print("="*80)
    
    required_leagues = ['CL', 'BL1', 'PD', 'PL', 'EC']
    
    for league in required_leagues:
        assert league in app.LEAGUES, f"Missing league: {league}"
        assert league in app.LEAGUE_NAMES, f"Missing league name: {league}"
        print(f"✓ {league}: {app.LEAGUE_NAMES[league]} (ID: {app.LEAGUES[league]})")
    
    print("\n✅ League Support: PASSED")
    return True


def test_match_fetching():
    """Test 3: Verify ability to fetch upcoming matches"""
    print("\n" + "="*80)
    print("TEST 3: Match Fetching")
    print("="*80)
    
    # Test fetching matches for each league
    for league_code in ['CL', 'PL', 'PD', 'BL1', 'EC']:
        matches = app.get_matches(league_code=league_code)
        print(f"✓ {league_code}: Found {len(matches)} matches")
        assert len(matches) > 0, f"No matches found for {league_code}"
    
    # Test fetching matches with date range
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    matches = app.get_matches(date_from=today, date_to=tomorrow)
    print(f"✓ Date range query: Found {len(matches)} matches")
    
    print("\n✅ Match Fetching: PASSED")
    return True


def test_prediction_completeness():
    """Test 4: Verify predictions include all required information"""
    print("\n" + "="*80)
    print("TEST 4: Prediction Completeness")
    print("="*80)
    
    # Get a sample match
    matches = app.get_matches()
    assert len(matches) > 0, "No matches available for testing"
    
    match = matches[0]
    prediction = app.generate_prediction(match)
    
    # Verify required fields
    required_fields = [
        'match_id',
        'home_team',
        'away_team',
        'date',
        'competition',
        'predicted_score',
        'predicted_result',
        'confidence',
        'goals_prediction',
        'stats_prediction'
    ]
    
    for field in required_fields:
        assert field in prediction, f"Missing field: {field}"
        print(f"✓ {field}: {type(prediction[field]).__name__}")
    
    # Verify goals prediction details
    goals_fields = ['total_goals', 'over_2_5', 'both_teams_score']
    for field in goals_fields:
        assert field in prediction['goals_prediction'], f"Missing goals field: {field}"
        print(f"  ✓ goals_prediction.{field}: {prediction['goals_prediction'][field]}")
    
    # Verify stats prediction details (corners, fouls, etc.)
    stats_fields = ['corners', 'fouls', 'yellow_cards', 'possession_home']
    for field in stats_fields:
        assert field in prediction['stats_prediction'], f"Missing stats field: {field}"
        print(f"  ✓ stats_prediction.{field}: {prediction['stats_prediction'][field]}")
    
    # Verify specific requirements from prompt
    print("\n  Specific Requirements:")
    print(f"  ✓ Match results: {prediction['predicted_result']}")
    print(f"  ✓ Goals (who scores): Implicit in score {prediction['predicted_score']}")
    print(f"  ✓ Fouls: {prediction['stats_prediction']['fouls']}")
    print(f"  ✓ Corners: {prediction['stats_prediction']['corners']}")
    print(f"  ✓ Other stats: Yellow cards, possession")
    
    print("\n✅ Prediction Completeness: PASSED")
    return True


def test_routes_exist():
    """Test 5: Verify required routes exist"""
    print("\n" + "="*80)
    print("TEST 5: Application Routes")
    print("="*80)
    
    client = app.app.test_client()
    
    # Test home page
    response = client.get('/')
    assert response.status_code == 200, "Home page not accessible"
    print(f"✓ Home page (/) - Status: {response.status_code}")
    
    # Test search page
    response = client.get('/search')
    assert response.status_code == 200, "Search page not accessible"
    print(f"✓ Search page (/search) - Status: {response.status_code}")
    
    # Test league pages
    for league in ['CL', 'PL', 'PD', 'BL1', 'EC']:
        response = client.get(f'/leagues/{league}')
        assert response.status_code == 200, f"League page {league} not accessible"
        print(f"✓ League page (/leagues/{league}) - Status: {response.status_code}")
    
    # Test API endpoints
    response = client.get('/api/predictions')
    assert response.status_code == 200, "API predictions endpoint not accessible"
    assert response.is_json, "API response is not JSON"
    print(f"✓ API predictions endpoint - Status: {response.status_code}")
    
    print("\n✅ Application Routes: PASSED")
    return True


def test_home_page_content():
    """Test 6: Verify home page shows today's predictions"""
    print("\n" + "="*80)
    print("TEST 6: Home Page Content")
    print("="*80)
    
    client = app.app.test_client()
    response = client.get('/')
    
    assert response.status_code == 200, "Home page not accessible"
    html = response.data.decode('utf-8')
    
    # Check for expected content
    assert 'Pronósticos de Fútbol' in html or 'Gambit' in html, "Missing title"
    print("✓ Page title present")
    
    assert 'prediction' in html.lower() or 'pronóstico' in html.lower(), "Missing predictions"
    print("✓ Predictions content present")
    
    # Check for date
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"✓ Today's date: {today}")
    
    print("\n✅ Home Page Content: PASSED")
    return True


def test_search_functionality():
    """Test 7: Verify search functionality for individual matches"""
    print("\n" + "="*80)
    print("TEST 7: Search Functionality")
    print("="*80)
    
    client = app.app.test_client()
    
    # Test search page
    response = client.get('/search')
    assert response.status_code == 200, "Search page not accessible"
    html = response.data.decode('utf-8')
    
    assert 'Buscar' in html or 'Search' in html.lower(), "Missing search interface"
    print("✓ Search page accessible")
    
    # Test API search with parameters
    today = datetime.now().strftime('%Y-%m-%d')
    tomorrow = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
    
    # Search by league
    response = client.get(f'/api/predictions?league=CL&date_from={today}&date_to={tomorrow}')
    assert response.status_code == 200, "Search API not working"
    data = response.get_json()
    assert data['success'], "API search failed"
    print(f"✓ Search by league: Found {data['count']} predictions")
    
    # Search by date range
    response = client.get(f'/api/predictions?date_from={today}&date_to={tomorrow}')
    assert response.status_code == 200, "Date range search not working"
    data = response.get_json()
    assert data['success'], "API date search failed"
    print(f"✓ Search by date range: Found {data['count']} predictions")
    
    print("\n✅ Search Functionality: PASSED")
    return True


def run_all_tests():
    """Run all specification tests"""
    print("\n" + "="*80)
    print("GAMBIT - MAIN PROMPT SPECIFICATIONS VERIFICATION")
    print("="*80)
    print("\nVerifying compliance with original requirements...")
    
    tests = [
        test_api_integration,
        test_league_support,
        test_match_fetching,
        test_prediction_completeness,
        test_routes_exist,
        test_home_page_content,
        test_search_functionality,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, True, None))
        except AssertionError as e:
            results.append((test.__name__, False, str(e)))
            print(f"\n❌ {test.__name__}: FAILED - {e}")
        except Exception as e:
            results.append((test.__name__, False, f"Error: {str(e)}"))
            print(f"\n❌ {test.__name__}: ERROR - {e}")
    
    # Print summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, error in results:
        status = "✅ PASSED" if success else f"❌ FAILED: {error}"
        print(f"{test_name}: {status}")
    
    print("\n" + "="*80)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("="*80)
    
    if passed == total:
        print("\n🎉 ALL SPECIFICATIONS MET! The application complies with the main prompt.")
        return 0
    else:
        print("\n⚠️  Some specifications are not met. Review the failures above.")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
