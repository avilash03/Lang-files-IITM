from flask import Flask, request, render_template, jsonify
import os
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from langdetect import detect, lang_detect_exception

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Map language codes to their full names
language_names = {
    'en': 'English',
    'hi': 'Hindi',
    'ta': 'Tamil',  # Add more languages and their full names as needed
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def detect_language(text):
    try:
        lang_code = detect(text)
        return language_names.get(lang_code, 'Unknown')  # Return full name or 'Unknown'
    except lang_detect_exception.LangDetectException:
        return 'Unknown'

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'})

        file = request.files['file']

        if file.filename == '':
            return jsonify({'error': 'No selected file'})

        if file and allowed_file(file.filename):
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)

            file_type = "PDF" if filename.endswith('.pdf') else "Image" if filename.endswith(('.png', '.jpg','.jpeg')) else "Text"
            detected_language = None

            if file_type == "PDF":
                pdf_text = extract_text_from_pdf(filename)
                detected_language = detect_language(pdf_text)

            elif file_type == "Image":
                img = Image.open(filename)
                text_en_hi = pytesseract.image_to_string(img, lang='eng+hin')
                text_ta = pytesseract.image_to_string(img, lang='tam')
                extracted_text = text_en_hi + " " + text_ta
                detected_language = detect_language(extracted_text)

            else:
                with open(filename, 'r', encoding='utf-8') as text_file:
                    file_content = text_file.read()
                detected_language = detect_language(file_content)

            return render_template('upload.html', file_type=file_type, detected_language=detected_language)

        else:
            return jsonify({'error': 'File type not allowed'})

    return render_template('upload.html')

def extract_text_from_pdf(filename):
    text = ""
    pdf_document = fitz.open(filename)
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        text += page.get_text()

        # If no text is detected in the PDF, use OCR on images
        if not text.strip():
            image_list = page.get_images(full=True)
            for img in image_list:
                xref = img[0]
                base_image = pdf_document.extract_image(xref)
                image_data = base_image["image"]

                # Save the image data to a file
                image_filename = f"temp_{xref}.png"
                with open(image_filename, "wb") as img_file:
                    img_file.write(image_data)

                # Open the saved image file and apply OCR
                img = Image.open(image_filename)
                text_en_hi = pytesseract.image_to_string(img, lang='eng+hin')
                text_ta = pytesseract.image_to_string(img, lang='tam')
                extracted_text = text_en_hi + " " + text_ta
                text += extracted_text

    pdf_document.close()
    return text

if __name__ == '__main__':
    app.run(debug=True)
