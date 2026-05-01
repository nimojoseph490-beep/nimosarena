import requests
import time
from flask import Flask, render_template_string, request, redirect
import json  # Required to read the JSON file
import os    # Required to check if the file exists
app = Flask(__name__)

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, redirect
from datetime import datetime
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

@app.route('/pay', methods=['POST'])
def pay():
    email = request.form.get('email')
    user_amount = request.form.get('amount')
    phone = request.form.get('phone')
    p_type = request.form.get('package_type')
    

    # Convert GHS to Pesewas for Paystack
    amount_in_pesewas = int(user_amount) * 100

# ADD THIS LINE HERE:
    memory_orders.append({
        "Email": email,
        "Phone": phone,
        "Package": p_type,
        "Amount": user_amount,
        "Status": "Pending",
        "Time": datetime.now().strftime("%H:%M")
    })

    # ... keep your existing Paystack redirect logic here ...


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
            # Store full details in the list
            order_alerts.append({
                "email": email,
                "phone": phone,
                "package": p_type,
                "amount": user_amount,
                "ref": res['data']['reference'], 
                "status": "Pending"
            })
            return redirect(res['data']['authorization_url'])
        else:
            return f"Error from Paystack: {res['message']}"
    except Exception as e:
        return f"System Error: {str(e)}"
    
@app.route('/recent-orders')
def recent_orders():
    # This pulls directly from the 'memory_orders' list defined at the top
    return render_template_string(RECENT_ORDERS_HTML, orders=memory_orders[::-1])    

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
        body { font-family: sans-serif; margin: 0; padding: 15px; background-color: #f4f7f6; }
        .nimo-header { background: #000; color: #fff; padding: 15px; text-align: center; font-size: 14px; letter-spacing: 1px; margin-bottom: 20px; }
        .card { background: white; padding: 10px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; min-width: 500px; }
        th { text-align: left; background: #eee; padding: 10px; font-size: 12px; }
        td { padding: 10px; border-bottom: 1px solid #eee; font-size: 13px; }
        .status { font-weight: bold; color: orange; }
    </style>
</head>
<body>
    <div class="nimo-header">FOR MR. NIMO'S USE ONLY</div>
    <h3 style="text-align: center;">Recent Session Orders</h3>
    <div class="card">
        <table>
            <tr>
                <th>Time</th>
                <th>Email</th>
                <th>Package</th>
                <th>Status</th>
            </tr>
            {% for order in orders %}
            <tr>
                <td>{{ order.Time }}</td>
                <td>{{ order.Email }}</td>
                <td>{{ order.Package }}</td>
                <td class="status">{{ order.Status }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    <p style="text-align: center;"><a href="/">← Back to Store</a></p>
</body>
</html>
"""

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