from flask import Flask, render_template, redirect, url_for, request, session, jsonify
from functools import wraps
import sqlite3
from dotenv import load_dotenv
import os

# ============ SECRET KEY CONFIGURATION (if you don't set this, app while crash)============
# 1. Create a .env file in the project root directory
# 2. Add this line to .env:
#    FLASK_SECRET_KEY='your-super-secret-key-here'
# 3. Add this after creating the Flask app:
#    load_dotenv()
#    app.secret_key = os.environ.get("FLASK_SECRET_KEY")
# =================================================

app = Flask(__name__)

# Check if secret key is set
if app.secret_key:
    print("FLASK_SECRET_KEY set.")
else:
    raise ValueError("FLASK_SECRET_KEY environment variable is not set.")

def db_init():
    """Initialize database"""
    con = None
    try:
        con = sqlite3.connect("app.db")
        con.executescript('''
        CREATE TABLE IF NOT EXISTS Users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS Products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            img_url TEXT,
            stock INTEGER DEFAULT 0,
            info TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS Cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES Users(email) ON DELETE CASCADE
        );
        
        CREATE TABLE IF NOT EXISTS CartItems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cart_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (cart_id) REFERENCES Cart(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES Products(id) ON DELETE CASCADE,
            UNIQUE(cart_id, product_id)
        );
        ''')
        
        con.commit()
        print("Database Initialized successfully.")
        return True
        
    except sqlite3.Error as e:
        print(f"Database Initialization Error: {e}")
        return False
    finally:
        if con:
            con.close()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

class Users:
    def __init__(self, email, password):
        self.email = email
        self.password = password
    
    def login(self):
        con = None
        try:
            con = sqlite3.connect("app.db")
            cur = con.cursor()

            cur.execute("SELECT 1 FROM Users WHERE email = ? LIMIT 1", (self.email,))
            check_user_result = cur.fetchone()
            
            user_exists = check_user_result is not None
            
            if not user_exists:
                cur.execute("INSERT INTO Users (email, password) VALUES(?, ?)", (self.email, self.password))
                con.commit()
                print("New User -> {}".format(self.email))
                return 0
            else:
                cur.execute("SELECT password FROM Users WHERE email = ?", (self.email,))
                user_verify_result = cur.fetchone()
                if user_verify_result is not None and user_verify_result[0] == self.password:
                    print("New Login -> {}".format(self.email))
                    return 1
                else:
                    print("Failed Login -> {}".format(self.email))
                    return 2
            
        except sqlite3.IntegrityError:
            print("INTEGRITY ERROR: User already exists?")
            return 3
        except sqlite3.Error as e:
            print("DATABASE ERROR: {}".format(e))
            return 3
        except Exception as e:
            print("UNKNOWN ERROR: {}".format(e))
            return 3
        finally:
            if con:
                con.close()

class ShoppingCart:
    def __init__(self, user_email):
        self.user_email = user_email
        self.cart_id = self._get_or_create_cart()

    def _get_or_create_cart(self):
        con = sqlite3.connect("app.db")
        cur = con.cursor()
        
        try:
            cur.execute("SELECT id FROM Cart WHERE user_email = ?", (self.user_email,))
            cart = cur.fetchone()
            
            if cart:
                return cart[0]
            else:
                cur.execute("INSERT INTO Cart (user_email) VALUES(?)", (self.user_email,))
                con.commit()
                return cur.lastrowid
        finally:
            con.close()
    
    def add_item(self, product_id, quantity=1):
        con = None
        try:
            con = sqlite3.connect("app.db")
            cur = con.cursor()
            
            product = cur.execute("SELECT stock FROM Products WHERE id = ?", (product_id,)).fetchone()
            
            if not product:
                return False, "Product not found."
            
            if product[0] < quantity:
                return False, "Not enough stock"
            
            existing = cur.execute(
                "SELECT id, quantity FROM CartItems WHERE cart_id = ? AND product_id = ?",
                (self.cart_id, product_id)
            ).fetchone()
            
            if existing:
                cur.execute(
                    "UPDATE CartItems SET quantity = quantity + ? WHERE id = ?",
                    (quantity, existing[0])
                )
            else:
                cur.execute(
                    "INSERT INTO CartItems (cart_id, product_id, quantity) VALUES (?, ?, ?)",
                    (self.cart_id, product_id, quantity)
                )
            
            cur.execute(
                "UPDATE Cart SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (self.cart_id,)
            )
            
            con.commit()
            return True, "Item added to cart."
            
        except sqlite3.Error as e:
            return False, f"DATABASE ERROR: {e}"
        finally:
            if con:
                con.close()
    
    def remove_item(self, product_id):
        con = None
        try:
            con = sqlite3.connect("app.db")
            cur = con.cursor()
            
            cur.execute(
                "DELETE FROM CartItems WHERE cart_id = ? AND product_id = ?",
                (self.cart_id, product_id)
            )
            con.commit()
            return True, "Item removed"
            
        except sqlite3.Error as e:
            return False, f"DATABASE ERROR: {e}"
        finally:
            if con:
                con.close()
    
    def update_quantity(self, product_id, quantity):
        if quantity <= 0:
            return self.remove_item(product_id)
        
        con = None
        try:
            con = sqlite3.connect("app.db")
            cur = con.cursor()
            
            cur.execute(
                "UPDATE CartItems SET quantity = ? WHERE cart_id = ? AND product_id = ?",
                (quantity, self.cart_id, product_id)
            )
            con.commit()
            return True, "Quantity Updated."
            
        except sqlite3.Error as e:
            return False, f"DATABASE ERROR: {e}"
        finally:
            if con:
                con.close()
    
    def get_cart_items(self):
        con = None
        try:
            con = sqlite3.connect("app.db")
            cur = con.cursor()
            
            items = cur.execute('''
                SELECT
                    ci.id,
                    ci.quantity,
                    p.id as product_id,
                    p.name,
                    p.price,
                    p.description,
                    p.img_url,
                    (p.price * ci.quantity) as subtotal
                FROM CartItems ci
                JOIN Products p ON ci.product_id = p.id
                WHERE ci.cart_id = ?
            ''', (self.cart_id,)).fetchall()
            
            return items
            
        except sqlite3.Error as e:
            print(f"Error getting cart items: {e}")
            return []
        finally:
            if con:
                con.close()
    
    def get_cart_total(self):
        con = None
        try:
            con = sqlite3.connect("app.db")
            cur = con.cursor()
            
            total = cur.execute("""
                SELECT SUM(p.price * ci.quantity) as total
                FROM CartItems ci
                JOIN Products p ON ci.product_id = p.id
                WHERE ci.cart_id = ?
            """, (self.cart_id,)).fetchone()
            
            return total[0] if total and total[0] else 0
            
        except sqlite3.Error as e:
            print(f"Error getting cart total: {e}")
            return 0
        finally:
            if con:
                con.close()
    
    def get_cart_count(self):
        con = None
        try:
            con = sqlite3.connect("app.db")
            cur = con.cursor()
            
            count = cur.execute("""
                SELECT SUM(quantity) as count
                FROM CartItems
                WHERE cart_id = ?
            """, (self.cart_id,)).fetchone()
            
            return count[0] if count and count[0] else 0
            
        except sqlite3.Error as e:
            print(f"Error getting cart count: {e}")
            return 0
        finally:
            if con:
                con.close()
    
    def clear_cart(self):
        con = None
        try:
            con = sqlite3.connect("app.db")
            cur = con.cursor()
            
            cur.execute("DELETE FROM CartItems WHERE cart_id = ?", (self.cart_id,))
            con.commit()
            return True, "Cart Cleared."
            
        except sqlite3.Error as e:
            return False, f"DATABASE ERROR: {e}"
        finally:
            if con:
                con.close()


class Modify:
    @staticmethod
    def to_persian_number_filter(number):
        persian_digits = "۰۱۲۳۴۵۶۷۸۹"
        english_digits = '0123456789'
        trans = str.maketrans(english_digits, persian_digits)
        return str(number).translate(trans)

@app.route("/")
def home():
    con = sqlite3.connect("app.db")
    cur = con.cursor()
    products = cur.execute("SELECT * FROM Products").fetchall()
    con.close()
    return render_template('home.html', products=products)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if not email or not password:
            return "Email and password required", 400
        
        user = Users(email, password)
        user_login = user.login()
        
        if user_login == 0 or user_login == 1:
            session["user_id"] = email
            session["logged_in"] = True
            session.permanent = True
            return redirect(url_for("dashboard"))
        
        elif user_login == 2:
            return redirect(url_for("login"))
        else:
            return "Database error", 500
        
    return render_template("login.html")

@app.route("/dashboard")
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/delete-account", methods=["POST"])
@login_required
def delete_account():
    con = None
    try:
        con = sqlite3.connect("app.db")
        cur = con.cursor()
        
        cur.execute("DELETE FROM Users WHERE email = ?", (session['user_id'],))
        con.commit()
        
        session.clear()
        return redirect(url_for("home"))
        
    except sqlite3.Error as e:
        print(f"Database Error: {e}")
        return redirect(url_for("dashboard"))
    finally:
        if con:
            con.close()

@app.route("/cart")
@login_required
def view_cart():
    cart = ShoppingCart(session['user_id'])
    items = cart.get_cart_items()
    total = cart.get_cart_total()
    items_count = cart.get_cart_count()
    
    return render_template('cart.html', items=items, total=total, items_count=items_count)

@app.route("/cart/add/<int:product_id>", methods=["POST"])
@login_required
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    cart = ShoppingCart(session['user_id'])
    cart.add_item(product_id, quantity)
    return redirect(url_for('view_cart'))

@app.route("/cart/remove/<int:product_id>", methods=["POST"])
@login_required
def remove_from_cart(product_id):
    cart = ShoppingCart(session['user_id'])
    cart.remove_item(product_id)
    return redirect(url_for("view_cart"))

@app.route('/cart/clear', methods=["POST"])
@login_required
def clear_cart():
    cart = ShoppingCart(session['user_id'])
    cart.clear_cart()
    return redirect(url_for("view_cart"))

@app.route('/cart/count')
@login_required
def cart_count():
    cart = ShoppingCart(session['user_id'])
    count = cart.get_cart_count()
    return jsonify({"count": count})

@app.template_filter('price')
def price(price):
    formatted = f"{int(price):,}"
    return Modify.to_persian_number_filter(formatted)

@app.route("/products")
def products():
    con = sqlite3.connect("app.db")
    cur = con.cursor()
    products = cur.execute("SELECT * FROM Products").fetchall()
    con.close()
    return render_template('products.html', products=products)

@app.route("/products/product/<int:product_id>")
def product(product_id):
    con = sqlite3.connect("app.db")
    cur = con.cursor()
    
    product = cur.execute("SELECT * FROM Products WHERE id = ?", (product_id,)).fetchone()
    
    if not product:
        con.close()
        return redirect(url_for("products"))
    
    in_cart = False
    cart_quantity = 1
    
    if 'user_id' in session:
        cart_item = cur.execute("""
            SELECT ci.quantity FROM CartItems ci
            JOIN Cart c ON ci.cart_id = c.id
            WHERE c.user_email = ? AND ci.product_id = ?
        """, (session['user_id'], product_id)).fetchone()
        
        if cart_item:
            in_cart = True
            cart_quantity = cart_item[0]
    
    con.close()
    
    return render_template("product.html", 
                         product=product, 
                         in_cart=in_cart,
                         cart_quantity=cart_quantity)

@app.route('/contact')
def contact():
    return render_template("contact.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.errorhandler(500)
def internal_server_error(error):
    return render_template("500.html"), 500

@app.errorhandler(403)
def forbidden(error):
    return render_template("403.html"), 403

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

if __name__ == "__main__":
    db_init()
    app.run(debug=False, use_reloader=False)
