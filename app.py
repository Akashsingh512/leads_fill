from flask import Flask, render_template, request, redirect, session, url_for
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import uuid
from pytz import timezone

# Initialize the Flask app
app = Flask(__name__)

# Set secret key for session handling
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

# Timezone for IST (India Standard Time)
IST = timezone('Asia/Kolkata')

# Define Users and Credentials (for login)
USERS = {
    'admin': {
        'password': 'admin123',
        'role': 'superadmin'
    },
    'user1': {
        'password': 'user123',
        'role': 'user'
    }
}


# Lead Form Route (Public)
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

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = USERS.get(username)

        if user and user['password'] == password:
            session['user'] = username
            session['role'] = user['role']
            print(f"User logged in: {session['user']}, Role: {session['role']}")  # Debugging log
            return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard
        else:
            error = 'Invalid credentials'

    return render_template('login.html', error=error)

# Logout Route
@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    return redirect(url_for('login'))  # Redirect back to login page

# Admin Dashboard Route
# @app.route('/admin')

# def admin_dashboard():
#      # Authenticate and fetch the worksheet
#     sheet = client.open_by_key("1G9u4zMuA9fbcsoIAJ0a7aQZAkrpS9fUjS5pnguav8C8").sheet1

#     # Manually fetch only the first row (headers)
#     raw_headers = sheet.row_values(1)
#     headers = raw_headers[:19]  # Columns A to S

#     # Now fetch the rest of the data
#     data = sheet.get_all_records(expected_headers=headers)

#     return render_template('admin_dashboard.html', data=data)


@app.route('/admin')
def admin_dashboard():
    if "user" not in session:
        return redirect("/login")

    try:
        # Open spreadsheet (you can use the global client if already initialized)
        spreadsheet_id = "1G9u4zMuA9fbcsoIAJ0a7aQZAkrpS9fUjS5pnguav8C8"  # Correct spreadsheet ID
        worksheet = client.open_by_key(spreadsheet_id).sheet1

        # Get all data (including headers)
        data = worksheet.get_all_values()
        # Example: data[0] is header row, data[1:] is the actual data

        return render_template("admin.html", user=session.get("user"), data=data)

    except Exception as e:
        return f"<h3>Error loading admin dashboard: {e}</h3>"

from flask import request, jsonify

# @app.route('/update_followup_cell', methods=['POST'])
# def update_followup_cell():
#     try:
#         data = request.get_json()
#         row = int(data['row'])   # 1-based index in Google Sheets (including header row)
#         col = int(data['col']) + 1 # gspread is 1-based columns

#         value = data['value']

#         # Open the sheet
#         spreadsheet_id = "YOUR_SHEET_ID"
#         worksheet = client.open_by_key(spreadsheet_id).sheet1

#         worksheet.update_cell(row, col, value)
#         return jsonify({'success': True})
#     except Exception as e:
#         return jsonify({'success': False, 'error': str(e)})
# old code upper
# # Edit Entry Route
# @app.route('/edit_entry/<entry_id>', methods=['GET', 'POST'])
# def edit_entry(entry_id):
#     if request.method == 'POST':
#         # Update the entry in the session
#         for entry in session['entries']:
#             if entry['id'] == entry_id:
#                 entry['data']['name'] = request.form['name']
#                 entry['data']['phone'] = request.form['phone']
#                 entry['data']['comment'] = request.form['comment']
#                 entry['data']['who_met'] = request.form['who_met']
#                 entry['data']['date'] = request.form['date']
#                 entry['data']['location'] = request.form['location']
#                 break

#         return redirect(url_for('lead_form'))

#     # Find the entry to edit
#     entry_data = next((entry for entry in session.get('entries', []) if entry['id'] == entry_id), None)
#     return render_template('edit_entry.html', entry=entry_data)



@app.route('/update_followup_cell', methods=['POST'])
def update_followup_cell():
    try:
        data = request.get_json()
        row = int(data['row'])  # 0-based row index (excluding header)
        field = data['field']
        value = data['value']

        # Define which field maps to which column
        field_column_map = {
    'FollowUp1_Comment': 7,
    'FollowUp1_Date': 8,
    'FollowUp1_WhoCalled': 9,
    'FollowUp2_Comment': 10,
    'FollowUp2_Date': 11,
    'FollowUp2_WhoCalled': 12,
    'FollowUp3_Comment': 13,
    'FollowUp3_Date': 14,
    'FollowUp3_WhoCalled': 15,
    'FollowUp4_Comment': 16,
    'FollowUp4_Date': 17,
    'FollowUp4_WhoCalled': 18
}


        col_index = field_column_map.get(field)
        if col_index is None:
            return jsonify({'success': False, 'error': 'Invalid field'})

        # Open sheet
        spreadsheet_id = "1G9u4zMuA9fbcsoIAJ0a7aQZAkrpS9fUjS5pnguav8C8"
        worksheet = client.open_by_key(spreadsheet_id).sheet1

        # +2 because row is 0-based, and first row is header
        worksheet.update_cell(row + 2, col_index + 1, value)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/edit_entry/<entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    if request.method == 'POST':
        # Update the entry in the session
        for entry in session['entries']:
            if entry['id'] == entry_id:
                entry['data']['name'] = request.form['name']
                entry['data']['phone'] = request.form['phone']
                entry['data']['comment'] = request.form['comment']
                entry['data']['who_met'] = request.form['who_met']
                entry['data']['date'] = request.form['date']
                entry['data']['location'] = request.form['location']
                break

        return redirect(url_for('lead_form'))

    # Find the entry to edit
    entry_data = next((entry for entry in session.get('entries', []) if entry['id'] == entry_id), None)
    return render_template('edit_entry.html', entry=entry_data)

# Main Entry Point
if __name__ == '__main__':
    app.run(debug=True)
