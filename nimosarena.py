import requests
import time
from flask import Flask, render_template_string, request, redirect
import json  # Required to read the JSON file
import os    # Required to check if the file exists
app = Flask(__name__)

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, render_template_string, request, redirect, url_for
from datetime import datetime, timedelta
app = Flask(__name__)

# --- TEMPORARY STORAGE ---
# This holds orders in the server memory until the next restart
memory_orders = []

# --- GOOGLE SHEETS SETUP ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Load credentials from Render Environment Variable
creds_json_string = os.environ.get('GOOGLE_CREDS_JSON')

if creds_json_string:
    creds_dict = json.loads(creds_json_string)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
else:
    # Local fallback
    creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

client = gspread.authorize(creds)

# USE THE EXACT NAME YOU PROVIDED
try:
    sheet = client.open("Nimo's Arena").sheet1
    print("Successfully connected to Google Sheets!")
except gspread.exceptions.SpreadsheetNotFound:
    print("ERROR: Spreadsheet 'Nimo's Arena' not found. Check the name or sharing permissions.")


@app.route('/live-track', methods=['POST'])
def live_track():
    data = request.json
    email = data.get('email')
    phone = data.get('phone')
    
    # We look for the email in the sheet. If it exists, update phone. 
    # If not, add a new row.
    try:
        cell = sheet.find(email)
        sheet.update_cell(cell.row, 2, phone) # Update Phone
        sheet.update_cell(cell.row, 5, "Typing...") # Update Status
    except:
        # Add a new row for a new user typing
        sheet.append_row([email, phone, "N/A", "0", "Typing...", "N/A"])
        
    return {"status": "ok"}

# --- CONFIGURATION ---
PAYSTACK_SECRET_KEY = "sk_test_8af4a01e1539445328e43c7d5556e228be746e44"

# This list stores your orders during the session
order_alerts = []

# --- DATABASE LOGIC (Reads from the file where orders are stored) ---
DB_FILE = "orders.json"  # Ensure this file exists, even if it's empty

def get_orders():
    # If the file doesn't exist, return an empty list
    if not os.path.exists(DB_FILE):
        return []
    
    # Try to read the file, if it's corrupted return an empty list
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return []

# --- HTML TEMPLATES ---

HOME_PAGE = """
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    ... your other tags ...
</head>
<div style="text-align: center; font-family: sans-serif; padding-top: 50px; background-color: #f9f9f9; min-height: 100vh;">
    <div style="display: inline-block; background: white; padding: 40px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); width: 320px;">
        <h1 style="color: #333; margin-bottom: 5px;">Nimo's Arena</h1>
        <p style="color: #777; margin-bottom: 25px;">Buy Bundles Instantly</p>
        
        <form action="/pay" method="POST">
            <input type="email" name="email" placeholder="Your Email" required 
                   style="padding: 12px; width: 100%; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 15px; box-sizing: border-box;">
            
            <input type="tel" name="phone" placeholder="Phone Number (e.g. 054...)" required 
                   style="padding: 12px; width: 100%; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 15px; box-sizing: border-box;">

            <select name="package_type" required 
                    style="padding: 12px; width: 100%; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 15px; background: white;">
                <option value="" disabled selected>Select Bundle Type</option>
                <option value="Internet Bundle">Internet Bundle</option>
                <option value="Call Bundle">Call Bundle</option>
            </select>

            <input type="number" name="amount" placeholder="Amount (GHS)" min="1" required 
                   style="padding: 12px; width: 100%; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 25px; box-sizing: border-box;">
            
            <button type="submit" style="background: #00bbff; color: white; border: none; padding: 15px; width: 100%; cursor: pointer; border-radius: 8px; font-weight: bold; font-size: 16px;">
                Proceed to Pay
            </button>
        </form>
    </div>
</div>
<div style="text-align: center; margin: 20px 0;">
    <a href="/packages" style="display: inline-block; padding: 15px 30px; background-color: #ffcc00; color: #000; text-decoration: none; border-radius: 10px; font-weight: bold; border: 2px solid #000;">
        ⚡ Click to view packages and prices
    </a>
</div>
"""
ADMIN_PAGE = """
<div style="font-family: sans-serif; padding: 40px;">
    <h2 style="border-bottom: 2px solid #00bbff; padding-bottom: 10px;">Order Alerts (Admin)</h2>
    <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
        <thead>
            <tr style="background-color: #f2f2f2; text-align: left;">
                <th style="padding: 12px; border: 1px solid #ddd;">Customer Email</th>
                <th style="padding: 12px; border: 1px solid #ddd;">Phone Number</th>
                <th style="padding: 12px; border: 1px solid #ddd;">Bundle Type</th>
                <th style="padding: 12px; border: 1px solid #ddd;">Amount (GHS)</th>
                <th style="padding: 12px; border: 1px solid #ddd;">Status</th>
                <th style="padding: 12px; border: 1px solid #ddd;">Action</th>
            </tr>
        </thead>
        <tbody>
            {% for order in orders %}
            <tr>
                <td style="padding: 12px; border: 1px solid #ddd;">{{ order.email }}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{{ order.phone }}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">{{ order.package }}</td>
                <td style="padding: 12px; border: 1px solid #ddd;">GHS {{ order.amount }}</td>
                <td style="padding: 12px; border: 1px solid #ddd; font-weight: bold; color: {{ 'green' if order.status == 'Success' else 'orange' }};">
                    {{ order.status }}
                </td>
                <td style="padding: 12px; border: 1px solid #ddd;">
                    {% if order.status == 'Pending' %}
                    <a href="/mark-success/{{ loop.index0 }}" style="color: #00bbff; text-decoration: none; font-weight: bold;">Mark Done</a>
                    {% else %}
                    ✅ Complete
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    <p style="margin-top: 20px;"><a href="/">← Back to Store</a></p>
</div>
"""

# --- ROUTES ---

@app.route('/')
def home():
    return render_template_string(HOME_PAGE)

@app.route('/packages')
def packages():
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Nimos Arena - Packages</title>
        <style>
            body { font-family: sans-serif; text-align: center; background-color: #0b1121; color: white; padding: 20px; margin: 0; }
            .container { max-width: 600px; margin: 0 auto; }
            img { width: 100%; height: auto; border-radius: 15px; border: 2px solid #c5a059; }
            .back-btn { display: inline-block; margin: 25px 0; padding: 12px 30px; background: linear-gradient(90deg, #c5a059, #8e6d2f); color: white; text-decoration: none; border-radius: 50px; font-weight: bold; font-size: 1.1rem; }
        </style>
    </head>
    <body>
        <div class="container">
            <img src="/static/prices.png" alt="MTN Data Price List">
            <br>
            <a href="/" class="back-btn">← Back to Store</a>
        </div>
    </body>
    </html>
    ''')

@app.route('/pay', methods=['POST'])
def pay():
    email = request.form.get('email')
    user_amount = request.form.get('amount')
    phone = request.form.get('phone')
    p_type = request.form.get('package_type')
    
    # Convert GHS to Pesewas for Paystack
    amount_in_pesewas = int(user_amount) * 100

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
                
    data = {
        "email": email,
        "amount": amount_in_pesewas,
        "currency": "GHS",
        "callback_url": "https://nimosarena.onrender.com/callback"
    }
            
    try:
        r = requests.post("https://api.paystack.co/transaction/initialize", headers=headers, json=data)
        res = r.json()

        if res['status']:
            # THE CORRECT SINGLE SAVE:
            # We use 'order_alerts' to match your latest logic
            order_alerts.append({
                "Email": email,
                "Phone": phone,
                "Package": p_type,
                "Amount": user_amount,
                "Status": "Pending",
                "Timestamp": datetime.now(), # For high-accuracy filtering
                "Date": datetime.now().strftime("%Y-%m-%d"), # Backup for safety
                "ref": res['data']['reference']
            })
            return redirect(res['data']['authorization_url'])
        else:
            return f"Error from Paystack: {res['message']}"
    except Exception as e:
        return f"System Error: {str(e)}" 

@app.route('/mark-done/<int:order_index>')
def mark_done(order_index):
    try:
        # We must update order_alerts because that is what the dashboard displays
        # Use [::-1] logic because the dashboard shows orders in reverse
        actual_index = len(order_alerts) - 1 - order_index
        
        if 0 <= actual_index < len(order_alerts):
            order_alerts[actual_index]['Status'] = 'Done'
            
        return redirect(url_for('callback'))
    except Exception as e:
        return f"Error updating status: {str(e)}"

SUCCESS_PAGE = """
<div style="font-family: sans-serif; text-align: center; padding: 50px;">
    <h2 style="color: green;">Payment Successful!</h2>
    <p>Your order has been received and is being processed.</p>
    <br>
    <a href="/recent-orders" style="display: inline-block; padding: 12px 24px; background-color: #00bbff; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">
        View Recent Orders
    </a>
    <p style="margin-top: 20px;"><a href="/">Return Home</a></p>
</div>
"""

RECENT_ORDERS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 10px; background-color: #f0f2f5; color: #333; }
        .nimo-warning { background: #000; color: #deff9a; padding: 15px; text-align: center; font-size: 12px; font-weight: bold; line-height: 1.4; border-bottom: 4px solid #deff9a; }
        
        .success-box { background: white; padding: 25px; text-align: center; border-radius: 12px; margin: 15px 0; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        .success-box h2 { color: #28a745; margin: 0 0 10px 0; }
        .success-box p { margin: 0; color: #555; font-weight: 500; }

        .filter-section { text-align: center; margin: 20px 0; }
        .filter-title { font-size: 14px; font-weight: bold; color: #666; margin-bottom: 10px; display: block; text-transform: uppercase; }
        .btn-group { display: flex; justify-content: center; gap: 5px; flex-wrap: wrap; }
        .btn-filter { background: white; border: 1px solid #ddd; padding: 8px 12px; border-radius: 20px; font-size: 12px; text-decoration: none; color: #333; transition: 0.3s; }
        .btn-filter.active { background: #000; color: #deff9a; border-color: #000; }

        .card { background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); overflow-x: auto; margin-top: 10px; }
        table { width: 100%; border-collapse: collapse; min-width: 700px; }
        th { text-align: left; background: #f8f9fa; padding: 15px; font-size: 11px; color: #888; text-transform: uppercase; }
        td { padding: 15px; border-bottom: 1px solid #f0f0f0; font-size: 13px; }
        
        .status-Pending { color: #f39c12; font-weight: bold; background: #fff9e6; padding: 4px 8px; border-radius: 4px; }
        .status-Done { color: #27ae60; font-weight: bold; background: #eafff2; padding: 4px 8px; border-radius: 4px; }
        
        .btn-done { background: #00bbff; color: white; padding: 6px 12px; text-decoration: none; border-radius: 6px; font-size: 11px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="nimo-warning">
        ⚠️ THE RIGHT TO CHANGE STATUS FROM Pending TO Done IS RESERVED FOR MR. NIMO ALONE. KINDLY TAKE NOTE! ⚠️
    </div>

    <div class="success-box">
        <h2>Payment Sent! ✅</h2>
        <p>Your Bundle will be received shortly.</p>
    </div>

    <div class="filter-section">
        <span class="filter-title">View Recent Orders</span>
        <div class="btn-group">
            <a href="/callback?filter=today" class="btn-filter {% if filter == 'today' %}active{% endif %}">Today</a>
            <a href="/callback?filter=week" class="btn-filter {% if filter == 'week' %}active{% endif %}">This Week</a>
            <a href="/callback?filter=month" class="btn-filter {% if filter == 'month' %}active{% endif %}">This Month</a>
            <a href="/callback?filter=year" class="btn-filter {% if filter == 'year' %}active{% endif %}">This Year</a>
        </div>
    </div>
    
    <div class="card">
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Email</th>
                    <th>Phone</th>
                    <th>Bundle</th>
                    <th>Amount</th>
                    <th>Status</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
                {% for order in orders %}
                <tr>
                    <td>{{ order.Time }}</td>
                    <td>{{ order.Email }}</td>
                    <td>{{ order.Phone }}</td>
                    <td>{{ order.Package }}</td>
                    <td>GHS {{ order.Amount }}</td>
                    <td><span class="status-{{ order.Status }}">{{ order.Status }}</span></td>
                    <td>
                        {% if order.Status == 'Pending' %}
                            <a href="/mark-done/{{ loop.index0 }}" class="btn-done">Mark Done</a>
                        {% else %}
                            <span style="color: #bbb;">Completed</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <p style="text-align: center; margin: 30px 0;">
        <a href="/" style="color: #00bbff; text-decoration: none; font-weight: bold;">← Back to Store</a>
    </p>
</body>
</html>
"""
@app.route('/callback')
def callback():
    filter_type = request.args.get('filter', 'today')
    filtered_orders = []
    
    now = datetime.now()
    
    # Define time boundaries
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_today - timedelta(days=now.weekday()) # Monday of this week
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    for order in order_alerts:
        # 1. Use .get() to avoid crashing. Use the same variable name 'order_time'
        order_date_str = order.get('Date', datetime.now().strftime("%Y-%m-%d"))
        order_time = datetime.strptime(order_date_str, "%Y-%m-%d")

        # 2. Match the indentation level for the filter logic
        if filter_type == 'today':
            if order_time >= start_of_today:
                filtered_orders.append(order)
        
        # Check if order belongs in the selected category
        if filter_type == 'today':
            if order_time >= start_of_today:
                filtered_orders.append(order)
                
        elif filter_type == 'week':
            if order_time >= start_of_week:
                filtered_orders.append(order)
                
        elif filter_type == 'month':
            if order_time >= start_of_month:
                filtered_orders.append(order)
                
        elif filter_type == 'year':
            if order_time >= start_of_year:
                filtered_orders.append(order)

    # Convert the Timestamp to a readable string just for the HTML table
    display_orders = []
    for o in filtered_orders:
        display_copy = o.copy()
        display_copy['Time'] = o['Timestamp'].strftime("%H:%M")
        display_copy['Date'] = o['Timestamp'].strftime("%d %b") # e.g., 01 May
        display_orders.append(display_copy)

    return render_template_string(RECENT_ORDERS_HTML, orders=display_orders[::-1], filter=filter_type)

@app.route('/admin')
def admin():
    return render_template_string(ADMIN_PAGE, orders=order_alerts[::-1])

@app.route('/mark-success/<int:idx>')
def mark_success(idx):
    real_idx = len(order_alerts) - 1 - idx
    order_alerts[real_idx]['status'] = "Success"
    return redirect('/admin')

# --- ADD THIS TO nimosarena.py ---

# A secret token to keep this API private. Make up a strong password here.
# Keep this secret!
API_SECURITY_TOKEN = "State2580@agogo" 

@app.route('/api/v1/get_orders', methods=['GET'])
def api_get_orders():
    # Basic security check
    auth_token = request.headers.get('X-Api-Token')
    
    if auth_token != API_SECURITY_TOKEN:
        return {"error": "Unauthorized"}, 403

    # We reuse your existing get_orders() function that reads the JSON file.
    # Return newest orders first.
    return {"orders": get_orders()[::-1]}

if __name__ == '__main__':
    app.run(debug=False)