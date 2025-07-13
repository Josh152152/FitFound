import os
import re
import numpy as np
from flask import Blueprint, request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from app.sheets import read_all, append_row, find_row_by_column, update_row_by_column
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import openai

main_bp = Blueprint('main', __name__)
import requests

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Geolocator setup using Geopy
geolocator = Nominatim(user_agent="fitfound-app")

# Cloudflare Turnstile secret for form validation
CLOUDFLARE_TURNSTILE_SECRET = "0x4AAAAAABk1sBpwSFeoJt39y_i-B5lqiNo"

# Function to verify Cloudflare Turnstile token
def verify_turnstile(token):
    """Verify Cloudflare Turnstile token (returns True if valid)."""
    import requests
    if not token:
        return False
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    data = {
        "secret": CLOUDFLARE_TURNSTILE_SECRET,
        "response": token,
        "remoteip": request.remote_addr
    }
    try:
        resp = requests.post(url, data=data, timeout=5)
        result = resp.json()
        return result.get("success", False)
    except Exception as e:
        print("[ERROR] Turnstile validation failed:", e)
        return False

# Function to get OpenAI embedding for text
def get_openai_embedding(text):
    if not text or not text.strip():
        return None
    response = openai.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return response.data[0].embedding

# Function to extract numbers from text
def extract_number(text):
    """Extract first number found in text, fallback to None."""
    match = re.search(r'(\d+(?:[.,]\d+)?)', str(text))
    if match:
        return float(match.group(1).replace(',', '').replace(' ', ''))
    return None

# Function to get coordinates for a location
def get_coords(location):
    try:
        loc = geolocator.geocode(location, timeout=10)
        return (loc.latitude, loc.longitude) if loc else None
    except Exception:
        return None

# Function to calculate text similarity using OpenAI embeddings
def text_similarity(a, b):
    emb_a = get_openai_embedding(a)
    emb_b = get_openai_embedding(b)
    if emb_a is None or emb_b is None:
        return 0.0
    emb_a = np.array(emb_a)
    emb_b = np.array(emb_b)
    sim = np.dot(emb_a, emb_b) / (np.linalg.norm(emb_a) * np.linalg.norm(emb_b))
    return float(sim)

main_bp = Blueprint('main', __name__)

# Route for testing if the API is running
@main_bp.route("/")
def index():
    return "FitFound: Talent Matching App (OpenAI embeddings) is running!"
@main_bp.route("/test")
def test():
    return jsonify({"message": "API is up and running."})

# ---------------------- EMPLOYER JOB ROUTES ----------------------------

@main_bp.route("/employer/jobs", methods=["GET"])
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

@main_bp.route("/employer/jobs/create", methods=["POST"])
def create_job():
    data = request.form if not request.is_json else request.get_json(force=True)
    job_overview = data.get("JobOverview") or data.get("Job Description")
    job_location = data.get("JobLocation") or data.get("Job location")
    required = ["Email", "Name", "Job Creation Date", "Compensation"]
    missing = [k for k in required if k not in data or not data[k]]
    if not job_overview:
        missing.append("JobOverview/Job Description")
    if not job_location:
        missing.append("JobLocation/Job location")
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    latitude, longitude = "", ""
    if data.get("Latitude") and data.get("Longitude"):
        latitude = data.get("Latitude")
        longitude = data.get("Longitude")
    else:
        coords = get_coords(job_location)
        if coords:
            latitude, longitude = coords

    try:
        append_row("Jobs2", {
            "Email": data["Email"],
            "Name": data["Name"],
            "Job Creation Date": data["Job Creation Date"],
            "JobOverview": job_overview,
            "JobLocation": job_location,
            "Compensation": data["Compensation"],
            "Nber of applicants": data.get("Nber of applicants", "0"),
            "Archived?": data.get("Archived?", ""),
            "Latitude": latitude,
            "Longitude": longitude
        })
        return jsonify({"message": "Job created!"})
    except Exception as e:
        return jsonify({"error": "Failed to update Google Sheet: " + str(e)}), 500

@main_bp.route("/employer/jobs/archive", methods=["POST"])
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

# ---------------------- CANDIDATE MATCHING ROUTE -----------------------

@main_bp.route("/employer/match-candidates", methods=["POST"])
def match_candidates():
    job = request.get_json(force=True)
    job_overview = job.get("JobOverview") or job.get("Job Description")
    job_location = job.get("JobLocation") or job.get("Job location")
    missing = []
    if not job.get("Name"): missing.append("Name")
    if not job_overview: missing.append("JobOverview/Job Description")
    if not job_location: missing.append("JobLocation/Job location")
    if missing:
        return jsonify({"error": f"Missing required job fields: {', '.join(missing)}"}), 400

    job_embedding = get_openai_embedding(job_overview)
    job_comp = extract_number(job.get("Compensation", ""))

    try:
        job_lat = float(job.get("Latitude", ""))
        job_lon = float(job.get("Longitude", ""))
        job_coords = (job_lat, job_lon)
    except (TypeError, ValueError):
        job_coords = get_coords(job_location)

    candidates = read_all("Candidates2")
    results = []
    for cand in candidates:
        cand_location = str(cand.get("Location", "")).strip().lower()
        job_location_lc = str(job_location or "").strip().lower()

        if cand_location == "remote" and "remote" not in job_location_lc:
            continue

        sim = 0.0
        if cand.get("Summary"):
            cand_embedding = get_openai_embedding(cand["Summary"])
            if cand_embedding is not None and job_embedding is not None:
                sim = float(np.dot(cand_embedding, job_embedding) / (np.linalg.norm(cand_embedding) * np.linalg.norm(job_embedding)))

        sal = extract_number(cand.get("Salary", ""))
        comp_bonus = 0.0
        if sal and job_comp:
            if job_comp >= sal:
                comp_bonus = 0.05  # Small boost if job >= candidate expectation

        skip_distance = (cand_location == "remote") or ("remote" in job_location_lc)
        dist = 0.0
        if not skip_distance:
            default_radius = 30.0  # km
            radius = extract_number(cand.get("Radius", "")) or default_radius
            try:
                cand_lat = float(cand.get("Latitude", ""))
                cand_lon = float(cand.get("Longitude", ""))
                cand_coords = (cand_lat, cand_lon)
            except (TypeError, ValueError):
                cand_coords = get_coords(cand.get("Location", ""))
            if not (job_coords and cand_coords):
                continue
            dist = geodesic(job_coords, cand_coords).km
            if dist > radius:
                continue

        total_score = sim + comp_bonus
        results.append({
            "candidate": cand,
            "score": total_score,
            "distance_km": round(dist, 1),
            "similarity": round(sim, 2),
            "comp_bonus": comp_bonus,
        })

    results = sorted(results, key=lambda x: x["score"], reverse=True)
    results = results[:10]
    return jsonify(results)

# ---------------------- COMPANY PROFILE ROUTE --------------------------

@main_bp.route("/company/create", methods=["POST"])
def create_company():
    data = request.form if not request.is_json else request.get_json(force=True)
    required = ["Email", "companyName", "companyOverview", "companyLocation"]
    missing = [k for k in required if k not in data or not data[k]]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        append_row("Company2", {
            "Email": data["Email"],
            "Company Name": data["companyName"],
            "Company Overview": data["companyOverview"],
            "Company Location": data["companyLocation"]
        })
        return jsonify({"message": "Company profile created!"})
    except Exception as e:
        return jsonify({"error": "Failed to update Google Sheet: " + str(e)}), 500

# ---------------------- CANDIDATE/CREDENTIAL ROUTES ---------------------

@main_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    data = request.get_json(force=True) if request.is_json else request.form
    required_fields = ("Email", "Name", "Password", "Type")
    missing_fields = [k for k in required_fields if k not in data or not data[k]]
    if missing_fields:
        return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

    # Turnstile verification
    cf_token = data.get("cf-turnstile-response")
    if not verify_turnstile(cf_token):
        return jsonify({"error": "Cloudflare verification failed. Please try again."}), 400

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

@main_bp.route("/login", methods=["GET", "POST"])
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

    user_type_raw = user.get("Type", "").strip().capitalize()
    return jsonify({
        "message": "Login successful!",
        "type": user_type_raw or "Candidate",
        "email": user.get("Email"),
        "name": user.get("Name")
    })

@main_bp.route("/user", methods=["GET"])
def get_user():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email required"}), 400
    user = find_row_by_column("Users2", "Email", email)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"name": user.get("Name", "")})

@main_bp.route("/candidate/profile", methods=["POST"])
def create_candidate_profile():
    data = request.get_json(force=True) if request.is_json else dict(request.form)
    required_fields = ("Email", "Name", "Location", "Radius", "Summary")
    if not all(k in data and data[k] for k in required_fields):
        return jsonify({"error": "Missing fields"}), 400

    latitude, longitude = "", ""
    if data.get("Latitude") and data.get("Longitude"):
        latitude = data.get("Latitude")
        longitude = data.get("Longitude")
    else:
        coords = get_coords(data["Location"])
        if coords:
            latitude, longitude = coords

    append_row("Candidates2", {
        "Email": data["Email"],
        "Name": data["Name"],
        "Location": data["Location"],
        "Radius": str(data["Radius"]),
        "Summary": data["Summary"],
        "Salary": data.get("Salary", ""),
        "Latitude": latitude,
        "Longitude": longitude
    })
    return jsonify({"message": "Profile created!"})

@main_bp.route("/test")
def test():
    return jsonify({"message": "API is up and running."})
