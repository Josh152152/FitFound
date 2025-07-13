import os
from flask import Blueprint, request, jsonify
import openai

# --------- AI BLUEPRINTS DEFINITION --------------

ai_profile_bp = Blueprint("ai_profile", __name__)
ai_culture_bp = Blueprint("ai_culture", __name__)
ai_compensation_bp = Blueprint("ai_compensation", __name__)

openai.api_key = os.getenv("OPENAI_API_KEY")

# --- Profile Prompt ---
PROFILE_PROMPT = """
You are an expert technical recruiter. Given the following answers, draft a clear, structured job profile:

Role: {role}
Hard Skills: {hard_skills}
Soft Skills: {soft_skills}
Years of Experience: {years_xp}
Team Size: {team_size}
Line Manager: {line_manager}

Please return a summary including:
- Job Title
- Hard Skills
- Soft Skills
- Required Experience
- Team Size
- Line Manager Title
- 3-5 Key Responsibilities (typical for this role)
"""

@ai_profile_bp.route("/ai/profile", methods=["POST"])
def ai_profile():
    data = request.get_json(force=True)
    required_fields = ["role", "hard_skills", "soft_skills", "years_xp", "team_size", "line_manager"]
    missing = [k for k in required_fields if k not in data or not data[k]]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    prompt = PROFILE_PROMPT.format(**data)
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}]
    )
    return jsonify({"profile_summary": response.choices[0].message["content"]})

# --- Culture Prompt ---
CULTURE_PROMPT = """
You are a company culture specialist. Summarize the company culture based on the following info:

Company Type: {company_type}
Performance Focus: {performance_focus}
Values: {values}
Management Style: {management_style}
Team Dynamic: {team_dynamic}
Notable Rituals: {rituals}

Return a short paragraph and key culture tags (e.g., performance-based, flat hierarchy, long-term vision).
"""

@ai_culture_bp.route("/ai/culture", methods=["POST"])
def ai_culture():
    data = request.get_json(force=True)
    required_fields = ["company_type", "performance_focus", "values", "management_style", "team_dynamic", "rituals"]
    missing = [k for k in required_fields if k not in data or not data[k]]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    prompt = CULTURE_PROMPT.format(**data)
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}]
    )
    return jsonify({"culture_summary": response.choices[0].message["content"]})

# --- Compensation Prompt ---
COMPENSATION_PROMPT = """
You are a compensation analyst. Based on this job profile and location ({location}), suggest a fair salary range and typical perks. If you can't access exact market data, say 'Estimation only - confirm locally'.

Job Profile: {job_profile}
Company Type: {company_type}

Return salary range (currency), typical bonus/equity, and a disclaimer if needed.
"""

@ai_compensation_bp.route("/ai/compensation", methods=["POST"])
def ai_compensation():
    data = request.get_json(force=True)
    required_fields = ["location", "job_profile", "company_type"]
    missing = [k for k in required_fields if k not in data or not data[k]]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    prompt = COMPENSATION_PROMPT.format(**data)
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}]
    )
    return jsonify({"compensation_summary": response.choices[0].message["content"]})

# --------- REGISTER BLUEPRINTS IN YOUR APP -----------

def register_ai_routes(app):
    app.register_blueprint(ai_profile_bp)
    app.register_blueprint(ai_culture_bp)
    app.register_blueprint(ai_compensation_bp)
