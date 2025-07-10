import os
from flask import request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from app.sheets import read_all, append_row, find_row_by_column, update_row_by_column
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

# ---------------------- EMPLOYER JOB ROUTES ----------------------------

@app.route("/employer/jobs", methods=["GET"])
def employer_jobs():
    email = request.args.get("email")
    archived = request.args.get("archived", "false").lower() == "true"
    if not email:
        return jsonify({"error": "Missing employer email"}), 400

    jobs = read_all("Jobs2")
    filtered = []
    for job in jobs:
        if job.get("Email", "").strip().lower() != email.strip().lower():
            continue
        is_archived = str(job.get("Archived?", "")).strip().lower() in ["yes", "y", "true", "1"]
        if archived and is_archived:
            filtered.append(job)
        elif not archived and not is_archived:
            filtered.append(job)
    filtered.sort(key=lambda x: x.get("Job Creation Date", ""), reverse=True)
    return jsonify(filtered)

@app.route("/employer/jobs/create", methods=["POST"])
def create_job():
    data = request.form if not request.is_json else request.get_json(force=True)
    required = [
        "Email", "Name", "Company Location", "Job Creation Date",
        "Job Description", "Job location", "Compensation"
    ]
    missing = [k for k in required if k not in data or not data[k]]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    append_row("Jobs2", {
        "Email": data["Email"],
        "Name": data["Name"],
        "Company Location": data["Company Location"],
        "Job Creation Date": data["Job Creation Date"],
        "Job Description": data["Job Description"],
        "Job location": data["Job location"],
        "Compensation": data["Compensation"],
        "Nber of applicants": data.get("Nber of applicants", "0"),
        "Archived?": data.get("Archived?", "")
    })
    return jsonify({"message": "Job created!"})

@app.route("/employer/jobs/archive", methods=["POST"])
def archive_job():
    data = request.get_json(force=True)
    email = data.get("email")
    name = data.get("name")
    job_creation_date = data.get("job_creation_date")
    archive = data.get("archive", True)
    if not (email and name and job_creation_date):
        return jsonify({"error": "Missing parameters"}), 400
    jobs = read_all("Jobs2")
    found = False
    for idx, job in enumerate(jobs):
        if (
            job.get("Email", "").strip().lower() == email.strip().lower() and
            job.get("Name", "").strip() == name.strip() and
            job.get("Job Creation Date", "").strip() == job_creation_date.strip()
        ):
            found = True
            update_row_by_column("Jobs2", "Job Creation Date", job_creation_date, {"Archived?": "Yes" if archive else ""})
            break
    if found:
        return jsonify({"message": "Job archive status updated."})
    else:
        return jsonify({"error": "Job not found."}), 404

# ---------------------- COMPANY PROFILE ROUTE --------------------------

@app.route("/company/create", methods=["POST"])
def create_company():
    data = request.form if not request.is_json else request.get_json(force=True)
    required = ["Email", "companyName", "companyOverview", "companyLocation"]
    missing = [k for k in required if k not in data or not data[k]]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    append_row("Company2", {
        "Email": data["Email"],
        "Company Name": data["companyName"],
        "Company Overview": data["companyOverview"],
        "Company Location": data["companyLocation"]
    })
    return jsonify({"message": "Company profile created!"})

# ---------------------- CANDIDATE/CREDENTIAL ROUTES ---------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    data = request.get_json(force=True) if request.is_json else request.form
    required_fields = ("Email", "Name", "Password", "Type")
    missing_fields = [k for k in required_fields if k not in data or not data[k]]
    if missing_fields:
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

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    data = request.get_json(force=True) if request.is_json else request.form
    required_fields = ("Email", "Password")
    missing_fields = [k for k in required_fields if k not in data or not data[k]]
    if missing_fields:
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400
    user = find_row_by_column("Users2", "Email", data["Email"])
    if not user or not check_password_hash(user.get("Password", ""), data["Password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    user_type_raw = None
    for k in user:
        if k.strip().lower() == "type":
            user_type_raw = user[k]
            break
    user_type = str(user_type_raw).strip().capitalize() if user_type_raw else "Candidate"
    if user_type not in ("Employer", "Candidate"):
        user_type = "Candidate"

    return jsonify({
        "message": "Login successful!",
        "type": user_type,
        "email": user.get("Email"),
        "name": user.get("Name")
    })

@app.route("/user", methods=["GET"])
def get_user():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email required"}), 400
    user = find_row_by_column("Users2", "Email", email)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"name": user.get("Name", "")})

@app.route("/candidate/profile", methods=["POST"])
def create_candidate_profile():
    data = request.get_json(force=True) if request.is_json else dict(request.form)
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

@app.route("/test")
def test():
    return jsonify({"message": "API is up and running."})
