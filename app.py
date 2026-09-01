from flask import Flask, request, render_template, send_file
from img2table.document import Image, PDF
from img2table.ocr import TesseractOCR
import os
import cv2
import numpy as np

app = Flask(__name__)

def clean_and_rotate_image(image_path):
    print("Preprocessing image...")
    # 1. Load the image
    img = cv2.imread(image_path)
    
    # 2. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 3. Maximize contrast (Otsu's Binarization)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # 4. Deskew (Auto-rotate)
    coords = np.column_stack(np.where(thresh == 0))
    angle = cv2.minAreaRect(coords)[-1]
    
    # Adjust angle format
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
        
    # Rotate the image to straighten it
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    rotated = cv2.warpAffine(thresh, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    
    # Save the cleaned image
    cv2.imwrite(image_path, rotated)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if a file was actually sent
    if 'document' not in request.files:
        return render_template('index.html', error="No file uploaded!")
    
    file = request.files['document']
    if file.filename == '':
        return render_template('index.html', error="No file selected!")

    filename = file.filename.lower()
    
    # Initialize the open-source OCR engine
    # NOTE: Windows users might need to specify tesseract_cmd path here
    ocr = TesseractOCR(n_threads=1, lang="eng")
    output_excel_path = "converted_data.xlsx"
    
    # 1. Load the document into memory
    if filename.endswith('.pdf'):
        print(f"Processing multi-page PDF: {file.filename}...")
        temp_path = "temp_upload.pdf"
        file.save(temp_path)
        doc = PDF(temp_path)
    else:
        print(f"Processing Image: {file.filename}...")
        temp_path = "temp_upload.jpg"
        file.save(temp_path)
        
        # Only run OpenCV on image files
        clean_and_rotate_image(temp_path)
        doc = Image(temp_path)

    print("Scanning document for tables...")
    
    # 2. Extract tables to verify they exist
    extracted_tables = doc.extract_tables(ocr=ocr)
    
    # Check if at least one table exists across all pages
    has_tables = any(len(tables) > 0 for tables in extracted_tables.values())

    # 3. Handle the 'No Tables' scenario
    if not has_tables:
        print("No tables detected.")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        # Reload the page and pass the error message
        return render_template('index.html', error="No tables were found in the uploaded document. Please try a file with a clear grid or columns.")

    print("Tables found! Generating Excel file...")
    
    # 4. Generate the Excel file
    doc.to_xlsx(dest=output_excel_path, ocr=ocr)

    # Clean up the temporary file
    if os.path.exists(temp_path):
        os.remove(temp_path)

    # Send the generated Excel file back to the user
    return send_file(output_excel_path, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)