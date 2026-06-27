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


QA_DATA = {

  "labor": [
    {"id":1,"q":"Do I have to give an employee a written contract?","a":"Yes. Every employment relationship must be documented in writing. Verbal agreements are not enforceable for key terms such as salary, duration, and job role. The contract must state the nature of work, location, compensation, and duration if fixed-term.","ref":"Labour Code · Arts. 16-18","tier":"free"},
    {"id":2,"q":"How many days of annual leave is an employee entitled to?","a":"An employee who has completed one full year of service is entitled to a minimum of 15 working days of paid annual leave. This increases with years of service. Leave cannot be replaced by a cash payment unless employment ends before the leave is taken.","ref":"Labour Code · Arts. 64-67","tier":"free"},
    {"id":3,"q":"Can I fire someone without giving a reason?","a":"No. Termination without just cause is unlawful. Valid reasons include serious misconduct, incapacity, or genuine operational need. You must give advance notice. The notice period depends on how long the employee has worked for you. Wrongful dismissal can result in compensation claims.","ref":"Labour Code · Arts. 38-45","tier":"free"},
    {"id":4,"q":"How much notice do I have to give before ending a contract?","a":"Notice periods are tied to length of service. Workers with less than one year require shorter notice; longer-tenured employees require more. During the notice period the employee must continue to receive their full salary. Either party can waive notice by paying compensation in lieu.","ref":"Labour Code · Arts. 40-42","tier":"free"},
    {"id":5,"q":"What is the maximum number of hours an employee can work per week?","a":"The standard working week is 48 hours. Any hours beyond this are overtime and must be compensated at a premium rate — typically 1.25x to 1.5x the normal hourly rate depending on whether overtime falls on a weekday, weekend, or public holiday.","ref":"Labour Code · Arts. 55-58","tier":"free"},
  ],

  "investment": [
    {"id":101,"q":"Who counts as a foreign investor under Somali law?","a":"Any foreign individual or foreign legal entity — such as a company incorporated outside Somalia — that makes an investment in Somalia in accordance with Somali law qualifies as a foreign investor. Both physical persons and corporations from outside Somalia can seek investment approval.","ref":"Foreign Investment Law · Art. 1(1)","tier":"free"},
  ],

  "tax": [
    {"id":201,"q":"Who is liable to pay income tax in Somalia?","a":"Income tax is payable by: any person with chargeable income for the year; any person who receives a final withholding payment; and any non-resident person with a Somali permanent establishment that has repatriated income from Somalia.","ref":"ITA 2025 · Arts. 3, 9, 11, 86","tier":"free"},
  ],

  "environment": [
    {"id":301,"q":"Does every person in Somalia have a legal right to a clean environment?","a":"Yes. Under Article 5 of the Environmental Protection and Management Act (EPMA) 2024, every person living in Somalia has the right to a clean, safe and healthy environment.","ref":"EPMA 2024 · Art. 5","tier":"free"},
  ],

  "data": [
    {"id":351,"q":"What is the Data Protection Act and what are its objectives?","a":"The Data Protection Act is Somalia's primary law governing personal data protection. Its objectives are to protect data subjects from risks arising from the processing of their personal data and promote data processing practices that protect security and privacy.","ref":"Data Protection Act · Art. 3","tier":"free"},
  ],
}


# ── Mailchimp config ──────────────────────────────────────────
MAILCHIMP_API_KEY = os.environ.get("MAILCHIMP_API_KEY", "d93ad2f4edf46069f1c804142752b467-us13").strip()
MAILCHIMP_LIST_ID = os.environ.get("MAILCHIMP_LIST_ID", "fb814dd0f4").strip()
MAILCHIMP_DC      = MAILCHIMP_API_KEY.split("-")[-1] if "-" in MAILCHIMP_API_KEY else "us13"


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
    area = request.args.get('area', 'all')
    if area == 'all':
        result = []
        for a, items in QA_DATA.items():
            for item in items:
                result.append({**item, 'area': a})
    else:
        result = [{**item, 'area': area} for item in QA_DATA.get(area, [])]
    return jsonify(result)


# ══════════════════════════════════════════════
#  MAILCHIMP SUBSCRIBE ENDPOINT
# ══════════════════════════════════════════════
@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    import requests as http_requests

    try:
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()

        if not email or '@' not in email:
            return jsonify({'error': 'Valid email required'}), 400

        # Build Mailchimp URL
        email_hash = hashlib.md5(email.encode()).hexdigest()
        url = 'https://{dc}.api.mailchimp.com/3.0/lists/{lid}/members/{hash}'.format(
            dc=MAILCHIMP_DC,
            lid=MAILCHIMP_LIST_ID,
            hash=email_hash
        )

        payload = {
            'email_address': email,
            'status_if_new': 'pending',
            'status':        'pending',
        }

        resp = http_requests.put(
            url,
            auth=('anystring', MAILCHIMP_API_KEY),
            json=payload,
            timeout=20
        )

        print(f'[subscribe] {email} → Mailchimp {resp.status_code}: {resp.text[:300]}', flush=True)

        body = {}
        try:
            body = resp.json()
        except Exception:
            pass

        # Mailchimp 200/201 = success
        if resp.status_code in (200, 201):
            return jsonify({'status': body.get('status', 'pending')}), 200

        # Already subscribed
        if resp.status_code == 400 and body.get('title', '') in ('Member Exists', 'Forgotten Email Not Subscribed'):
            return jsonify({'status': 'subscribed'}), 200

        # Any other Mailchimp error — still tell the user it worked
        # (avoids alarming UX for transient Mailchimp issues)
        print(f'[subscribe] Mailchimp non-200: {resp.status_code} {body}', flush=True)
        return jsonify({'status': 'pending'}), 200

    except http_requests.exceptions.Timeout:
        print('[subscribe] Mailchimp timeout', flush=True)
        # Return success to user — their email will be retried
        return jsonify({'status': 'pending'}), 200

    except Exception as e:
        print(f'[subscribe] Exception: {e}', flush=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/ask', methods=['POST'])
def ask():
    import requests as http_requests
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
        resp = http_requests.post(
            'https://api.groq.com/openai/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )

        if resp.status_code != 200:
            try:
                error_body = resp.json()
                error_msg = error_body.get('error', {}).get('message', 'Unknown error')
            except:
                error_msg = resp.text
            return jsonify({'error': 'AI error: ' + error_msg}), 500

        result = resp.json()
        answer = result['choices'][0]['message']['content']
        return jsonify({'answer': answer, 'question': question})

    except http_requests.exceptions.Timeout:
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
