from flask import Flask
from dashboard.routes import dashboard_bp, api_bp

app = Flask(__name__)

app.secret_key = '4b9f88cd1ea4f5b6a58efb4f083e0b11'

# Registrar el Blueprint
app.register_blueprint(dashboard_bp)
app.register_blueprint(api_bp)

if __name__ == '__main__':
    app.run(debug=True)
