import PyPDF2
import os

# Function to extract text from a PDF
def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
    return text

# Function to compare the job description with a resume (using a basic scoring method)
def compare_text(job_description, resume_text):
    # A basic approach to compare the two texts (could be enhanced with more sophisticated NLP techniques)
    job_words = set(job_description.split())
    resume_words = set(resume_text.split())
    common_words = job_words.intersection(resume_words)
    return len(common_words)  # Return the number of common words as the "score"

# Function to match resumes with a job description
def match_resumes(job_description_path, resume_paths):
    # Extract text from the job description PDF
    job_description_text = extract_text_from_pdf(job_description_path)
    
    rankings = []
    for resume_path in resume_paths:
        # Extract text from each resume
        resume_text = extract_text_from_pdf(resume_path)
        
        # Compare the job description and resume, and calculate a score
        score = compare_text(job_description_text, resume_text)
        
        # Append the resume path and score to the rankings list
        rankings.append((resume_path, score))
    
    # Sort the rankings by score (highest score first)
    rankings.sort(key=lambda x: x[1], reverse=True)
    
    return rankings
