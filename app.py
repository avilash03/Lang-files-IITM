from flask import Flask, request, render_template, send_file, session, url_for
from flask_session import Session
import os
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
from langdetect import detect, lang_detect_exception
from googletrans import Translator
from docx import Document
import secrets  # Import the secrets module to generate a secret key

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a random secret key
app.config['SESSION_TYPE'] = 'filesystem'  # Use the filesystem to store session data
Session(app)

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
            return render_template('upload.html', error='No file part')

        file = request.files['file']

        if file.filename == '':
            return render_template('upload.html', error='No selected file')

        if file and allowed_file(file.filename):
            filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filename)

            file_type = "PDF" if filename.endswith('.pdf') else "Image" if filename.endswith(('.png', '.jpg', '.jpeg')) else "Text"
            detected_language = None
            translated_text = None

            if file_type == "PDF":
                pdf_text = extract_text_from_pdf(filename)
                detected_language = detect_language(pdf_text)
                if detected_language != 'ta':
                    translator = Translator()
                    translation = translator.translate(pdf_text, src=detected_language, dest='ta')
                    if translation:
                        translated_text = translation.text
                    else:
                        translated_text = "Translation failed"
                else:
                    translated_text = pdf_text
            elif file_type == "Image":
                img = Image.open(filename)
                text_en_hi = pytesseract.image_to_string(img, lang='eng+hin')
                text_ta = pytesseract.image_to_string(img, lang='tam')
                extracted_text = text_en_hi + " " + text_ta
                detected_language = detect_language(extracted_text)
                if detected_language != 'ta':
                    translator = Translator()
                    translation = translator.translate(extracted_text, src=detected_language, dest='ta')
                    if translation:
                        translated_text = translation.text
                    else:
                        translated_text = "Translation failed"
                else:
                    translated_text = extracted_text
            else:
                with open(filename, 'r', encoding='utf-8') as text_file:
                    file_content = text_file.read()
                detected_language = detect_language(file_content)
                if detected_language != 'ta':
                    translator = Translator()
                    translation = translator.translate(file_content, src=detected_language, dest='ta')
                    if translation:
                        translated_text = translation.text
                    else:
                        translated_text = "Translation failed"
                else:
                    translated_text = file_content

            # Create and save the translated DOCX file
            doc = Document()
            doc.add_paragraph(translated_text)
            docx_filename = 'translated_text.docx'
            doc.save(docx_filename)

            # Prepare the information to be displayed on the page
            info_dict = {
                'file_type': file_type,
                'detected_language': language_names.get(detected_language, 'Unknown'),
                'translated_text': translated_text,
            }

            # Serve the DOCX file for download and pass the info_dict to the template
            return render_template('result.html', info=info_dict, docx_filename=docx_filename)

        else:
            return render_template('upload.html', error='File type not allowed')

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

@app.route('/download_docx/<filename>')
def download_docx(filename):
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
