from app import app

if __name__ == '__main__':
    from waitress import serve
    import os
    port = int(os.environ.get('PORT', 5000))
    print(f"Serving Yadav General Store on production WSGI (Waitress) at port {port}...")
    serve(app, host='0.0.0.0', port=port)
