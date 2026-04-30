import requests
import time
from flask import Flask, render_template_string, request, redirect

app = Flask(__name__)

# --- CONFIGURATION ---
PAYSTACK_SECRET_KEY = "sk_live_a8e8c45194c64eda089a94553fa8912212ea5a4b"

# This list stores your orders during the session
order_alerts = []

# --- HTML TEMPLATES ---

HOME_PAGE = """
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

@app.route('/callback')
def callback():
    return """
    <div style="text-align: center; padding-top: 100px; font-family: sans-serif;">
        <h1 style="color: green;">Payment Sent!</h1>
        <p>We have received your request. Your bundle will be sent shortly.</p>
        <a href="/">Back to Home</a>
    </div>
    """

@app.route('/admin')
def admin():
    return render_template_string(ADMIN_PAGE, orders=order_alerts[::-1])

@app.route('/mark-success/<int:idx>')
def mark_success(idx):
    real_idx = len(order_alerts) - 1 - idx
    order_alerts[real_idx]['status'] = "Success"
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=False)