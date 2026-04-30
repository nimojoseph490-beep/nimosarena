import requests
import time
from flask import Flask, render_template_string, request, redirect

app = Flask(__name__)

# --- CONFIGURATION ---
# Your Test Secret Key from image_feacb6.png
PAYSTACK_SECRET_KEY = "sk_live_a8e8c45194c64eda089a94553fa8912212ea5a4b"

# This list stores your orders during the session
order_alerts = []

# --- HTML TEMPLATES ---

HOME_PAGE = """
<div style="text-align: center; font-family: sans-serif; padding-top: 100px; background-color: #f9f9f9; height: 100vh;">
    <div style="display: inline-block; background: white; padding: 50px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
        <h1 style="color: #333;">Nimo's Arena</h1>
        <p style="color: #777;">Access Premium Service</p>
        <h2 style="color: #00bbff;">GHS 15.00</h2>
        
        <form action="/pay" method="POST" style="margin-top: 20px;">
            <input type="email" name="email" placeholder="Enter your email" required 
                   style="padding: 12px; width: 250px; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 20px;"><br>
            <button type="submit" style="background: #00bbff; color: white; border: none; padding: 15px 40px; cursor: pointer; border-radius: 8px; font-weight: bold;">
                Tap and Pay 15
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
                <th style="padding: 15px; border: 1px solid #ddd;">Customer</th>
                <th style="padding: 15px; border: 1px solid #ddd;">Reference</th>
                <th style="padding: 15px; border: 1px solid #ddd;">Status</th>
                <th style="padding: 15px; border: 1px solid #ddd;">Action</th>
            </tr>
        </thead>
        <tbody>
            {% for order in orders %}
            <tr>
                <td style="padding: 15px; border: 1px solid #ddd;">{{ order.email }}</td>
                <td style="padding: 15px; border: 1px solid #ddd;">{{ order.ref }}</td>
                <td style="padding: 15px; border: 1px solid #ddd; font-weight: bold; color: {{ 'green' if order.status == 'Success' else 'orange' }};">
                    {{ order.status }}
                </td>
                <td style="padding: 15px; border: 1px solid #ddd;">
                    {% if order.status == 'Pending' %}
                    <a href="/mark-success/{{ loop.index0 }}" style="color: #00bbff; text-decoration: none;">Mark Done</a>
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
    # Paystack amount is in pesewas (15 GHS = 1500 pesewas)
    amount = 15 * 100 

    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "email": email,
        "amount": amount,
        "currency": "GHS",
        "callback_url": "http://127.0.0.1:5000/callback"
    }
    
    try:
        r = requests.post("https://api.paystack.co/transaction/initialize", headers=headers, json=data)
        res = r.json()

        if res['status']:
            # Save to your list immediately
            order_alerts.append({"email": email, "ref": res['data']['reference'], "status": "Pending"})
            # Send customer to Paystack to pay
            return redirect(res['data']['authorization_url'])
        else:
            return f"Error from Paystack: {res['message']}"
    except Exception as e:
        return f"System Error: {str(e)}"

@app.route('/callback')
def callback():
    return """
    <div style="text-align: center; padding-top: 100px; font-family: sans-serif;">
        <h1 style="color: green;">Success!</h1>
        <p>Thank you for your payment of GHS 15.00.</p>
        <a href="/">Back to Home</a>
    </div>
    """

@app.route('/admin')
def admin():
    # Show orders with the newest ones at the top
    return render_template_string(ADMIN_PAGE, orders=order_alerts[::-1])

@app.route('/mark-success/<int:idx>')
def mark_success(idx):
    # Adjust for the reversed list in the admin view
    real_idx = len(order_alerts) - 1 - idx
    order_alerts[real_idx]['status'] = "Success"
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)