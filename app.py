
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, session
from functools import wraps
import sqlite3
import qrcode
from io import BytesIO

app = Flask(__name__)
app.secret_key = "ticketmate_secret_key_2026"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

events = {
    "Music Concert": 500,
    "College Fest": 200,
    "Museum Visit": 100
}


# Create database
def create_database():
    conn = sqlite3.connect("ticketmate.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            event TEXT,
            quantity INTEGER,
            total_price INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price INTEGER NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM events")

    if cursor.fetchone()[0] == 0:
        default_events = [
            ("Music Concert", 500),
            ("College Fest", 200),
            ("Museum Visit", 100)
        ]

        cursor.executemany(
            "INSERT INTO events (name, price) VALUES (?, ?)",
            default_events
        )

    conn.commit()
    conn.close()
def get_events():
    conn = sqlite3.connect("ticketmate.db")
    cursor = conn.cursor()

    cursor.execute("SELECT name, price FROM events")
    event_data = cursor.fetchall()

    conn.close()

    return dict(event_data)

# Homepage
@app.route("/")
def home():
    available_events = get_events()

    return render_template(
        "index.html",
        events=available_events
    )

# Chatbot
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip().lower()

    if not message:
        return jsonify({"reply": "Please enter a message."}), 400

    available_events = get_events()

    if any(word in message for word in ["hello", "hi", "hey"]):
        reply = "Hello! Welcome to TicketMate AI. How can I help you?"

    elif any(word in message for word in ["event", "events", "available"]):
        if available_events:
            reply = "Here are our available events:\n"
            for event, price in available_events.items():
                reply += f"{event} - ₹{price}\n"
        else:
            reply = "Sorry, no events are currently available."

    else:
        reply = "Sorry, I couldn't understand. Ask me about available events or ticket prices."

        for event, price in available_events.items():
            if event.lower() in message:
                if any(word in message for word in ["price", "cost", "how much"]):
                    reply = f"The ticket price for {event} is ₹{price}."
                elif any(word in message for word in ["book", "ticket"]):
                    reply = f"You can book {event} tickets at /book/{event}."
                else:
                    reply = f"{event} is available. The ticket price is ₹{price}."

                break

    return jsonify({"reply": reply})


# Booking page
@app.route("/book/<event_name>", methods=["GET", "POST"])
def booking(event_name):

    available_events = get_events()

    if event_name not in available_events:
        return "Event not found", 404

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        quantity = int(request.form["quantity"])

        if not name.strip() or not email.strip() or quantity < 1 or quantity > 10:
            return "Please enter valid booking details.", 400

        total_price = available_events[event_name] * quantity

        conn = sqlite3.connect("ticketmate.db")
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO bookings
            (name, email, event, quantity, total_price)
            VALUES (?, ?, ?, ?, ?)
        """, (name, email, event_name, quantity, total_price))

        booking_id = cursor.lastrowid

        conn.commit()
        conn.close()

        return render_template(
            "success.html",
            booking_id=booking_id,
            name=name,
            event=event_name,
            quantity=quantity,
            total_price=total_price
        )

    return render_template(
        "booking.html",
        event=event_name,
        price=available_events[event_name]
    )

# Generate QR code
@app.route("/qr/<int:booking_id>")
def generate_qr(booking_id):

    conn = sqlite3.connect("ticketmate.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, event, quantity FROM bookings WHERE id = ?",
        (booking_id,)
    )

    booking = cursor.fetchone()
    conn.close()

    if booking is None:
        return "Booking not found", 404

    qr_data = (
        f"TicketMate AI\n"
        f"Booking ID: {booking[0]}\n"
        f"Event: {booking[1]}\n"
        f"Tickets: {booking[2]}"
    )

    qr = qrcode.make(qr_data)

    image_buffer = BytesIO()
    qr.save(image_buffer, format="PNG")
    image_buffer.seek(0)

    return send_file(
        image_buffer,
        mimetype="image/png"
    )

# Check whether admin is logged in
def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "admin" not in session:
            return redirect(url_for("admin_login"))

        return function(*args, **kwargs)

    return wrapper


# Admin Login
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:

            session["admin"] = username

            return redirect(url_for("admin_dashboard"))

        return render_template(
            "admin_login.html",
            error="Invalid username or password"
        )

    return render_template("admin_login.html")


# Admin Logout
@app.route("/admin/logout")
def admin_logout():

    session.pop("admin", None)

    return redirect(url_for("admin_login"))
   
# Admin Dashboard
@app.route("/admin")
@admin_required
def admin_dashboard():

    conn = sqlite3.connect("ticketmate.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Total bookings
    cursor.execute("SELECT COUNT(*) FROM bookings")
    total_bookings = cursor.fetchone()[0]

    # Total tickets sold
    cursor.execute("SELECT SUM(quantity) FROM bookings")
    total_tickets = cursor.fetchone()[0] or 0

    # Total revenue
    cursor.execute("SELECT SUM(total_price) FROM bookings")
    total_revenue = cursor.fetchone()[0] or 0
    # Get all events
    cursor.execute("SELECT * FROM events ORDER BY id DESC")
    all_events = cursor.fetchall()

    # All booking details
    cursor.execute("""
        SELECT * FROM bookings
        ORDER BY id DESC
    """)
    bookings = cursor.fetchall()

    # Event-wise booking information
    cursor.execute("""
        SELECT event,
               SUM(quantity) AS tickets_sold,
               SUM(total_price) AS revenue
        FROM bookings
        GROUP BY event
    """)
    event_stats = cursor.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        total_bookings=total_bookings,
        total_tickets=total_tickets,
        total_revenue=total_revenue,
        bookings=bookings,
        event_stats=event_stats,
        events=all_events
    )
# Add New Event
@app.route("/admin/events/add", methods=["POST"])
@admin_required
def add_event():

    name = request.form.get("name", "").strip()

    try:
        price = int(request.form.get("price", 0))
    except ValueError:
        return "Invalid ticket price", 400

    if not name or price < 1:
        return "Enter a valid event name and price", 400

    conn = sqlite3.connect("ticketmate.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO events (name, price) VALUES (?, ?)",
            (name, price)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "This event already exists", 400

    conn.close()

    return redirect(url_for("admin_dashboard"))


# Edit Event
@app.route("/admin/events/edit/<int:event_id>", methods=["POST"])
@admin_required
def edit_event(event_id):

    name = request.form.get("name", "").strip()

    try:
        price = int(request.form.get("price", 0))
    except ValueError:
        return "Invalid ticket price", 400

    if not name or price < 1:
        return "Enter a valid event name and price", 400

    conn = sqlite3.connect("ticketmate.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE events SET name = ?, price = ? WHERE id = ?",
            (name, price, event_id)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return "This event name already exists", 400

    conn.close()

    return redirect(url_for("admin_dashboard"))


# Delete Event
@app.route("/admin/events/delete/<int:event_id>", methods=["POST"])
@admin_required
def delete_event(event_id):

    conn = sqlite3.connect("ticketmate.db")
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM events WHERE id = ?",
        (event_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("admin_dashboard"))   

if __name__ == "__main__":
    create_database()
    app.run(debug=True)
