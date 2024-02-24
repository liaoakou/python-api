from flask import Flask, Response, request, jsonify
from flask_restful import Api, Resource
import socket
import psycopg2
import time
import os
from prometheus_client import generate_latest, Counter, Gauge, Histogram
from flask_restful import Resource
from app import db
from models import QueryLog

app = Flask(__name__)
api = Api(app)

# Metrics
REQUEST_COUNT = Counter('app_request_count', 'Total web app request count')
REQUEST_LATENCY = Histogram('app_request_latency_seconds', 'Latency of requests in seconds')
IN_PROGRESS = Gauge('app_in_progress_requests', 'In progress requests')

# Set default values to None or specify default values
db_username = os.environ.get('DB_USERNAME', None)
db_password = os.environ.get('DB_PASSWORD', None)
db_name = os.environ.get('DB_NAME', None)

# Database connection settings
connection_string = f"postgresql://{db_username}:{db_password}@localhost/{db_name}"

# Utility functions
def resolve_domain(domain):
    try:
        return socket.gethostbyname(domain)
    except socket.gaierror:
        return None

def log_query(domain, ip_address):
    conn = psycopg2.connect(connection_string)
    cur = conn.cursor()
    cur.execute("INSERT INTO query_log (domain, result) VALUES (%s, %s)", (domain, ip_address))
    conn.commit()
    cur.close()
    conn.close()

def validate_ipv4(ip):
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False

# API Resources
class RootEndpoint(Resource):
    def get(self):
        REQUEST_COUNT.inc()
        return {
            "version": "0.1.0",
            "date": int(time.time()),
            "kubernetes": False
        }

class ValidateEndpoint(Resource):
    def get(self, ip):
        return {"valid": validate_ipv4(ip)}

class HistoryEndpoint(Resource):
    def get(self):
        # Query the last 20 entries ordered by timestamp
        recent_queries = QueryLog.query.order_by(QueryLog.timestamp.desc()).limit(20).all()
        
        # Transform the query results into a JSON-serializable format
        queries_json = [
            {"id": query.id, "domain": query.domain, "result": query.result, "timestamp": query.timestamp}
            for query in recent_queries
        ]
        
        return {"queries": queries_json}

@app.route('/health')
def health():
    return {"status": "ok"}

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype='text/plain')

@app.route('/v1/tools/lookup/<domain>', methods=['GET'])
def lookup(domain):
    ip_address = resolve_domain(domain)
    if ip_address:
        log_query(domain, ip_address)
        return jsonify({'domain': domain, 'ip_address': ip_address}), 200
    else:
        return jsonify({'error': 'Domain could not be resolved'}), 404

# Endpoint registration
api.add_resource(RootEndpoint, '/')
api.add_resource(ValidateEndpoint, '/v1/tools/validate/<string:ip>')
api.add_resource(HistoryEndpoint, '/v1/history')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
