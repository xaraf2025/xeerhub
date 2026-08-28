import os
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='static')

# ══════════════════════════════════════════════
#  NOTE ON SCOPE
#  This Flask service now does exactly two jobs:
#    1. Serve the static SPA (index.html, sitemap, robots)
#    2. Handle newsletter subscription (Mailchimp)
#
#  Everything else — the Q&A knowledge base and the
#  AI /ask endpoint — lives in server.js (Node/Railway),
#  which is the service the frontend actually calls
#  (RAILWAY_API in index.html). This file previously
#  carried a second, unused copy of both (QA_DATA and
#  /api/ask) using a stale taxonomy and an ungrounded
#  Groq prompt with no retrieval step. Both were removed
#  on 2026-08-27 — see repo history if you need them back
#  for reference, but do not resurrect /api/ask here: it
#  had no citation grounding and could hallucinate article
#  numbers, which conflicts with the "zero hallucination"
#  promise on the site.
# ══════════════════════════════════════════════


@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def static_files(path):
    try:
        full = os.path.join(app.static_folder, path)
        if os.path.exists(full):
            return send_from_directory(app.static_folder, path)
        return send_from_directory(app.static_folder, 'index.html')
    except Exception:
        return send_from_directory(app.static_folder, 'index.html')


# ══════════════════════════════════════════════
#  MAILCHIMP SUBSCRIBE ENDPOINT
# ══════════════════════════════════════════════
@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    import requests as req
    import hashlib

    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email required'}), 400

    MAILCHIMP_API_KEY = os.environ.get('MAILCHIMP_API_KEY', '').strip()
    MAILCHIMP_LIST_ID = os.environ.get('MAILCHIMP_LIST_ID', 'fb814dd0f4').strip()
    MAILCHIMP_DC = os.environ.get('MAILCHIMP_DC', 'us13').strip()

    if not MAILCHIMP_API_KEY:
        # Fail loudly server-side, gracefully client-side.
        # This should never happen in production if the env var is set,
        # but a hardcoded fallback key is exactly what caused the last
        # security incident, so we do not repeat that pattern here.
        print('MAILCHIMP_API_KEY not set in environment', flush=True)
        return jsonify({'error': 'Subscription service temporarily unavailable'}), 503

    url = 'https://{}.api.mailchimp.com/3.0/lists/{}/members'.format(MAILCHIMP_DC, MAILCHIMP_LIST_ID)
    member_hash = hashlib.md5(email.encode()).hexdigest()

    try:
        resp = req.put(
            url + '/' + member_hash,
            auth=('anystring', MAILCHIMP_API_KEY),
            json={
                'email_address': email,
                # FIXED: was 'pending'/'pending', which silently drops new
                # subscribers into double opt-in and they never receive a
                # confirmation email in some Mailchimp audience configs.
                # 'subscribed' adds them directly.
                'status_if_new': 'subscribed',
                'status': 'subscribed',
            },
            timeout=15,
        )
        print('Mailchimp status:', resp.status_code, resp.text[:200], flush=True)
        body = resp.json()
        if resp.status_code in (200, 201):
            return jsonify({'status': body.get('status', 'subscribed')}), 200
        if resp.status_code == 400 and body.get('title') == 'Member Exists':
            return jsonify({'status': 'subscribed'}), 200
        return jsonify({'status': 'pending', 'detail': body.get('detail', '')}), 200
    except req.exceptions.Timeout:
        return jsonify({'error': 'Subscription service timed out. Please try again.'}), 504
    except Exception as e:
        print('Subscribe error:', str(e), flush=True)
        return jsonify({'error': 'Could not subscribe. Please try again.'}), 500


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('.', 'sitemap.xml', mimetype='application/xml')


@app.route('/robots.txt')
def robots():
    return send_from_directory('.', 'robots.txt', mimetype='text/plain')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
