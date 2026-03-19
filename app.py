# =========================================
# IMPORTS
# =========================================
from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
import bcrypt
import random
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
CORS(app, origins=["http://bakshivijayalakshmi.chetantechnologies.com"])

otp_store = {}

# =========================================
# DATABASE CONNECTION
# =========================================
def get_db():
    return mysql.connector.connect(
        host="autorack.proxy.rlwy.net  ",
        user="root",
        password="ZPUFawUVzSbHfvwfiTNtdxZkvPyHlRqj",
        database="railway",
        port=46856
    )

# =========================================
# ADMIN AUTH CHECK
# =========================================
def verify_admin(req):
    token = req.headers.get("Authorization")

    if not token or not token.startswith("Bearer admin_token_"):
        return False
    return True


# =========================================
# AUTH ROUTES
# =========================================

# REGISTER
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    db = get_db()
    cursor = db.cursor(dictionary=True)

    role = data.get("role", "user")

    # Admin validation
    if role == "admin":
        if data.get("adminPasscode") != "Srianagha":
            return jsonify({"message": "Invalid admin passcode"}), 403

    cursor.execute("SELECT * FROM users WHERE email=%s", (data["email"],))
    if cursor.fetchone():
        return jsonify({"message": "User exists"}), 400

    # 🔐 HASH PASSWORD
    hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt()).decode()

    cursor.execute(
        "INSERT INTO users (name,email,password,role) VALUES (%s,%s,%s,%s)",
        (data["name"], data["email"], hashed, role)
    )
    db.commit()

    return jsonify({"message": "Registered successfully"})


# LOGIN
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM users WHERE email=%s", (data["email"],))
    user = cursor.fetchone()

    if not user:
        return jsonify({"message": "User not found"}), 400

    if not bcrypt.checkpw(data["password"].encode(), user["password"].encode()):
        return jsonify({"message": "Wrong password"}), 400

    cursor.execute("UPDATE users SET last_login=NOW() WHERE id=%s", (user["id"],))
    db.commit()

    return jsonify({
        "token": f"admin_token_{user['id']}",
        "user": user
    })


# SEND OTP
@app.route("/api/auth/send-otp", methods=["POST"])
def send_otp():
    email = request.json["email"]

    otp = str(random.randint(100000, 999999))
    otp_store[email] = otp

    msg = MIMEText(f"Your OTP is {otp}")
    msg["Subject"] = "OTP"
    msg["From"] = "your_email@gmail.com"
    msg["To"] = email

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login("srianaghaservice@gmail.com", "vdpzvumbxazsnejl")
    server.sendmail("your_email@gmail.com", email, msg.as_string())
    server.quit()

    return jsonify({"message": "OTP sent"})


# VERIFY OTP
@app.route("/api/auth/verify-otp", methods=["POST"])
def verify_otp():
    data = request.json

    if otp_store.get(data["email"]) == data["otp"]:
        return jsonify({"message": "OTP verified"})

    return jsonify({"message": "Invalid OTP"})


# RESET PASSWORD
@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.json

    db = get_db()
    cursor = db.cursor()

    hashed = bcrypt.hashpw(data["newPassword"].encode(), bcrypt.gensalt())

    cursor.execute(
        "UPDATE users SET password=%s WHERE email=%s",
        (hashed, data["email"])
    )
    db.commit()

    return jsonify({"message": "Password updated"})


# =========================================
# PRODUCTS (USER)
# =========================================

# GET PRODUCTS
@app.route("/api/products", methods=["GET"])
def get_products():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM products")
    return jsonify(cursor.fetchall())


# =========================================
# PRODUCTS (ADMIN)
# =========================================

# ADD PRODUCT
@app.route("/api/products", methods=["POST"])
def add_product():
    if not verify_admin(request):
        return jsonify({"message": "Unauthorized"}), 401

    data = request.json
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO products
        (name,category,sweetener,price,original_price,rating,reviews,image,badge,description)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data["name"],
        data["category"],
        data.get("sweetener", "Jaggery"),
        data["price"],
        data.get("original_price", data["price"] + 50),
        data.get("rating", 5.0),
        data.get("reviews", 0),
        data.get("image", ""),
        data.get("badge", ""),
        data.get("description", "")
    ))

    db.commit()
    return jsonify({"message": "Product added"})


# UPDATE PRODUCT
@app.route("/api/products/<int:id>", methods=["PUT"])
def update_product(id):
    if not verify_admin(request):
        return jsonify({"message": "Unauthorized"}), 401

    data = request.json
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE products SET
        name=%s,category=%s,sweetener=%s,price=%s,
        original_price=%s,rating=%s,reviews=%s,
        image=%s,badge=%s,description=%s
        WHERE id=%s
    """, (
        data["name"],
        data["category"],
        data.get("sweetener"),
        data["price"],
        data.get("original_price"),
        data.get("rating"),
        data.get("reviews"),
        data.get("image"),
        data.get("badge"),
        data.get("description"),
        id
    ))

    db.commit()
    return jsonify({"message": "Product updated"})


# DELETE PRODUCT
@app.route("/api/products/<int:id>", methods=["DELETE"])
def delete_product(id):
    if not verify_admin(request):
        return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM products WHERE id=%s", (id,))
    db.commit()

    return jsonify({"message": "Product deleted"})


# =========================================
# CART
# =========================================

# ADD
@app.route("/api/cart/add", methods=["POST"])
def cart_add():
    data = request.json
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM cart WHERE user_id=%s AND product_id=%s",
        (data["user_id"], data["product_id"])
    )

    if cursor.fetchone():
        cursor.execute(
            "UPDATE cart SET quantity=quantity+%s WHERE user_id=%s AND product_id=%s",
            (data.get("quantity", 1), data["user_id"], data["product_id"])
        )
    else:
        cursor.execute(
            "INSERT INTO cart (user_id,product_id,quantity) VALUES (%s,%s,%s)",
            (data["user_id"], data["product_id"], data.get("quantity", 1))
        )

    db.commit()
    return jsonify({"message": "Cart updated"})


# GET
@app.route("/api/cart/<int:user_id>", methods=["GET"])
def cart_get(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT cart.product_id AS id,products.name,products.price,
        IFNULL(products.image,'') AS image,cart.quantity
        FROM cart JOIN products ON cart.product_id=products.id
        WHERE cart.user_id=%s
    """, (user_id,))

    return jsonify(cursor.fetchall())


# UPDATE
@app.route("/api/cart/update", methods=["PUT"])
def cart_update():
    data = request.json
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "UPDATE cart SET quantity=%s WHERE user_id=%s AND product_id=%s",
        (data["quantity"], data["user_id"], data["product_id"])
    )

    db.commit()
    return jsonify({"message": "Updated"})


# REMOVE
@app.route("/api/cart/remove", methods=["DELETE"])
def cart_remove():
    data = request.json
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM cart WHERE user_id=%s AND product_id=%s",
        (data["user_id"], data["product_id"])
    )

    db.commit()
    return jsonify({"message": "Removed"})


# CLEAR
@app.route("/api/cart/clear/<int:user_id>", methods=["DELETE"])
def cart_clear(user_id):
    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM cart WHERE user_id=%s", (user_id,))
    db.commit()

    return jsonify({"message": "Cart cleared"})


# =========================================
# WISHLIST
# =========================================

# ADD
@app.route("/api/wishlist/add", methods=["POST"])
def wishlist_add():
    data = request.json
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM wishlist WHERE user_id=%s AND product_id=%s",
        (data["user_id"], data["product_id"])
    )

    if cursor.fetchone():
        return jsonify({"message": "Already exists"}), 400

    cursor.execute(
        "INSERT INTO wishlist (user_id,product_id) VALUES (%s,%s)",
        (data["user_id"], data["product_id"])
    )

    db.commit()
    return jsonify({"message": "Added"})


# GET
@app.route("/api/wishlist/<int:user_id>", methods=["GET"])
def wishlist_get(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT wishlist.product_id AS id,products.name,products.price,
        products.category,products.badge,IFNULL(products.image,'') AS image
        FROM wishlist JOIN products ON wishlist.product_id=products.id
        WHERE wishlist.user_id=%s
    """, (user_id,))

    return jsonify(cursor.fetchall())


# REMOVE
@app.route("/api/wishlist/remove", methods=["DELETE"])
def wishlist_remove():
    data = request.json
    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "DELETE FROM wishlist WHERE user_id=%s AND product_id=%s",
        (data["user_id"], data["product_id"])
    )

    db.commit()
    return jsonify({"message": "Removed"})


# =========================================
# ORDERS
# =========================================

# PLACE ORDER
@app.route("/api/orders", methods=["POST"])
def place_order():
    data = request.json
    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO orders
        (order_id,user_id,full_name,email,phone,address,city,zip,payment_method,total_amount)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data["order_id"],
        data.get("user_id"),
        data["full_name"],
        data["email"],
        data["phone"],
        data["address"],
        data["city"],
        data["zip"],
        data.get("payment_method","cod"),
        data["total_amount"]
    ))

    cursor.execute(
        "INSERT INTO payments (order_id,user_id,amount,payment_method,payment_status) VALUES (%s,%s,%s,%s,%s)",
        (data["order_id"], data.get("user_id"), data["total_amount"], data.get("payment_method","cod"), "Success")
    )

    cursor.execute("DELETE FROM cart WHERE user_id=%s", (data.get("user_id"),))
    db.commit()

    return jsonify({"message": "Order placed"})


# ADMIN GET ORDERS
@app.route("/api/orders", methods=["GET"])
def admin_orders():
    if not verify_admin(request):
        return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM orders ORDER BY order_date DESC")
    return jsonify(cursor.fetchall())


# USER ORDERS
@app.route("/api/orders/user/<int:user_id>", methods=["GET"])
def user_orders(user_id):
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT order_id,total_amount,status,order_date
        FROM orders WHERE user_id=%s
    """, (user_id,))

    return jsonify(cursor.fetchall())


# UPDATE STATUS
@app.route("/api/orders/<order_id>/status", methods=["PUT"])
def update_status(order_id):
    if not verify_admin(request):
        return jsonify({"message": "Unauthorized"}), 401

    status = request.json["status"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        "UPDATE orders SET status=%s WHERE order_id=%s",
        (status, order_id)
    )

    db.commit()
    return jsonify({"message": "Updated"})


# DELETE ORDER
@app.route("/api/orders/<order_id>", methods=["DELETE"])
def delete_order(order_id):
    if not verify_admin(request):
        return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM orders WHERE order_id=%s", (order_id,))
    db.commit()

    return jsonify({"message": "Deleted"})


# =========================================
# PAYMENTS (ADMIN)
# =========================================

# GET PAYMENTS
@app.route("/api/payments", methods=["GET"])
def get_payments():
    if not verify_admin(request):
        return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT payments.*, users.name
        FROM payments
        LEFT JOIN users ON payments.user_id = users.id
    """)

    return jsonify(cursor.fetchall())


# DELETE PAYMENT
@app.route("/api/payments/<int:id>", methods=["DELETE"])
def delete_payment(id):
    if not verify_admin(request):
        return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM payments WHERE payment_id=%s", (id,))
    db.commit()

    return jsonify({"message": "Deleted"})
# =========================================
# USERS (ADMIN)
# =========================================

# GET USERS
@app.route("/api/users", methods=["GET"])
def get_users():
    if not verify_admin(request):
        return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, name, email, role, last_login
        FROM users
        ORDER BY id DESC
    """)

    return jsonify(cursor.fetchall())


# DELETE USER
@app.route("/api/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    if not verify_admin(request):
        return jsonify({"message": "Unauthorized"}), 401

    db = get_db()
    cursor = db.cursor()

    cursor.execute("DELETE FROM users WHERE id=%s", (user_id,))
    db.commit()

    return jsonify({"message": "User deleted"})

# =========================================
# START SERVER
# =========================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)