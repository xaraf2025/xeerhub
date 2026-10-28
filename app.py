import os, hashlib
import requests as req
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='static')


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    full = os.path.join(app.static_folder, path)
    if os.path.exists(full):
        return send_from_directory(app.static_folder, path)
    # SPA fallback: unknown paths render the app
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email required'}), 400

    api_key = os.environ.get('MAILCHIMP_API_KEY', '').strip()
    list_id = os.environ.get('MAILCHIMP_LIST_ID', '').strip()
    if not api_key or not list_id or '-' not in api_key:
        return jsonify({'error': 'Newsletter is not configured'}), 500
    dc = api_key.split('-')[1]

    url = 'https://{}.api.mailchimp.com/3.0/lists/{}/members/{}'.format(
        dc, list_id, hashlib.md5(email.encode()).hexdigest())
    try:
        resp = req.put(
            url,
            auth=('xeerhub', api_key),
            # status_if_new only: existing subscribers are never reset to pending
            json={'email_address': email, 'status_if_new': 'pending'},
            timeout=15,
        )
        body = resp.json() if resp.content else {}
        if resp.status_code in (200, 201):
            return jsonify({'status': 'subscribed' if body.get('status') == 'subscribed' else 'pending'}), 200
        print('Mailchimp error:', resp.status_code, body.get('title', ''), flush=True)
        return jsonify({'error': 'Subscription failed'}), 502
    except Exception as e:
        print('Subscribe error:', str(e), flush=True)
        return jsonify({'error': 'Server error'}), 500
