#!/usr/bin/env python3
"""
Simple test script to verify Flask server can start
"""
import sys
import os

# Add project to path
sys.path.insert(0, '/workspaces/Gambit')

try:
    print("Testing imports...")
    import flask
    print("✓ Flask imported")
    
    import soccerdata
    print("✓ soccerdata imported")
    
    import pandas
    print("✓ pandas imported")
    
    from dotenv import load_dotenv
    print("✓ dotenv imported")
    
    print("\nLoading environment...")
    load_dotenv('/workspaces/Gambit/.env')
    print("✓ Environment loaded")
    
    api_key = os.environ.get('FOOTBALL_DATA_API_KEY', '')
    print(f"✓ API Key configured: {bool(api_key)} ({'*' * min(len(api_key), 5) if api_key else 'EMPTY'})")
    
    print("\nTrying to import app...")
    import app as gambit_app
    print("✓ App module imported")
    
    print("\nStarting Flask server...")
    print("Server will run on: http://0.0.0.0:5000")
    print("Access via: https://crispy-space-palm-tree-vqj64rgwgxxfr6w-5000.app.github.dev/")
    print("-" * 60)
    
    gambit_app.app.run(debug=True, host='0.0.0.0', port=5000)
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nTrying to install missing packages...")
    os.system("pip install -r /workspaces/Gambit/requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
