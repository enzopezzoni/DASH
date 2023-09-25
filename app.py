import sqlite3
from flask import Flask, redirect, render_template, request, session
from helpers import usd, to_date
from datetime import date, datetime, timedelta
from functools import wraps

app = Flask(__name__)
connection = sqlite3.connect("dash.db")
db = connection.cursor()
app.jinja_env.filters["usd"] = usd
app.jinja_env.filters["to_date"] = to_date

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
session(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# USER --------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if request.method == "GET":
        return render_template("login.html", error_message = "")
    else:
        if not request.form.get("log_email"):
            return render_template("login.html", error_message = "Please provide email address")
        if not request.form.get("log_password"):
            return render_template("login.html", error_message = "Please provide password")
        log_email = request.form.get("log_email")
        log_password = request.form.get("log_password")
        user = db.execute("SELECT * FROM users WHERE email = ? AND password = ?",
                          log_email, log_password)
        if len(user) == 0:
            return render_template("login.html", error_message = "Please check credentials")
        else:
            session["user_id"] = user[0]["id"]
            return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        users = db.execute("SELECT * FROM users WHERE email = 'enzopezzonii@icloud.com'")
        print(len(users))
        return render_template("register.html", error_message="*Please fill out all the fields")
    else:
        # VERIFICATIONS
        if not request.form.get("fullName"):
            return render_template("register.html", error_message="Please provide your name")
        if not request.form.get("emailAddress"):
            return render_template("register.html", error_message="Please provide your email address")
        users = db.execute("SELECT * FROM users WHERE email = ?", request.form.get("emailAddress"))
        if len(users) > 0 :
            return render_template("register.html", error_message="This user already exist")
        if not request.form.get("org"):
            return render_template("register.html", error_message="Please pick an oganization")
        if not request.form.get("password"):
            return render_template("register.html", error_message="Please enter your password")
        if not request.form.get("confirm_password"):
            return render_template("register.html", error_message="Please confirm your password")
        if request.form.get("password") != request.form.get("confirm_password"):
            return render_template("register.html", error_message="Passwords don't match")
        # INSCRIPTION
        full_name = request.form.get("fullName")
        email_address = request.form.get("emailAddress")
        org = request.form.get("org")
        password = request.form.get("password")
        db.execute("INSERT INTO users (full_name, password, org, email) VALUES(?, ?, ?, ?)",
                   full_name, password, org, email_address)
        return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# HOME PAGE ----------------------------------------------------------

@app.route("/")
@login_required
def index():
    user_fullName = db.execute("SELECT * FROM users WHERE id = ?", session['user_id'])[0]['full_name'].upper()
    return render_template("index.html", user_fullName = user_fullName)


# CONTRACT ----------------------------------------------------------

@app.route("/contracts")
@login_required
def contracts():
    user_orga = db.execute("SELECT * FROM users WHERE id = ?", session['user_id'])[0]['org']
    try:
        search = request.args['search']
        contracts = db.execute("SELECT * FROM contracts WHERE orga = '{user_orga}' AND name LIKE '%{s}%' ORDER BY name ASC".format(user_orga=user_orga, s=search))
        return render_template("contracts.html", contracts=contracts, search=search, user_orga=user_orga)
    except:
        contracts = db.execute("SELECT * FROM contracts WHERE orga = ? ORDER BY name ASC", user_orga)
        return render_template("contracts.html", contracts=contracts, user_orga=user_orga)


@app.route("/newcontract", methods=["GET", "POST"])
@login_required
def new():
    info_message = "*Please fill out all fields"
    error_message = ""
    vendor_list = db.execute("SELECT legal_name FROM vendors")
    if request.method == "GET":
        return render_template("newContract.html", vendor_list=vendor_list, error_message=error_message)
    else:
        user_orga = db.execute("SELECT * FROM users WHERE id = ?", session['user_id'])[0]['org']
        number = request.form.get("number")
        if len(db.execute("SELECT * FROM contracts WHERE number = ?", number)) > 0:
            return render_template("newContract.html", vendor_list=vendor_list, error_message="Contract number already exists", info_message=info_message )
        else:
            name = request.form.get("name")
            vendor = request.form.get("vendor")
            value = request.form.get("value")
            start = request.form.get("start")
            end = request.form.get("end")
            sollicitation = request.form.get("sollicitation")
            if not name or not vendor or not value or not start or not end or not sollicitation:
               return render_template("newContract.html", vendor_list=vendor_list, error_message="", info_message=info_message)
            else:
                db.execute("INSERT INTO contracts (number, name, vendor, start, end, value, bid_sollicitation, orga, owner) VALUES (?,?,?,?,?,?,?,?,?)",
                        number, name, vendor, start, end, value, sollicitation, user_orga, session['user_id'])
                return redirect("/contracts")


@app.route("/contracts/<number>", methods=["GET"])
@login_required
def edit(number):
    contract = db.execute("SELECT * FROM contracts WHERE number = ?", number)[0]
    vendor_list = db.execute("SELECT legal_name FROM vendors")
    owner = db.execute("SELECT * FROM users WHERE id = ?", contract['owner'])[0]
    return render_template("editContract.html", contract=contract, owner=owner, vendor_list=vendor_list)


@app.route("/contract/delete/<number>", methods=["GET"])
@login_required
def delete(number):
    db.execute("DELETE FROM contracts WHERE number=?", number)
    return redirect("/contracts")


@app.route("/contract/update/<number>", methods=["POST"])
@login_required
def update(number):
    new_number = request.form.get("number")
    name = request.form.get("name")
    vendor = request.form.get("vendor")
    value = request.form.get("value")
    start = request.form.get("start")
    end = request.form.get("end")
    sollicitation = request.form.get("sollicitation")
    db.execute("UPDATE contracts SET number=?, name=?, vendor=?, start=?, end=?, value=?, bid_sollicitation=? WHERE number=?",
               new_number,name,vendor,start,end,value,sollicitation,number)
    return redirect("/contracts")


# VENDORS -----------------------------------------------------------

@app.route("/vendors")
@login_required
def vendors():
    vendors = db.execute("SELECT * FROM vendors ORDER BY legal_name ASC")
    return render_template("vendors.html", vendors=vendors)


@app.route("/newvendor", methods=["POST"])
@login_required
def NewVendor():
    legalName = request.form.get("legalName")
    city = request.form.get("city")
    country = request.form.get("country")
    db.execute("INSERT INTO vendors (legal_name, city, country) VALUES(?,?,?)", legalName, city, country)
    return redirect("/vendors")


@app.route("/vendor/<id>", methods=["GET", "POST"])
@login_required
def editVendor(id):
    if request.method == "GET":
        vendor_selected = db.execute("SELECT * FROM vendors WHERE id = ?", id)[0]
        return render_template("editVendor.html", vendor_selected=vendor_selected)
    else:
        legal_name = request.form.get("name")
        city = request.form.get("city")
        country = request.form.get("country")
        db.execute("UPDATE vendors SET legal_name=?, city=?, country=? WHERE id=?", legal_name, city, country, id)
        return redirect("/vendors")


@app.route("/vendor/delete/<id>", methods=["GET"])
@login_required
def deleteVendor(id):
    db.execute("DELETE from vendors WHERE id=?", id)
    return redirect("/vendors")


# TRACKER -------------------------------------------------------------------

@app.route("/tracker")
@login_required
def tracker():
    user_orga = db.execute("SELECT * FROM users WHERE id = ?", session['user_id'])[0]['org']
    today = datetime.now()
    expired = db.execute("SELECT * FROM contracts WHERE end < ? AND orga = ? ORDER BY end DESC", date.today(), user_orga)
    expiring = db.execute("SELECT * FROM contracts WHERE end > ? AND end < ?  AND orga = ? ORDER BY end ASC", date.today(), (date.today() + timedelta(days=30)), user_orga)
    total_contract = db.execute("SELECT DISTINCT COUNT(number) AS count FROM contracts WHERE orga = ? ", user_orga)[0]
    total_expired = db.execute("SELECT DISTINCT COUNT(number) AS count FROM contracts WHERE end < ?  AND orga = ?", date.today(), user_orga)[0]
    total_expiring = db.execute("SELECT DISTINCT COUNT(number) AS count FROM contracts WHERE end > ? AND end < ? AND orga = ?", date.today(), (date.today() + timedelta(days=30)), user_orga)[0]
    return render_template("tracker.html",
                           total_contract=total_contract, total_expired=total_expired, total_expiring=total_expiring,
                           expired = expired, expiring=expiring, today=today)
