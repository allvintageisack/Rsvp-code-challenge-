# app.py
from flask import Flask, request, jsonify, send_from_directory, render_template
import sqlite3
import uuid
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables (e.g., EVENT_CAPACITY, EMAIL_SENDER)
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='static') # Serve static files from 'static'

# --- Configuration ---
DATABASE = 'event.db'
EVENT_CAPACITY = int(os.getenv('EVENT_CAPACITY', 100)) # Default capacity from .env or 100 if not set
# For initial testing, you can increase this or set in .env
# EVENT_CAPACITY = 500000

# --- Database Helper Functions ---
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row # This allows us to access columns by name
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS guests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            unique_link_id TEXT UNIQUE NOT NULL,
            rsvp_status TEXT DEFAULT 'pending', -- 'pending', 'confirmed', 'declined', 'waitlisted'
            rsvp_timestamp TEXT,
            email_sent INTEGER DEFAULT 0, -- 0 for false, 1 for true
            event_seat_number INTEGER -- Optional, for confirmed guests
        )
    ''')
    # You might want a table for email logs, but for "simplest technologies", keep it here.
    conn.commit()
    conn.close()

# Initialize the database when the app starts
with app.app_context():
    init_db()

# --- Routes ---

# Route to serve the main HTML page (the frontend)
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# API to get guest status and details (for frontend on page load)
@app.route('/api/guest_status')
def get_guest_status():
    unique_id = request.args.get('id')
    if not unique_id:
        return jsonify({'status': 'error', 'message': 'Missing unique ID'}), 400

    conn = get_db_connection()
    guest = conn.execute('SELECT full_name, email, rsvp_status FROM guests WHERE unique_link_id = ?', (unique_id,)).fetchone()
    conn.close()

    if guest:
        return jsonify({
            'status': 'success',
            'guest_name': guest['full_name'],
            'guest_email': guest['email'],
            'rsvp_status': guest['rsvp_status']
        })
    else:
        return jsonify({'status': 'error', 'message': 'Guest not found or invalid link.'}), 404

# API to handle RSVP submission
@app.route('/api/rsvp', methods=['POST'])
def rsvp():
    data = request.get_json()
    unique_id = data.get('unique_id')
    action = data.get('action') # 'confirm' or 'decline' (we'll implement decline later)

    if not unique_id or action not in ['confirm', 'decline']:
        return jsonify({'status': 'error', 'message': 'Invalid request data'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check current guest status and event capacity
        guest = cursor.execute(
            'SELECT id, rsvp_status FROM guests WHERE unique_link_id = ?', (unique_id,)
        ).fetchone()

        if not guest:
            conn.close()
            return jsonify({'status': 'error', 'message': 'Guest not found or invalid link.'}), 404

        guest_id = guest['id']
        current_status = guest['rsvp_status']

        if action == 'confirm':
            if current_status == 'confirmed':
                conn.close()
                return jsonify({'status': 'info', 'message': 'You have already confirmed your spot!'}), 200

            # Check available seats
            confirmed_guests_count = conn.execute(
                "SELECT COUNT(*) FROM guests WHERE rsvp_status = 'confirmed'"
            ).fetchone()[0]

            if confirmed_guests_count >= EVENT_CAPACITY:
                # Event is full, add to waitlist
                cursor.execute(
                    'UPDATE guests SET rsvp_status = ?, rsvp_timestamp = ? WHERE id = ?',
                    ('waitlisted', datetime.now().isoformat(), guest_id)
                )
                conn.commit()
                conn.close()
                return jsonify({'status': 'waitlisted', 'message': 'Event is full. You have been added to the waitlist.'}), 200
            else:
                # Confirm the spot
                cursor.execute(
                    'UPDATE guests SET rsvp_status = ?, rsvp_timestamp = ? WHERE id = ?',
                    ('confirmed', datetime.now().isoformat(), guest_id)
                )
                conn.commit()
                conn.close()
                return jsonify({'status': 'success', 'message': 'Your spot has been successfully confirmed!'}), 200

        elif action == 'decline':
            if current_status == 'declined':
                conn.close()
                return jsonify({'status': 'info', 'message': 'You have already declined this invitation.'}), 200

            cursor.execute(
                'UPDATE guests SET rsvp_status = ?, rsvp_timestamp = ? WHERE id = ?',
                ('declined', datetime.now().isoformat(), guest_id)
            )
            conn.commit()
            conn.close()
            return jsonify({'status': 'success', 'message': 'Your invitation has been declined.'}), 200

    except Exception as e:
        conn.rollback() # Rollback on error
        print(f"Error during RSVP: {e}")
        return jsonify({'status': 'error', 'message': 'An internal error occurred. Please try again.'}), 500
    finally:
        conn.close() # Ensure connection is closed even on success or error


# --- Admin Dashboard (Minimal for now) ---
# This would be expanded significantly for a full admin system

@app.route('/admin')
def admin_dashboard():
    conn = get_db_connection()
    guests = conn.execute('SELECT full_name, email, rsvp_status, email_sent FROM guests ORDER BY full_name').fetchall()
    conn.close()
    # For a simple demo, we'll just render text or a basic HTML list.
    # In a real app, you'd have dedicated admin HTML templates.
    # We can create a simple `admin.html` if you want a visual.
    return render_template('admin_summary.html', guests=guests) # This will look for 'admin_summary.html' in 'static'

# Let's add a basic admin_summary.html file to 'static'
# (Create static/admin_summary.html with simple table)

# --- Guest Management for Admin (Placeholder for CLI/Admin Panel) ---

# Example: Adding a guest from Python (for testing)
def add_guest(full_name, email):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        unique_id = str(uuid.uuid4())
        cursor.execute(
            'INSERT INTO guests (full_name, email, unique_link_id) VALUES (?, ?, ?)',
            (full_name, email, unique_id)
        )
        conn.commit()
        print(f"Added guest: {full_name} ({email}) with link ID: {unique_id}")
        return unique_id
    except sqlite3.IntegrityError:
        print(f"Error: Guest with email {email} already exists.")
        return None
    finally:
        conn.close()

# Example: Bulk import from CSV (simplified)
@app.route('/admin/import_guests', methods=['POST'])
def import_guests_from_csv_route():
    # This is a placeholder. A real import would handle file uploads etc.
    # For now, it just calls the function below.
    try:
        import_guests_from_csv('guests.csv')
        return jsonify({'status': 'success', 'message': 'Guests imported from CSV.'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Error importing guests: {e}'}), 500


def import_guests_from_csv(filepath):
    import csv
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        with open(filepath, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                full_name = row.get('full_name')
                email = row.get('email')
                if full_name and email:
                    unique_id = str(uuid.uuid4())
                    try:
                        cursor.execute(
                            'INSERT INTO guests (full_name, email, unique_link_id) VALUES (?, ?, ?)',
                            (full_name, email, unique_id)
                        )
                        print(f"Imported: {full_name} ({email})")
                    except sqlite3.IntegrityError:
                        print(f"Skipping duplicate email: {email}")
                else:
                    print(f"Skipping row due to missing data: {row}")
        conn.commit()
        print("CSV import finished.")
    except FileNotFoundError:
        print(f"Error: CSV file not found at {filepath}")
    except Exception as e:
        print(f"Error during CSV import: {e}")
        conn.rollback()
    finally:
        conn.close()


# --- Email Sending (Placeholder for Bulk Email) ---
# This part is highly simplified. Bulk email is a major system design challenge.

def send_email_invitation(guest_email, guest_name, unique_link_id):
    # In a real system, you'd use a transactional email service like SendGrid, Mailgun, AWS SES.
    # For now, we'll just print a placeholder and mark as sent.
    invite_url = f"http://127.0.0.1:5000/?id={unique_link_id}" # Replace with actual domain in production

    print(f"\n--- SIMULATING EMAIL SEND ---")
    print(f"TO: {guest_email} ({guest_name})")
    print(f"SUBJECT: Your Exclusive Event Invitation!")
    print(f"BODY: Hi {guest_name},\n\nYou're invited! Please confirm your spot here: {invite_url}\n\nSee you there!\n")
    print(f"--- END SIMULATION ---\n")

    conn = get_db_connection()
    try:
        conn.execute('UPDATE guests SET email_sent = 1 WHERE unique_link_id = ?', (unique_link_id,))
        conn.commit()
    except Exception as e:
        print(f"Error marking email as sent for {guest_email}: {e}")
        conn.rollback()
    finally:
        conn.close()
    return True # Simulate success for now

@app.route('/admin/send_invitations')
def send_invitations_route():
    # This is a very basic "send all pending" trigger for demo.
    # In a real system, this would be a background task, batched.
    conn = get_db_connection()
    pending_guests = conn.execute(
        "SELECT email, full_name, unique_link_id FROM guests WHERE email_sent = 0"
    ).fetchall()
    conn.close()

    sent_count = 0
    for guest in pending_guests:
        # In a real system, add to a message queue (e.g., Celery, RabbitMQ, SQS)
        # to handle rate limits and retries. For now, direct call.
        if send_email_invitation(guest['email'], guest['full_name'], guest['unique_link_id']):
            sent_count += 1
            # Add a small delay for demo purposes to simulate batching
            # import time
            # time.sleep(0.1) # Simulate sending time

    return jsonify({'status': 'success', 'message': f'Attempted to send {sent_count} invitations.'}), 200


# --- Main execution block ---
if __name__ == '__main__':
    # Initial setup if you want to run it from command line like:
    # python app.py add "John Doe" john.doe@example.com
    # python app.py import
    # python app.py send
    # python app.py runserver

    if len(os.sys.argv) > 1:
        if os.sys.argv[1] == 'add' and len(os.sys.argv) == 4:
            add_guest(os.sys.argv[2], os.sys.argv[3])
        elif os.sys.argv[1] == 'import':
            import_guests_from_csv('guests.csv') # Ensure guests.csv exists
        elif os.sys.argv[1] == 'send':
            with app.app_context(): # Needed for app context outside of request
                send_invitations_route()
        elif os.sys.argv[1] == 'runserver':
            app.run(debug=True) # debug=True reloads server on code changes
        else:
            print("Usage:")
            print("  python app.py runserver                  # Run the Flask web server")
            print("  python app.py add <full_name> <email>    # Add a single guest")
            print("  python app.py import                     # Import guests from guests.csv")
            print("  python app.py send                       # Send invitations to pending guests (simulated)")
    else:
        # Default action if no arguments provided
        app.run(debug=True) # Run the web server by default