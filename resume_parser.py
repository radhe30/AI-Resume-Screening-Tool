import pdfplumber
import os

def extract_text_from_pdf(file_path):
    text = ''
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
    return text

def get_all_resumes_text(folder_path='resumes'):
    resumes = {}
    for file in os.listdir(folder_path):
        if file.endswith(".pdf"):
            path = os.path.join(folder_path, file)
            resumes[file] = extract_text_from_pdf(path)
    return resumes
