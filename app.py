from flask import Flask, render_template, request, redirect, session
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.secret_key = "inventory_secret_key"

# -----------------------------
# MongoDB Connection
# -----------------------------

client = MongoClient(os.getenv("MONGO_URI"))

db = client["inventory_db"]

users = db["users"]
products = db["products"]
customers = db["customers"]
sales = db["sales"]


# -----------------------------
# LOGIN
# -----------------------------

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        user = users.find_one({
            "username": username
        })

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["username"] = username

            return redirect("/dashboard")

        return "Invalid username or password"

    return render_template("login.html")


# -----------------------------
# LOGOUT
# -----------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# -----------------------------
# DASHBOARD
# -----------------------------

@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect("/")

    total_products = products.count_documents({})
    total_customers = customers.count_documents({})
    total_sales = sales.count_documents({})

    # Total sales amount
    result = sales.aggregate([
        {
            "$group": {
                "_id": None,
                "total": {
                    "$sum": "$total"
                }
            }
        }
    ])

    result = list(result)

    total_revenue = result[0]["total"] if result else 0

    # Low stock
    low_stock = products.count_documents({
        "$expr": {
            "$lte": [
                "$quantity",
                "$reorder_level"
            ]
        }
    })

    return render_template(
        "dashboard.html",
        total_products=total_products,
        total_customers=total_customers,
        total_sales=total_sales,
        total_revenue=total_revenue,
        low_stock=low_stock
    )


# -----------------------------
# PRODUCTS
# -----------------------------

@app.route("/products")
def product_list():

    if "username" not in session:
        return redirect("/")

    search = request.args.get("search", "")

    if search:

        product_data = products.find({
            "name": {
                "$regex": search,
                "$options": "i"
            }
        })

    else:

        product_data = products.find()

    return render_template(
        "products.html",
        products=product_data,
        search=search
    )


# -----------------------------
# ADD PRODUCT
# -----------------------------

@app.route("/products/add", methods=["GET", "POST"])
def add_product():

    if "username" not in session:
        return redirect("/")

    if request.method == "POST":

        product = {

            "name": request.form["name"],

            "category": request.form["category"],

            "price": float(
                request.form["price"]
            ),

            "quantity": int(
                request.form["quantity"]
            ),

            "reorder_level": int(
                request.form["reorder_level"]
            ),

            "supplier": request.form["supplier"],

            "created_at": datetime.now()

        }

        products.insert_one(product)

        return redirect("/products")

    return render_template("add_product.html")


# -----------------------------
# EDIT PRODUCT
# -----------------------------

@app.route("/products/edit/<id>", methods=["GET", "POST"])
def edit_product(id):

    if "username" not in session:
        return redirect("/")

    product = products.find_one({
        "_id": ObjectId(id)
    })

    if request.method == "POST":

        products.update_one(

            {
                "_id": ObjectId(id)
            },

            {
                "$set": {

                    "name": request.form["name"],

                    "category": request.form["category"],

                    "price": float(
                        request.form["price"]
                    ),

                    "quantity": int(
                        request.form["quantity"]
                    ),

                    "reorder_level": int(
                        request.form["reorder_level"]
                    ),

                    "supplier": request.form["supplier"]

                }
            }
        )

        return redirect("/products")

    return render_template(
        "edit_product.html",
        product=product
    )


# -----------------------------
# DELETE PRODUCT
# -----------------------------

@app.route("/products/delete/<id>")
def delete_product(id):

    if "username" not in session:
        return redirect("/")

    products.delete_one({
        "_id": ObjectId(id)
    })

    return redirect("/products")


# -----------------------------
# CUSTOMERS
# -----------------------------

@app.route("/customers")
def customer_list():

    if "username" not in session:
        return redirect("/")

    customer_data = customers.find()

    return render_template(
        "customers.html",
        customers=customer_data
    )


# -----------------------------
# ADD CUSTOMER
# -----------------------------

@app.route("/customers/add", methods=["GET", "POST"])
def add_customer():

    if "username" not in session:
        return redirect("/")

    if request.method == "POST":

        customer = {

            "name": request.form["name"],

            "email": request.form["email"],

            "phone": request.form["phone"],

            "city": request.form["city"],

            "created_at": datetime.now()

        }

        customers.insert_one(customer)

        return redirect("/customers")

    return render_template("add_customer.html")


# -----------------------------
# SALES
# -----------------------------

@app.route("/sales")
def sales_list():

    if "username" not in session:
        return redirect("/")

    sales_data = sales.find().sort(
        "created_at",
        -1
    )

    return render_template(
        "sales.html",
        sales=sales_data
    )


# -----------------------------
# CREATE SALE
# -----------------------------

@app.route("/sales/create", methods=["POST"])
def create_sale():

    if "username" not in session:
        return redirect("/")

    product_id = request.form["product_id"]

    quantity = int(
        request.form["quantity"]
    )

    product = products.find_one({
        "_id": ObjectId(product_id)
    })

    if not product:
        return "Product not found"

    if product["quantity"] < quantity:
        return "Not enough stock"

    total = product["price"] * quantity

    sale = {

        "product": product["name"],

        "quantity": quantity,

        "price": product["price"],

        "total": total,

        "customer": request.form["customer"],

        "created_at": datetime.now()

    }

    sales.insert_one(sale)

    # Reduce stock
    products.update_one(

        {
            "_id": ObjectId(product_id)
        },

        {
            "$inc": {
                "quantity": -quantity
            }
        }
    )

    return redirect("/sales")


# -----------------------------
# CREATE ADMIN USER
# -----------------------------

@app.route("/create-admin")
def create_admin():

    existing = users.find_one({
        "username": "admin"
    })

    if existing:
        return "Admin already exists"

    users.insert_one({

        "username": "admin",

        "password": generate_password_hash(
            "admin123"
        ),

        "role": "admin"

    })

    return "Admin created successfully"


# -----------------------------
# RUN
# -----------------------------

if __name__ == "__main__":

    app.run(
        debug=True
    )