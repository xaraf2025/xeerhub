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
    """Mailchimp signup. Credentials come from environment variables only:
       MAILCHIMP_API_KEY (e.g. xxxxxxxx-us13) and MAILCHIMP_LIST_ID."""
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email or len(email) > 200:
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


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('.', 'sitemap.xml', mimetype='application/xml')


@app.route('/robots.txt')
def robots():
    return send_from_directory('.', 'robots.txt', mimetype='text/plain')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
