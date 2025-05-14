from flask import Flask, render_template, request, redirect, session, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import uuid
from pytz import timezone

IST = timezone('Asia/Kolkata')
now = datetime.now(IST)
from datetime import timedelta
app = Flask(__name__)
app.secret_key = '611b5ff2e01220fa8df00578e1353cbcd4e519a8'  # Replace with a secure secret key

# Setup Google Sheets API
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open("Data").sheet1  # Replace with your actual sheet name

# Helper to append lead to sheet with empty follow-up fields
def append_lead(data):
    # Add empty placeholders for follow-up fields (12 in total: 3 fields × 4 follow-ups)
    empty_followups = ['' for _ in range(12)]
    full_row = data + empty_followups
    sheet.append_row(full_row)

@app.route('/', methods=['GET', 'POST'])
def lead_form():
    if request.method == 'POST':
        now = datetime.now()
        data = [
            now.strftime('%Y-%m-%d %H:%M:%S'),  # Full timestamp
            request.form['name'],
            request.form['phone'],
            request.form['comment'],
            request.form['who_met'],
            now.strftime('%Y-%m-%d'),           # Only the date
            request.form['location']
            ]

        append_lead(data)

        # Store last 3 entries in session
        entry_id = str(uuid.uuid4())
        entry_data = dict(zip(
            ['timestamp', 'name', 'phone', 'comment', 'who_met', 'date', 'location'],
            data
        ))
        session.setdefault('entries', []).append({'id': entry_id, 'data': entry_data})
        session['entries'] = session['entries'][-3:]  # Keep only the last 3 entries
        session.modified = True

        return redirect(url_for('lead_form'))

    return render_template('lead_form.html', entries=session.get('entries', []))
@app.route('/edit/<entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    entries = session.get('entries', [])
    entry = next((e for e in entries if e['id'] == entry_id), None)
    if not entry:
        return "Entry not found", 404

    if request.method == 'POST':
        # Update session data
        entry['data']['name'] = request.form['name']
        entry['data']['phone'] = request.form['phone']
        entry['data']['comment'] = request.form['comment']
        entry['data']['who_met'] = request.form['who_met']
        entry['data']['location'] = request.form['location']
        session['entries'] = entries
        session.modified = True

        # Update Google Sheet (find by timestamp)
        all_rows = sheet.get_all_records()
        for i, row in enumerate(all_rows, start=2):  # Offset for header
            if row['Timestamp'] == entry['data']['timestamp']:
                sheet.update(f'B{i}', [[
                    entry['data']['name'],
                    entry['data']['phone'],
                    entry['data']['comment'],
                    entry['data']['who_met'],
                    entry['data']['date'],
                    entry['data']['location']
                ]])
                break

        return redirect(url_for('lead_form'))

    return render_template('edit_entry.html', entry=entry)


if __name__ == '__main__':
    app.run(debug=True)
