from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from resume_parser import get_all_resumes_text
from text_cleaner import clean_text

def match_resumes(job_desc_file='job_description.txt'):
    with open(job_desc_file, 'r', encoding='utf-8') as f:
        job_desc = f.read()

    job_clean = clean_text(job_desc)
    resumes = get_all_resumes_text()
    cleaned_resumes = [clean_text(res) for res in resumes.values()]
    names = list(resumes.keys())

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform([job_clean] + cleaned_resumes)

    similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
    ranked = sorted(zip(names, similarities), key=lambda x: x[1], reverse=True)
    return ranked
