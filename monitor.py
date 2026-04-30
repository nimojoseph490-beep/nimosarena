import requests
import time
import os
import threading
from flask import Flask, render_template_string, redirect

app = Flask(__name__)

# --- CONFIGURATION (Match this to Phase 1) ---
LIVE_SITE_URL = "https://nimosarena.onrender.com"
# Must match the API_SECURITY_TOKEN you set in Phase 1
API_TOKEN = "State2580@agogo" 

# Stores orders retrieved from the live site
local_orders_cache = []

# --- DASHBOARD HTML (Matches image_5.png) ---
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nimo's Arena - Order Monitor</title>
    <style>
        body { font-family: sans-serif; padding: 40px; }
        h1 { margin-bottom: 20px; }
        .monitor-status { color: #555; margin-bottom: 30px; border-bottom: 2px solid #ddd; padding-bottom: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { text-align: left; background-color: #f2f2f2; padding: 15px; border: 1px solid #ddd; }
        td { padding: 15px; border: 1px solid #ddd; }
        .status-pending { color: orange; font-weight: bold; }
        .status-success { color: green; font-weight: bold; }
        .status-unknown { color: red; font-weight: bold; }
        .action-link { color: #00bbff; text-decoration: none; font-weight: bold; }
        .live-link { text-decoration: none; color: inherit; }
    </style>
</head>
<body>
    <div style="text-align: center; font-family: sans-serif; padding-top: 100px; background-color: #f9f9f9; height: 100vh;">
    <div style="display: inline-block; background: white; padding: 50px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
    <h1>Order Alerts (Admin)</h1>
    
    <div class="monitor-status">
        Live Monitor Status: <strong>Running...</strong> (Polling every 10 seconds)
    </div>

    <table>
        <thead>
            <tr>
                <th>Customer Email</th>
                <th>Phone Number</th>
                <th>Bundle Type</th>
                <th>Amount (GHS)</th>
                <th>Status</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
            {% for order in orders %}
            <tr>
                <td>{{ order.email }}</td>
                <td>{{ order.phone }}</td>
                <td>{{ order.package }}</td>
                <td>GHS {{ order.amount }}</td>
                
                <td class="
                    {% if order.status == 'Pending' %}status-pending
                    {% elif order.status == 'Success' %}status-success
                    {% else %}status-unknown{% endif %}
                ">
                    {{ order.status }}
                </td>
                
                <td>
                    {% if order.status == 'Pending' %}
                    <a href="/external-mark-done/{{ order.ref }}" class="action-link">Mark Done</a>
                    {% else %}
                    âœ… Complete
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
            {% if not orders %}
            <tr>
                <td colspan="6" style="text-align: center; color: #777; padding: 30px;">
                    No orders in cache. Waiting for next live update...
                </td>
            </tr>
            {% endif %}
        </tbody>
    </table>

    <p style="margin-top: 30px; font-size: 0.9em; color: #555;">
        This monitor is running locally on your machine.<br>
        Check the live site at: <a href="{{ live_url }}" class="live-link" target="_blank">{{ live_url }}</a>
    </p>
</div>
</body>
</html>
"""

# --- MONITORING LOGIC ---

def fetch_live_orders():
    global local_orders_cache
    print("!!! DEBUG: Background sync thread HAS STARTED !!!")
    
    headers = {'X-Api-Token': API_TOKEN}
    api_url = f"{LIVE_SITE_URL}/api/v1/get_orders"

    while True:
        try:
            print(f"--- Requesting data from {api_url} ---")
            response = requests.get(api_url, headers=headers, timeout=10)
            print(f"--- Server responded with status: {response.status_code} ---")
            
            if response.status_code == 200:
                data = response.json()
                local_orders_cache = data.get('orders', [])
                print(f"--- Successfully synced {len(local_orders_cache)} orders ---")
        except Exception as e:
            print(f"!!! CONNECTION ERROR: {e} !!!")
        
        time.sleep(10)  # Poll every 10 seconds

# Start the background thread
polling_thread = threading.Thread(target=fetch_live_orders, daemon=True)
polling_thread.start()

# --- ROUTES ---

@app.route('/admin')
def admin():
    # Serve the dashboard using the local cache of orders
    return render_template_string(DASHBOARD_HTML, orders=local_orders_cache, live_url=LIVE_SITE_URL)

@app.route('/external-mark-done/<ref>')
def external_mark_done(ref):
    # Optional: If you also want this monitor to update the live status,
    # you would need a corresponding API endpoint on the live site for 'mark_success'.
    print(f"DEBUG: 'Mark Done' action requested for reference: {ref}")
    print("WARNING: This monitor does not currently update the live site's status.")
    # For now, just refresh the admin page.
    return redirect('/admin')

@app.route('/')
def home():
    # Optional redirect to admin
    return redirect('/admin')

# 1. Start the background sync thread FIRST
polling_thread = threading.Thread(target=fetch_live_orders, daemon=True)
polling_thread.start()

# 2. Run the local website SECOND
if __name__ == '__main__':
    app.run(port=5001)