import datetime
import io
from flask import Flask, jsonify, make_response, request, render_template, session, redirect, url_for, send_file, g
import json
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace 'your_secret_key' with a secure key
DATA_FILE = 'society_data.json'

def save_data(data):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file_path = os.path.join(script_dir, DATA_FILE)
    
    with open(data_file_path, 'w') as file:
        json.dump(data, file, indent=4)

def load_data():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_file_path = os.path.join(script_dir, DATA_FILE)
    
    if not os.path.exists(data_file_path):
        default_data = {"owners": [], "expenses": [], "funds": 0}
        save_data(default_data)
        return default_data
    try:
        with open(data_file_path, 'r') as file:
            return json.load(file)
    except json.JSONDecodeError:
        app.logger.error("Invalid JSON data. Initializing with default data.")
        default_data = {"owners": [], "expenses": [], "funds": 0}
        save_data(default_data)
        return default_data

@app.before_request
def load_current_user():
    if 'user' in session:
        data = load_data()
        g.current_user = next((owner for owner in data['owners'] if owner['email'] == session['user']), None)
    else:
        g.current_user = None

@app.context_processor
def inject_current_user():
    return dict(current_user=g.current_user)

@app.route('/')
def index():
    data = load_data()
    total_maintenance = sum(sum(int(m['amount']) for m in owner['maintenance']) for owner in data['owners'])
    total_expenses = sum(int(expense['amount']) for expense in data['expenses'])
    net_funds = total_maintenance - total_expenses
    return render_template('index.html', data=data, total_maintenance=total_maintenance, total_expenses=total_expenses, net_funds=net_funds)

@app.route('/signup', methods=['POST'])
def signup():
    data = load_data()
    new_user = request.json
    
    for owner in data['owners']:
        if owner['email'] == new_user['email']:
            return jsonify({"message": "User already in database"}), 409
    
    new_owner = {
        "name": new_user['name'],
        "email": new_user['email'],
        "password": new_user['password'],
        "userType": new_user['userType'],
        "Phone": [],
        "Address": [],
        "Family Members": [],
        "maintenance": []
    }
    data['owners'].append(new_owner)
    save_data(data)
    
    return jsonify({"message": "User added successfully!"})

@app.route('/login', methods=['POST'])
def login():
    data = load_data()
    user_check = request.json

    app.logger.info('Received login request: %s', user_check)

    for owner in data['owners']:
        app.logger.info('Checking owner: %s', owner)
        if owner['email'] == user_check['email'] and owner['password'] == user_check['password']:
            session['user'] = owner['email']
            app.logger.info('User found: %s', owner['email'])
            return jsonify({"message": "Login successful"}), 200
    
    app.logger.info('User not found or incorrect password for email: %s', user_check['email'])
    return jsonify({"message": "User not found or incorrect password"}), 401

@app.route('/home')
def home():
    data = load_data()
    total_maintenance = sum(sum(int(m['amount']) for m in owner['maintenance']) for owner in data['owners'])
    total_expenses = sum(int(expense['amount']) for expense in data['expenses'])
    net_funds = total_maintenance - total_expenses
    if 'user' in session:
        return render_template('home.html', data=data, total_maintenance=total_maintenance, total_expenses=total_expenses, net_funds=net_funds)
    else:
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/get_members')
def get_members():
    if 'user' not in session:
        return jsonify({'message': 'Unauthorized'}), 401
    
    data = load_data()
    current_user = next((owner for owner in data['owners'] if owner['email'] == session['user']), None)
    
    if not current_user:
        return jsonify({'message': 'User not found'}), 404

    if current_user['userType'] == 'admin':
        return jsonify({'message': 'User is an admin user', 'user': current_user, 'data': data}), 200
    else:
        return jsonify({'message': 'User is not an admin user'}), 403

@app.route('/get_current_user')
def get_current_user():
    if 'user' in session:
        data = load_data()
        current_user = next((owner for owner in data['owners'] if owner['email'] == session['user']), None)
        
        if current_user:
            return jsonify({'user': {'name': current_user['name'], 'userType': current_user['userType'], 'email': current_user['email']}})
    return jsonify({'user': None}), 401

@app.route('/edit_member', methods=['POST'])
def edit_member():
    data = load_data()
    member_update = request.json
    email = member_update['email']
    
    for owner in data['owners']:
        if owner['email'] == email:
            owner['name'] = member_update['newName']
            owner['email'] = member_update['newEmail']
            owner['password'] = member_update['newPassword']
            owner['userType'] = member_update['newUserType']
            owner['Phone'] = member_update['newPhone']
            owner['Address'] = member_update['newAddress']
            owner['Family Members'] = member_update['newFamilyMembers']
            save_data(data)
            return jsonify({"message": "Member updated successfully"})
    
    return jsonify({"message": "Member not found"}), 404

@app.route('/delete_member', methods=['POST'])
def delete_member():
    data = load_data()
    member_delete = request.json
    email = member_delete['email']
    
    for i, owner in enumerate(data['owners']):
        if owner['email'] == email:
            data['owners'].pop(i)
            save_data(data)
            return jsonify({"message": "Member deleted successfully"})
    
    return jsonify({"message": "Member not found"}), 404

@app.route('/add_maintenance', methods=['POST'])
def add_maintenance():
    data = load_data()
    maintenance_data = request.json
    email = maintenance_data['email']

    for owner in data['owners']:
        if owner['email'] == email:
            new_maintenance = {
                "amount": maintenance_data['amount'],
                "date": maintenance_data['date'],
                "method": maintenance_data['method']
            }
            owner['maintenance'].append(new_maintenance)
            save_data(data)
            return jsonify({"message": "Maintenance added successfully"}), 201
    
    return jsonify({"message": "Owner not found"}), 404

@app.route('/get_user', methods=['GET'])
def get_user():
    data = load_data()
    email = request.args.get('email')
    
    user = next((owner for owner in data['owners'] if owner['email'] == email), None)
    
    if user:
        return jsonify({"message": "User found", "user": user}), 200
    else:
        return jsonify({"message": "User not found"}), 404

@app.route('/add_maintenance_page')
def add_maintenance_page():
    
    return render_template('add_maintenance.html')

@app.route('/maintenance_Report')
def maintenance_Report():
    return render_template('maintenance_report.html')

@app.route('/Society')
def Society():
    data = load_data()
    total_maintenance = sum(sum(int(m['amount']) for m in owner['maintenance']) for owner in data['owners'])
    total_expenses = sum(int(expense['amount']) for expense in data['expenses'])
    net_funds = total_maintenance - total_expenses
    if 'user' in session:
        return render_template('home.html', data=data, total_maintenance=total_maintenance, total_expenses=total_expenses, net_funds=net_funds)
    else:
        return redirect(url_for('index'))


@app.route('/get_maintenance_report', methods=['GET'])
def get_maintenance_report():
    data = load_data()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    email = request.args.get('email')

    filtered_maintenance = []

    for owner in data['owners']:
        if email and owner['email'] != email:
            continue
        
        total_amount = 0
        for maintenance in owner['maintenance']:
            if start_date and maintenance['date'] < start_date:
                continue
            if end_date and maintenance['date'] > end_date:
                continue
            total_amount += int(maintenance['amount'])
        
        filtered_maintenance.append({
            'name': owner['name'],
            'email': owner['email'],
            'totalAmount': total_amount
        })
    
    return jsonify({'data': filtered_maintenance})

@app.route('/download_pdf', methods=['GET'])
def download_pdf():
    email = request.args.get('email')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    data = load_data()
    user = next((owner for owner in data['owners'] if owner['email'] == email), None)
    
    if not user:
        return jsonify({"message": "User not found"}), 404

    pdf_file_path = generate_pdf(user, start_date_str, end_date_str)
    return send_file(pdf_file_path, as_attachment=True)

def generate_pdf(user, start_date_str, end_date_str):
    pdf_file_path = f'{user["email"]}_maintenance_report.pdf'
    c = canvas.Canvas(pdf_file_path, pagesize=A4)

    # Convert date strings to datetime objects
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None

    # Filter maintenance data based on date range
    filtered_maintenance = [
        maintenance for maintenance in user['maintenance']
        if (not start_date or datetime.strptime(maintenance['date'], '%Y-%m-%d') >= start_date) and
           (not end_date or datetime.strptime(maintenance['date'], '%Y-%m-%d') <= end_date)
    ]

    # Calculate the grand total
    grand_total = sum(int(maintenance['amount']) for maintenance in filtered_maintenance)

    # Add a title with a larger font size and bold styling
    c.setFillColor(HexColor('#1A237E'))  # Dark blue color
    c.setFont("Helvetica-Bold", 16)
    c.drawString(30, 770, f"Maintenance Report for {user['name']}")

    # Add user email and date range below the title with a slightly smaller font size
    c.setFillColor(HexColor('#0D47A1'))  # Blue color
    c.setFont("Helvetica", 12)
    c.drawString(30, 750, f"Email: {user['email']} From: {start_date.strftime('%B %d, %Y')} To: {end_date.strftime('%B %d, %Y')} Printed: {datetime.now().strftime('%B %d, %Y, %H:%M')}")

    # Draw a line separator below the header
    c.setStrokeColor(HexColor('#64B5F6'))  # Light blue color
    c.setLineWidth(1)
    c.line(30, 740, 550, 740)

    # Table headers
    c.setFillColor(HexColor('#E65100'))  # Orange color
    c.setFont("Helvetica-Bold", 12)
    c.drawString(100, 720, "Date")
    c.drawString(200, 720, "Amount")
    c.drawString(300, 720, "Method")

    # Draw a line separator below the table headers
    c.setStrokeColor(HexColor('#64B5F6'))  # Light blue color
    c.setLineWidth(1)
    c.line(30, 710, 550, 710)

    y = 690
    c.setFillColor(HexColor('#000000'))  # Black color
    c.setFont("Helvetica", 12)
    for maintenance in filtered_maintenance:
        c.drawString(100, y, maintenance['date'])
        c.drawString(200, y, str(maintenance['amount']))
        c.drawString(300, y, maintenance['method'])
        y -= 20

        if y < 50:
            c.showPage()
            c.setFillColor(HexColor('#1A237E'))  # Dark blue color
            c.setFont("Helvetica-Bold", 16)
            c.drawString(30, 770, f"Maintenance Report for {user['name']}")
            c.setFillColor(HexColor('#0D47A1'))  # Blue color
            c.setFont("Helvetica", 12)
            c.drawString(30, 750, f"Email: {user['email']} From: {start_date.strftime('%B %d, %Y')} To: {end_date.strftime('%B %d, %Y')} Printed: {datetime.now().strftime('%B %d, %Y, %H:%M')}")
            c.setStrokeColor(HexColor('#64B5F6'))  # Light blue color
            c.setLineWidth(1)
            c.line(30, 740, 550, 740)
            c.setFillColor(HexColor('#E65100'))  # Orange color
            c.setFont("Helvetica-Bold", 12)
            c.drawString(100, 720, "Date")
            c.drawString(200, 720, "Amount")
            c.drawString(300, 720, "Method")
            c.setStrokeColor(HexColor('#64B5F6'))  # Light blue color
            c.setLineWidth(1)
            c.line(30, 710, 550, 710)
            y = 690
            c.setFillColor(HexColor('#000000'))  # Black color
            c.setFont("Helvetica", 12)
        
    # Add design elements before the grand total
    y -= 20
    c.setStrokeColor(HexColor('#64B5F6'))  # Light blue color
    c.setLineWidth(1)
    c.line(30, y, 550, y)
    y -= 20
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(HexColor('#1A237E'))  # Dark blue color
    c.drawString(100, y, "Grand Total")
    c.drawString(200, y, str(grand_total))
    y -= 20
    c.setStrokeColor(HexColor('#64B5F6'))  # Light blue color
    c.line(30, y, 550, y)

    # Add the footer note
    c.setFillColor(HexColor('#0D47A1'))  # Blue color
    c.setFont("Helvetica", 12)
    c.drawString(95, 10, "THIS IS SYSTEM GENERATED INVOICE AND REQUIRES NO SIGNATURE")

    c.save()
    return pdf_file_path



# Add Expense
@app.route('/add_expense', methods=['GET', 'POST'])
def add_expense():
    data = load_data()
    if request.method == 'POST':
        expense = {
            "id": len(data['expenses']) + 1,
            "description": request.form.get('description'),
            "amount": float(request.form.get('amount')),
            "date": request.form.get('date')
        }
        data['expenses'].append(expense)
        data['funds'] -= expense['amount']  # Deduct from total funds
        save_data(data)
        return redirect(url_for('list_expenses'))
    return render_template('add_expense.html')


# List Expenses
@app.route('/expenses', methods=['GET'])
def list_expenses():
    data = load_data()
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Convert date strings to datetime objects
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None

    # Filter the expenses data based on the date range
    filtered_expenses = [
        expense for expense in data['expenses']
        if (not start_date or datetime.strptime(expense['date'], '%Y-%m-%d') >= start_date) and
           (not end_date or datetime.strptime(expense['date'], '%Y-%m-%d') <= end_date)
    ]
    
    return render_template('expenses.html', expenses=filtered_expenses, start_date=start_date_str, end_date=end_date_str)


@app.route('/expenses/pdf')
def generate_expenses_pdf():
    data = load_data()
    
    # Extract the start and end dates from the request
    start_date_str = request.args.get('start_date')

    end_date_str = request.args.get('end_date')
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None
    
    # Filter the expenses data based on the date range
    filtered_expenses = [
        expense for expense in data['expenses']
        if (not start_date or datetime.strptime(expense['date'], '%Y-%m-%d') >= start_date) and
           (not end_date or datetime.strptime(expense['date'], '%Y-%m-%d') <= end_date)
    ]
    
    # Create a PDF buffer
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    
    # Set up the PDF
    width, height = A4
    p.setFont("Helvetica", 12)
    p.setFillColor(HexColor("#000000"))
    
    # Add title
    p.setFillColor(HexColor('#1A237E'))  # Dark blue color
    p.setFont("Helvetica-Bold", 16)
    p.drawString(30, height - 50, "Expenses Report")
    
    # Add printed date
    current_date = datetime.now().strftime('%B %d, %Y, %H:%M')
    p.setFillColor(HexColor('#0D47A1'))  # Blue color
    p.setFont("Helvetica", 12)
    p.drawString(30, height - 70, f"Printed: {current_date}")
    
    # Draw line separator
    p.setStrokeColor(HexColor('#64B5F6'))  # Light blue color
    p.setLineWidth(1)
    p.line(30, height - 80, width - 30, height - 80)
    
    # Table headers
    p.setFillColor(HexColor('#E65100'))  # Orange color
    p.setFont("Helvetica-Bold", 12)
    headers = ["ID", "Description", "Amount", "Date"]
    header_x_positions = [50, 150, 250, 350]
    for x, header in zip(header_x_positions, headers):
        p.drawString(x, height - 100, header)
    
    # Draw line separator
    p.setStrokeColor(HexColor('#64B5F6'))  # Light blue color
    p.setLineWidth(1)
    p.line(30, height - 110, width - 30, height - 110)
    
    y = height - 130
    p.setFillColor(HexColor('#000000'))  # Black color
    p.setFont("Helvetica", 12)
    for expense in filtered_expenses:
        p.drawString(50, y, str(expense['id']))
        p.drawString(150, y, expense['description'])
        p.drawString(250, y, str(expense['amount']))
        p.drawString(350, y, expense['date'])
        y -= 20

        if y < 50:
            p.showPage()
            p.setFillColor(HexColor('#1A237E'))  # Dark blue color
            p.setFont("Helvetica-Bold", 16)
            p.drawString(30, height - 50, "Expenses Report")
            p.setFillColor(HexColor('#0D47A1'))  # Blue color
            p.setFont("Helvetica", 12)
            p.drawString(30, height - 70, f"Printed: {current_date}")
            p.setStrokeColor(HexColor('#64B5F6'))  # Light blue color
            p.setLineWidth(1)
            p.line(30, height - 80, width - 30, height - 80)
            p.setFillColor(HexColor('#E65100'))  # Orange color
            p.setFont("Helvetica-Bold", 12)
            for x, header in zip(header_x_positions, headers):
                p.drawString(x, height - 100, header)
            p.setStrokeColor(HexColor('#64B5F6'))  # Light blue color
            p.setLineWidth(1)
            p.line(30, height - 110, width - 30, height - 110)
            y = height - 130
            p.setFillColor(HexColor('#000000'))  # Black color
            p.setFont("Helvetica", 12)
    
    # Add design elements before the grand total
    y -= 20
    p.setStrokeColor(HexColor('#64B5F6'))  # Light blue color
    p.setLineWidth(1)
    p.line(30, y, width - 30, y)
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.setFillColor(HexColor('#1A237E'))  # Dark blue color
    grand_total = sum(int(expense['amount']) for expense in filtered_expenses)
    p.drawString(100, y, "Grand Total")
    p.drawString(200, y, str(grand_total))
    y -= 20
    p.setStrokeColor(HexColor('#64B5F6'))  # Light blue color
    p.line(30, y, width - 30, y)
    
    # Add footer note
    p.setFillColor(HexColor('#0D47A1'))  # Blue color
    p.setFont("Helvetica", 12)
    p.drawString(95, 10, "THIS IS SYSTEM GENERATED INVOICE AND REQUIRES NO SIGNATURE")
    
    p.save()
    buffer.seek(0)
    
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=expenses.pdf'
    
    return response

@app.route('/maintenance_detail')
def maintenance_detail():
    return render_template('maintenance_detail.html')

if __name__ == '__main__':
    app.run(debug=True)
