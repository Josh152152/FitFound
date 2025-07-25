from flask import Blueprint, request, jsonify
import openai
import os

ai_culture_bp = Blueprint("ai_culture", __name__)

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

openai.api_key = os.getenv("OPENAI_API_KEY")

@ai_culture_bp.route("/ai/culture", methods=["POST"])
def ai_culture():
    data = request.get_json(force=True)
    required_fields = ["company_type", "performance_focus", "values", "management_style", "team_dynamic", "rituals"]
    missing = [k for k in required_fields if k not in data or not data[k]]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    prompt = CULTURE_PROMPT.format(**data)
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}]
    )
    return jsonify({"culture_summary": response.choices[0].message["content"]})
