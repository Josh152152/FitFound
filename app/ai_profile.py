from flask import Blueprint, request, jsonify
import openai
import os

ai_profile_bp = Blueprint("ai_profile", __name__)

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

openai.api_key = os.getenv("OPENAI_API_KEY")

@ai_profile_bp.route("/ai/profile", methods=["POST"])
def ai_profile():
    data = request.get_json(force=True)
    required_fields = ["role", "hard_skills", "soft_skills", "years_xp", "team_size", "line_manager"]
    missing = [k for k in required_fields if k not in data or not data[k]]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    prompt = PROFILE_PROMPT.format(**data)
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}]
    )
    return jsonify({"profile_summary": response.choices[0].message["content"]})
