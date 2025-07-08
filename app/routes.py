import os
from flask import request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from app.sheets import read_all, append_row, find_row_by_column
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import numpy as np
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")
geolocator = Nominatim(user_agent="fitfound-app")

def get_openai_embedding(text):
    if not text or not text.strip():
        return None
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

def text_similarity(a, b):
    emb_a = get_openai_embedding(a)
    emb_b = get_openai_embedding(b)
    if emb_a is None or emb_b is None:
        return 0.0
    emb_a = np.array(emb_a)
    emb_b = np.array(emb_b)
    sim = np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b))
    return float(sim)

@app.route("/")
def index():
    return "FitFound: Talent Matching App (OpenAI embeddings) is running!"

# Signup route (accepts form data or JSON)
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    # Accept both JSON and form data
    if request.is_json:
        data = request.get_json()
        print("Received JSON data:", data)
    else:
        data = request.form
        print("Received FORM data:", data.to_dict())

    required_fields = ("Email", "Name", "Password", "Type")
    missing_fields = [k for k in required_fields if k not in data or not data[k]]
    if missing_fields:
        print("Missing fields:", missing_fields)
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

    if find_row_by_column("Users2", "Email", data["Email"]):
        return jsonify({"error": "Email already exists"}), 400

    hashed_password = generate_password_hash(data["Password"])

    append_row("Users2", {
        "Email": data["Email"],
        "Name": data["Name"],
        "Password": hashed_password,
        "Type": data["Type"]
    })
    return jsonify({"message": "Signup successful!"})

# Login route (accepts form data or JSON)
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    if request.is_json:
        data = request.get_json()
        print("Received JSON data:", data)
    else:
        data = request.form
        print("Received FORM data:", data.to_dict())

    required_fields = ("Email", "Password")
    missing_fields = [k for k in required_fields if k not in data or not data[k]]
    if missing_fields:
        print("Missing fields:", missing_fields)
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

    user = find_row_by_column("Users2", "Email", data["Email"])
    if not user or not check_password_hash(user.get("Password", ""), data["Password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful!"})

# Endpoint to get user info by email (for greeting on dashboard)
@app.route("/user", methods=["GET"])
def get_user():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email required"}), 400
    user = find_row_by_column("Users2", "Email", email)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"name": user.get("Name", "")})

# Candidate profile creation: updated to support form and JSON submissions robustly!
@app.route("/candidate/profile", methods=["POST"])
def create_candidate_profile():
    # Accept both JSON and form submissions
    if request.is_json:
        data = request.get_json()
    else:
        data = dict(request.form)
    required_fields = ("Email", "Name", "Location", "Radius", "Summary")
    if not all(k in data and data[k] for k in required_fields):
        return jsonify({"error": "Missing fields"}), 400
    append_row("Candidates2", {
        "Email": data["Email"],
        "Name": data["Name"],
        "Location": data["Location"],
        "Radius": str(data["Radius"]),
        "Summary": data["Summary"],
        "Salary": data.get("Salary", "")
    })
    return jsonify({"message": "Profile created!"})

# The rest of your routes remain the same...
# (Post job, geo calculations, match candidates, etc.)
