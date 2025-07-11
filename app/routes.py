import os
import re
import numpy as np
from flask import request, jsonify, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from app import app
from app.sheets import read_all, append_row, find_row_by_column, update_row_by_column
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
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

def extract_number(text):
    """Extract first number found in text, fallback to None."""
    match = re.search(r'(\d+(?:[.,]\d+)?)', str(text))
    if match:
        return float(match.group(1).replace(',', '').replace(' ', ''))
    return None

def get_coords(location):
    try:
        loc = geolocator.geocode(location, timeout=10)
        return (loc.latitude, loc.longitude) if loc else None
    except Exception:
        return None

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
        "Email", "Name", "Job Creation Date",
        "JobOverview", "JobLocation", "Compensation"
    ]
    missing = [k for k in required if k not in data or not data[k]]
    if missing:
        print("[ERROR] Missing fields in job creation:", missing)
        print("[DEBUG] Received data:", dict(data))
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    try:
        print("[INFO] Appending new job to Jobs2:", dict(data))
        append_row("Jobs2", {
            "Email": data["Email"],
            "Name": data["Name"],
            "Job Creation Date": data["Job Creation Date"],
            "JobOverview": data["JobOverview"],
            "JobLocation": data["JobLocation"],
            "Compensation": data["Compensation"],
            "Nber of applicants": data.get("Nber of applicants", "0"),
            "Archived?": data.get("Archived?", "")
        })
        print("[INFO] Job appended to sheet.")
        return jsonify({"message": "Job created!"})
    except Exception as e:
        print("[ERROR] Failed to append job:", str(e))
        return jsonify({"error": "Failed to update Google Sheet: " + str(e)}), 500

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

# ---------------------- CANDIDATE MATCHING ROUTE -----------------------

@app.route("/employer/match-candidates", methods=["POST"])
def match_candidates():
    job = request.get_json(force=True)
    print("[MATCH JOB PAYLOAD]", job)
    required = ["Name", "JobOverview", "JobLocation"]
    missing = [k for k in required if not job.get(k)]
    if missing:
        print("[MATCH MISSING FIELDS]", missing)
        return jsonify({"error": f"Missing required job fields: {', '.join(missing)}"}), 400

    job_embedding = get_openai_embedding(job["JobOverview"])
    job_comp = extract_number(job.get("Compensation", ""))
    job_coords = get_coords(job["JobLocation"])

    if job_embedding is None:
        print("[ERROR] JobOverview could not be embedded:", job["JobOverview"])
    if not job_coords:
        print("[ERROR] Could not geocode job location:", job["JobLocation"])

    candidates = read_all("Candidates2")
    results = []
    for cand in candidates:
        # 1. Embedding Similarity
        sim = 0.0
        if cand.get("Summary"):
            cand_embedding = get_openai_embedding(cand["Summary"])
            if cand_embedding is not None and job_embedding is not None:
                sim = float(np.dot(cand_embedding, job_embedding) / (np.linalg.norm(cand_embedding) * np.linalg.norm(job_embedding)))
        # 2. Salary/Compensation Bonus (optional, soft match)
        sal = extract_number(cand.get("Salary", ""))
        comp_bonus = 0.0
        if sal and job_comp:
            if job_comp >= sal:
                comp_bonus = 0.05  # Small boost if job >= candidate expectation

        # 3. Location/Radius filter
        default_radius = 30.0  # km
        radius = extract_number(cand.get("Radius", "")) or default_radius
        cand_coords = get_coords(cand.get("Location", ""))
        if not (job_coords and cand_coords):
            print("[CAND SKIP] Missing coords: job_coords:", job_coords, "cand_coords:", cand_coords)
            continue  # skip if cannot geocode either
        dist = geodesic(job_coords, cand_coords).km
        if dist > radius:
            print("[CAND SKIP] Candidate outside preferred radius:", cand.get("Name"), "dist:", dist, "radius:", radius)
            continue  # Candidate outside preferred radius

        # 4. Aggregate score
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

# ... keep the rest of your code unchanged ...
