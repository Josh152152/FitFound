from flask import request, jsonify
from app import app
from app.sheets import read_all, append_row, find_row_by_column
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

model = SentenceTransformer('all-MiniLM-L6-v2')
geolocator = Nominatim(user_agent="fitfound-app")

@app.route("/")
def index():
    return "FitFound: Talent Matching App is running!"

@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    # For demo: storing plain password (NOT recommended—hash in production!)
    if find_row_by_column("Users2", "Email", data["Email"]):
        return jsonify({"error": "Email already exists"}), 400
    append_row("Users2", {
        "Email": data["Email"],
        "Name": data["Name"],
        "Password": data["Password"],
        "Type": data["Type"]
    })
    return jsonify({"message": "Signup successful!"})

@app.route("/candidate/profile", methods=["POST"])
def create_candidate_profile():
    data = request.json
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
    append_row("Jobs2", {
        "Email": data["Email"],
        "Name": data["Name"],
        "Location": data["Location"],
        "Job description": data["JobDescription"]
    })
    return jsonify({"message": "Job posted!"})

def get_coordinates(location):
    loc = geolocator.geocode(location)
    if loc:
        return (loc.latitude, loc.longitude)
    return None

def geo_score(candidate_loc, job_loc, candidate_radius):
    c_coords = get_coordinates(candidate_loc)
    j_coords = get_coordinates(job_loc)
    if not c_coords or not j_coords:
        return 0
    dist = geodesic(c_coords, j_coords).km
    try:
        candidate_radius = float(candidate_radius)
    except:
        candidate_radius = 0
    return 1.0 if dist <= candidate_radius else max(0, 1 - dist/100)

def text_similarity(a, b):
    emb = model.encode([a, b])
    return cosine_similarity([emb[0]], [emb[1]])[0][0]

@app.route("/employer/match_candidates/<job_id>", methods=["GET"])
def match_candidates(job_id):
    jobs = read_all("Jobs2")
    candidates = read_all("Candidates2")
    # For demo, use row index as job_id
    try:
        job = jobs[int(job_id)]
    except:
        return jsonify({"error": "Job not found"}), 404
    results = []
    for candidate in candidates:
        text_sim = text_similarity(candidate.get("Summary", ""), job.get("Job description", ""))
        geo_sim = geo_score(candidate.get("Location", ""), job.get("Location", ""), candidate.get("Radius", "0"))
        final_score = 0.7 * text_sim + 0.3 * geo_sim
        results.append({
            "Candidate": candidate.get("Name"),
            "Email": candidate.get("Email"),
            "Score": round(float(final_score), 3),
            "Text Match": round(float(text_sim), 3),
            "Geo Match": round(float(geo_sim), 3)
        })
    results.sort(key=lambda x: x["Score"], reverse=True)
    return jsonify(results)
