from PyPDF2 import PdfReader

def extract_text_from_pdf(pdf_file_path):
    try:
        reader = PdfReader(pdf_file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF: {e}")
        return ""

# Test the text extraction
if __name__ == "__main__":
    pdf_file_path = "resumes/ShaliniResume.pdf"  # Replace with your actual file path
    resume_text = extract_text_from_pdf(pdf_file_path)
    print("Extracted Text: ", resume_text)
