import os, json, hashlib
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder='static', template_folder='static')

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

SYSTEM_PROMPT = """You are XeerHub AI, a legal information assistant specializing exclusively in the laws of the Federal Republic of Somalia.

You have deep knowledge of:
1. The Somalia Labour Code
2. The Companies Law (Law No. 18, signed 26 December 2019)
3. The Foreign Investment Law of the Federal Republic of Somalia
4. The Somali Civil Law and general civil code principles

STRICT RULES:
- Answer in plain English that a non-lawyer can understand
- Always cite the specific article number(s): e.g. "Labour Code · Art. 38"
- Keep answers under 160 words
- Never give a definitive legal opinion
- End every answer with: "For your specific situation, consult a qualified Somali lawyer."
- Never invent article numbers"""


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
    except Exception as e:
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/qa')
def get_qa():
    return jsonify([])


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

    # Read from Railway environment variables — NEVER hardcode credentials
    MAILCHIMP_API_KEY = os.environ.get('MAILCHIMP_API_KEY', '').strip()
    MAILCHIMP_LIST_ID = os.environ.get('MAILCHIMP_LIST_ID', '').strip()
    MAILCHIMP_DC      = os.environ.get('MAILCHIMP_DC', 'us13').strip()

    if not MAILCHIMP_API_KEY or not MAILCHIMP_LIST_ID:
        print('ERROR: MAILCHIMP_API_KEY or MAILCHIMP_LIST_ID not set in environment', flush=True)
        return jsonify({'error': 'Newsletter service not configured'}), 500

    subscriber_hash = hashlib.md5(email.encode()).hexdigest()
    url = f'https://{MAILCHIMP_DC}.api.mailchimp.com/3.0/lists/{MAILCHIMP_LIST_ID}/members/{subscriber_hash}'

    payload = {
        'email_address': email,
        # 'subscribed' skips double opt-in so the subscriber receives
        # content immediately. Switch back to 'pending' if you want
        # Mailchimp to send a confirmation email first.
        'status_if_new': 'subscribed',
        'status': 'subscribed',
    }

    try:
        resp = req.put(
            url,
            auth=('anystring', MAILCHIMP_API_KEY),
            json=payload,
            timeout=15,
        )
        body = resp.json()
        print(f'Mailchimp status: {resp.status_code} | email: {email} | body: {str(body)[:300]}', flush=True)

        if resp.status_code in (200, 201):
            return jsonify({'status': body.get('status', 'subscribed')}), 200

        if resp.status_code == 400:
            title = body.get('title', '')
            detail = body.get('detail', '')

            if title == 'Member Exists':
                return jsonify({'status': 'subscribed'}), 200

            if 'fake or invalid' in detail.lower() or 'compliance state' in detail.lower():
                return jsonify({'error': 'This email address cannot be subscribed.'}), 400

        # All other responses — treat as success to avoid leaking info
        return jsonify({'status': 'subscribed'}), 200

    except req.exceptions.Timeout:
        print('Mailchimp timeout', flush=True)
        return jsonify({'error': 'Request timed out. Please try again.'}), 504
    except Exception as e:
        print(f'Subscribe error: {e}', flush=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/ask', methods=['POST'])
def ask():
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
            headers=headers,
            json=payload,
            timeout=30
        )

        if resp.status_code != 200:
            try:
                error_body = resp.json()
                error_msg = error_body.get('error', {}).get('message', 'Unknown error')
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
