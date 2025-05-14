OCR Web Application
This is an OCR web application built with Flask, Google Vision API, and Donut (for better table detection). The app enables users to upload images, process them using OCR models, and view or download results.

File Structure
Templates Folder
Contains all page rendering files for the web application:

base.html: Includes the navbar style using basic CSS and HTML.

index.html: Home page where users can perform OCR without logging in.

login.html: User login page.

ocr_upload.html: Allows logged-in users to upload files to the database.

register.html: User registration page.

result.html: Displays the OCR result from the Google Vision OCR model.

user.html: User dashboard page.

imageocr.html: A page that enables OCR processing for images without the need for a user login.

pdfocr.html: A page that enables OCR processing for PDFs, also without the need for a user login.

share_image.html: Page to share OCR results with others.

tessocr.html: Page to perform OCR using the Tesseract model.

view_shared_files.html: Page to view files shared with the user.


<---------------------------------------------------------------------------------------------------------------------------------------------------------------------------->


Donut Model Code
This model performs OCR using Donut for better table detection. The code provided below loads the Donut model and processor, and generates output text after processing the image:

python
Copy
Edit
from transformers import DonutProcessor, VisionEncoderDecoderModel
import torch
from PIL import Image

# Initialize Donut model and processor
model_name = "naver-clova-ix/donut-base"
processor = DonutProcessor.from_pretrained(model_name)
model = VisionEncoderDecoderModel.from_pretrained(model_name)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

def ocr_with_donut(image_path):
    """Perform OCR using Donut for better table detection"""
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt").to(device)
    output_ids = model.generate(inputs["pixel_values"], max_length=512)
    output_text = processor.decode(output_ids[0], skip_special_tokens=True)
    return output_text
Route for handling OCR with Donut:

python
Copy
Edit
@app.route('/uploadocr3', methods=['POST'])
def upload_image3():
    if 'image' not in request.files:
        return 'No image uploaded', 400

    image_file = request.files['image']
    content = image_file.read()

    # Save the image temporarily to pass to Donut
    image_path = "temp_image.png"
    with open(image_path, 'wb') as f:
        f.write(content)

    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=content)

    # Use document_text_detection for structured OCR
    response = client.document_text_detection(image=image)
    annotation = response.full_text_annotation

    # Logo detection (optional)
    logo_response = client.logo_detection(image=image)
    logos = logo_response.logo_annotations
    detected_logos = [logo.description for logo in logos]

    doc = Document()
    doc.add_paragraph("Detected Text:")

    # Process blocks from Google Vision
    for page in annotation.pages:
        for block in page.blocks:
            block_text = ""
            for paragraph in block.paragraphs:
                para_text = ""
                for word in paragraph.words:
                    word_text = ''.join([symbol.text for symbol in word.symbols])
                    para_text += word_text + " "
                block_text += para_text.strip() + "\n"

            # Heuristic to identify tables (existing logic)
            if len(block.paragraphs) > 1 and all(len(p.words) > 1 for p in block.paragraphs):
                doc.add_paragraph("\n[Possible Table Detected Below]", style='Intense Quote')
                table = doc.add_table(rows=0, cols=1)
                for paragraph in block.paragraphs:
                    row_cells = [''.join(s.text for w in paragraph.words for s in w.symbols)]
                    row = table.add_row().cells
                    row[0].text = row_cells[0]
            else:
                doc.add_paragraph(block_text.strip())

    # Use Donut for table detection and text extraction
    donut_text = ocr_with_donut(image_path)
    doc.add_paragraph("\n[Donut OCR Output for Table Detection Below]", style='Heading 1')
    doc.add_paragraph(donut_text)

    if detected_logos:
        doc.add_paragraph("\nDetected Logos:")
        for logo in detected_logos:
            doc.add_paragraph(f"- {logo}")

    # Create the output DOCX
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    return render_template('result.html',
                           detected_text=annotation.text,
                           detected_logos=detected_logos,
                           file_stream=file_stream)

<----------------------------------------------------------------------------------------------------------------------------------------->
Excel Adding Code
The following code uses the ExtractTable library to extract tables from an image and save the data in CSV format:

python
Copy
Edit
api_key = ""
et_sess = ExtractTable(api_key)
usage = et_sess.check_usage()

@app.route("/csvtest", methods=["POST"])
def csvtest():
    image_file = request.files["image"]
    base_filename = os.path.splitext(secure_filename(image_file.filename))[0]

    # Save the uploaded file (optional)
    upload_path = os.path.join(app.config['UPLOAD_FOLDER_2'], secure_filename(image_file.filename))
    image_file.save(upload_path)

    # Process and save CSV
    table_data = et_sess.process_file(filepath=upload_path, output_format="df")
    csv_filename = base_filename + ".csv"
    csv_output_path = os.path.join("static", "outputs", csv_filename)
    et_sess.save_output(csv_output_path, output_format="csv")

    return render_template("result2.html", detected_text=table_data, csv_filename=csv_filename)

<----------------------------------------------------------------------------------------------------------------------->
Conclusion
This application allows users to:

Upload images for OCR processing.

Get text results, including table detection (with Donut).

Download results as DOCX or CSV files.

Share OCR results and view shared files.
