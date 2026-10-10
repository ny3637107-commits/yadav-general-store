import sys
import os
from config import Config
from app import app

if __name__ == '__main__':
    port = 5000
    is_prod = '--prod' in sys.argv or Config.ENVIRONMENT == 'production'
    
    for arg in sys.argv[1:]:
        if arg.isdigit():
            port = int(arg)
            
    if is_prod:
        from waitress import serve
        print(f"🚀 Starting Yadav General Store on Production WSGI (Waitress) http://127.0.0.1:{port}")
        serve(app, host='0.0.0.0', port=port)
    else:
        print(f"🛠️ Starting Yadav General Store in Development mode on http://127.0.0.1:{port}")
        app.run(host='0.0.0.0', port=port, debug=False)
