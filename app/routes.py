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

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")

    data = request.json
    if not all(k in data for k in ("Email", "Name", "Password", "Type")):
        return jsonify({"error": "Missing fields"}), 400
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

    data = request.json
    if not all(k in data for k in ("Email", "Password")):
        return jsonify({"error": "Missing fields"}), 400

    user = find_row_by_column("Users2", "Email", data["Email"])
    if not user or not check_password_hash(user.get("Password", ""), data["Password"]):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"message": "Login successful!"})

@app.route("/candidate/profile", methods=["POST"])
def create_candidate_profile():
    data = request.json
    if not all(k in data for k in ("Email", "Name", "Location", "Radius", "Summary")):
        return jsonify({"error": "Missing fields"}), 400
    append_row("Candidates2", {
        "Email": data["Email"],
        "Name": data["Name"],
        "Location": data["Location"],
        "Radius": str(data["Radius"]),
        "Summary": data["Summary"]
    })
    return jsonify({"message": "Profile created!"})

@app.route("/employer/job", methods=["POST"])
def post_job():
    data = request.json
    if not all(k in data for k in ("Email", "Name", "Location", "JobDescription")):
        return jsonify({"error": "Missing fields"}), 400
    append_row("Jobs2", {
        "Email": data["Email"],
        "Name": data["Name"],
        "Location": data["Location"],
        "Job description": data["JobDescription"]
    })
    return jsonify({"message": "Job posted!"})

def get_coordinates(location):
    try:
        loc = geolocator.geocode(location, timeout=10)
        if loc:
            return (loc.latitude, loc.longitude)
    except Exception:
        pass
    return None

def geo_score(candidate_loc, job_loc, candidate_radius):
    c_coords = get_coordinates(candidate_loc)
    j_coords = get_coordinates(job_loc)
    if not c_coords or not j_coords:
        return 0
    dist = geodesic(c_coords, j_coords).km
    try:
        candidate_radius = float(candidate_radius)
    except Exception:
        candidate_radius = 0
    return 1.0 if dist <= candidate_radius else max(0, 1 - dist/100)

@app.route("/employer/match_candidates/<int:job_id>", methods=["GET"])
def match_candidates(job_id):
    jobs = read_all("Jobs2")
    candidates = read_all("Candidates2")
    if job_id < 0 or job_id >= len(jobs):
        return jsonify({"error": "Job not found"}), 404
    job = jobs[job_id]
    results = []
    for candidate in candidates:
        text_sim = text_similarity(candidate.get("Summary", ""), job.get("Job description", ""))
        geo_sim = geo_score(candidate.get("Location", ""), job.get("Location", ""), candidate.get("Radius", "0"))
        final_score = 0.7 * text_sim + 0.3 * geo_sim
        results.append({
            "Candidate": candidate.get("Name"),
            "Email": candidate.get("Email"),
            "Score": round(final_score, 3),
            "Text Match": round(text_sim, 3),
            "Geo Match": round(geo_sim, 3)
        })
    results.sort(key=lambda x: x["Score"], reverse=True)
    return jsonify(results)
