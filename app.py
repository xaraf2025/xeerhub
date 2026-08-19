import os, json
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='static')

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

# ══════════════════════════════════════════════
#  SECURITY FIX: Mailchimp credentials must come from
#  environment variables, never be hardcoded in source.
#  The key that was previously hardcoded here has been
#  committed to source control and shared externally —
#  it must be rotated in the Mailchimp dashboard
#  (Account > Extras > API keys) regardless of this fix.
# ══════════════════════════════════════════════
MAILCHIMP_API_KEY = os.environ.get("MAILCHIMP_API_KEY", "").strip()
MAILCHIMP_LIST_ID = os.environ.get("MAILCHIMP_LIST_ID", "").strip()
MAILCHIMP_DC = os.environ.get("MAILCHIMP_DC", "").strip()

# ══════════════════════════════════════════════
#  LEGACY / DEAD ENDPOINTS
#  /api/ask and /api/qa are NOT called by the current
#  frontend (it talks to the Railway Node service and a
#  hardcoded JS QA object instead). Left enabled, they:
#   - burn Groq quota on unauthenticated requests
#   - serve a stale, mismatched Q&A dataset (old law list)
#  Disabled by default. Set ENABLE_LEGACY_API=1 in the
#  environment only if you have a real reason to use them,
#  and add rate limiting / auth before doing so.
# ══════════════════════════════════════════════
ENABLE_LEGACY_API = os.environ.get("ENABLE_LEGACY_API", "").strip() == "1"

SYSTEM_PROMPT = """You are XeerHub AI, a legal information assistant specializing exclusively in the laws of the Federal Republic of Somalia.

STRICT RULES:
- Answer in plain English that a non-lawyer can understand
- Always cite the specific article number(s): e.g. "Labour Code · Art. 38"
- Keep answers under 160 words
- Never give a definitive legal opinion
- End every answer with: "For your specific situation, consult a qualified Somali lawyer."
- Never invent article numbers"""

# NOTE: The full legacy QA_DATA blob (Labour/Companies/Foreign Investment/
# Civil Law, ~200 entries) has been intentionally removed from this file.
# It described a DIFFERENT law lineup than the current site (which covers
# Labour, Foreign Investment, Income Tax 2025, EPMA 2024, Data Protection),
# and having it live behind /api/qa risked serving stale/wrong content if
# ever wired up by mistake. The current site's Q&A Library is sourced from
# static/index.html's client-side QA object; keep that as the single
# source of truth, or migrate it to Supabase per your roadmap notes.


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


@app.route('/api/qa')
def get_qa():
    if not ENABLE_LEGACY_API:
        return jsonify({'error': 'This endpoint is deprecated. The Q&A library is served client-side.'}), 404
    return jsonify([])  # legacy dataset removed — see note above


# ══════════════════════════════════════════════
#  MAILCHIMP SUBSCRIBE ENDPOINT
# ══════════════════════════════════════════════
@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    import requests as req
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email required'}), 400

    if not (MAILCHIMP_API_KEY and MAILCHIMP_LIST_ID and MAILCHIMP_DC):
        return jsonify({'error': 'Mailchimp not configured on server'}), 500

    url = 'https://{}.api.mailchimp.com/3.0/lists/{}/members'.format(MAILCHIMP_DC, MAILCHIMP_LIST_ID)

    try:
        resp = req.put(
            url + '/' + __import__('hashlib').md5(email.encode()).hexdigest(),
            auth=('anystring', MAILCHIMP_API_KEY),
            json={
                'email_address': email,
                'status_if_new': 'pending',
                'status': 'pending'
            },
            timeout=15
        )
        body = resp.json()
        if resp.status_code in (200, 201):
            return jsonify({'status': body.get('status', 'pending')}), 200
        if resp.status_code == 400 and body.get('title') == 'Member Exists':
            return jsonify({'status': 'subscribed'}), 200
        return jsonify({'status': 'pending', 'detail': body.get('detail', '')}), 200
    except Exception as e:
        print('Subscribe error:', str(e), flush=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/ask', methods=['POST'])
def ask():
    if not ENABLE_LEGACY_API:
        return jsonify({'error': 'This endpoint is deprecated. Use the Railway /ask service used by the frontend.'}), 404

    import requests as req
    data = request.get_json()
    question = data.get('question', '').strip()
    law_area = data.get('lawArea', 'General')

    if not question:
        return jsonify({'error': 'Question is required'}), 400

    GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '').strip()
    if not GROQ_API_KEY:
        return jsonify({'error': 'API key not configured. Set GROQ_API_KEY environment variable.'}), 500

    payload = {
        'model': 'llama-3.3-70b-versatile',
        'max_tokens': 600,
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': 'Law area: ' + law_area + ' Question: ' + question}
        ]
    }
    headers = {
        'Authorization': 'Bearer ' + GROQ_API_KEY,
        'content-type': 'application/json'
    }

    try:
        resp = req.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers, json=payload, timeout=30
        )
        if resp.status_code != 200:
            try:
                error_msg = resp.json().get('error', {}).get('message', 'Unknown error')
            except Exception:
                error_msg = resp.text
            return jsonify({'error': 'AI error: ' + error_msg}), 500

        result = resp.json()
        answer = result['choices'][0]['message']['content']
        return jsonify({'answer': answer, 'question': question})
    except req.exceptions.Timeout:
        return jsonify({'error': 'Request timed out. Please try again.'}), 504
    except Exception as e:
        return jsonify({'error': 'Server error: ' + str(e)}), 500


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('.', 'sitemap.xml', mimetype='application/xml')

@app.route('/robots.txt')
def robots():
    return send_from_directory('.', 'robots.txt', mimetype='text/plain')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
