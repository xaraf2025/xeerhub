import os
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='static')

# NOTE: The following legacy routes were removed in this pass because they are
# dead/stale code, not because they were unused by accident:
#
#   - /api/qa   and its QA_DATA dict (Labour Code / Companies Law / Foreign
#     Investment / Civil Law) — this is an OLD 4-law dataset that does not
#     match the current 5-law product (Labour, Foreign Investment, ITA 2025,
#     EPMA 2024, Data Protection Act). It is not called by static/index.html
#     at all — the frontend hits the Railway service (server.js) directly for
#     Ask AI. Leaving this route live meant anyone hitting
#     xeerhub.com/api/qa got a *different, wrong* legal dataset served under
#     the XeerHub domain.
#   - /api/ask and SYSTEM_PROMPT — same issue: references "Companies Law" and
#     "Civil Law" which are no longer part of the product, and duplicates
#     (worse, contradicts) the real Ask AI logic that already lives in
#     server.js on Railway. Also required a GROQ_API_KEY this app was never
#     actually using in production.
#
# If either dataset needs to be resurrected (e.g. for an admin/debug view),
# pull it from git history and update it to match the current 5-law schema
# and QA content in static/index.html's QA object before re-adding.


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
#  Credentials MUST come from Railway environment variables.
#  Set these in the Railway dashboard for this service:
#    MAILCHIMP_API_KEY  (format: xxxxxxxxxxxxxxxxxxxxxxxx-usNN)
#    MAILCHIMP_LIST_ID
# ══════════════════════════════════════════════
MAILCHIMP_API_KEY = os.environ.get('MAILCHIMP_API_KEY', '').strip()
MAILCHIMP_LIST_ID = os.environ.get('MAILCHIMP_LIST_ID', '').strip()


@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    import requests as req
    import hashlib

    if not MAILCHIMP_API_KEY or not MAILCHIMP_LIST_ID:
        # Fail loudly in logs, but don't leak config state to the client.
        print('Mailchimp not configured: missing MAILCHIMP_API_KEY or MAILCHIMP_LIST_ID env var', flush=True)
        return jsonify({'error': 'Newsletter signup is temporarily unavailable.'}), 503

    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email required'}), 400

    # Derive the datacenter from the API key suffix (e.g. "...-us13") instead
    # of hardcoding it, so a key rotation to a different DC doesn't silently break this.
    try:
        mailchimp_dc = MAILCHIMP_API_KEY.split('-')[-1]
    except Exception:
        mailchimp_dc = 'us1'

    url = 'https://{}.api.mailchimp.com/3.0/lists/{}/members'.format(mailchimp_dc, MAILCHIMP_LIST_ID)

    try:
        resp = req.put(
            url + '/' + hashlib.md5(email.encode()).hexdigest(),
            auth=('anystring', MAILCHIMP_API_KEY),
            json={
                'email_address': email,
                'status_if_new': 'pending',
                'status': 'pending'
            },
            timeout=15
        )
        print('Mailchimp status:', resp.status_code, resp.text[:200], flush=True)
        body = resp.json()
        if resp.status_code in (200, 201):
            return jsonify({'status': body.get('status', 'pending')}), 200
        if resp.status_code == 400 and body.get('title') == 'Member Exists':
            return jsonify({'status': 'subscribed'}), 200
        return jsonify({'status': 'pending', 'detail': body.get('detail', '')}), 200
    except Exception as e:
        print('Subscribe error:', str(e), flush=True)
        return jsonify({'error': 'Could not process subscription right now.'}), 500


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('.', 'sitemap.xml', mimetype='application/xml')


@app.route('/robots.txt')
def robots():
    return send_from_directory('.', 'robots.txt', mimetype='text/plain')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
