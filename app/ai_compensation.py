# ai_compensation.py
from flask import Blueprint, request, jsonify
import openai
import os

ai_compensation_bp = Blueprint("ai_compensation", __name__)

COMPENSATION_PROMPT = """
You are a compensation analyst. Based on this job profile and location ({location}), suggest a fair salary range and typical perks. If you can't access exact market data, say 'Estimation only - confirm locally'.

Job Profile: {job_profile}
Company Type: {company_type}

Return salary range (currency), typical bonus/equity, and a disclaimer if needed.
"""

openai.api_key = os.getenv("OPENAI_API_KEY")

@ai_compensation_bp.route("/ai/compensation", methods=["POST"])
def ai_compensation():
    data = request.get_json(force=True)
    required_fields = ["location", "job_profile", "company_type"]
    missing = [k for k in required_fields if k not in data or not data[k]]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400
    prompt = COMPENSATION_PROMPT.format(**data)
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": prompt}]
    )
    return jsonify({"compensation_summary": response.choices[0].message.content})
