from transformers import pipeline

nlp = pipeline("zero-shot-classification")

def match_profile(job_desc, candidate_summary):
    result = nlp(candidate_summary, candidate_labels=[job_desc])
    return result['scores'][0]
