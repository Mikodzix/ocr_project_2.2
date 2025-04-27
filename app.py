from flask import Flask, render_template, request, redirect, url_for, send_file,session,flash
from google.cloud import vision
import os
from docx import Document
import io
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta, datetime
import bcrypt
from pdf2image import convert_from_path
import pytesseract
import msoffcrypto
import docx
import tempfile


app = Flask(__name__,static_folder='static')
app.secret_key = "abcd"
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Gang$hit101@localhost/OCR_PROJECT'
app.permanent_session_lifetime = timedelta(days=365)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['UPLOAD_FOLDER_2']='static/uploads/csv'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 #16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif','webp'}

db = SQLAlchemy(app)

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_2'], exist_ok=True)

#CHECK IF FILE TYPE IS ALLOWED
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

#PICS DB CLASS
class init_test_pics(db.Model):
    __tablename__ = 'init_test_pics'
    created_at = db.Column(db.DateTime, default=datetime.now())
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('init_test_users.id', ondelete='CASCADE'))

    def __init__(self, image_path=None):
        self.image_path = image_path

#USERS DB CLASS
class init_test_users(db.Model):
    __tablename__ = 'init_test_users'
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String(400))
    lname = db.Column(db.String(400))
    email = db.Column(db.String(400))
    created_at = db.Column(db.DateTime, default=datetime.now())
    image_path = db.Column(db.String(400))
    images = db.relationship('init_test_pics', backref='owner', cascade='all, delete-orphan')

    def __init__(self, fname, lname, email,image_path):
        self.fname = fname
        self.lname = lname
        self.email = email
        self.image_path = image_path


#DEFAULT ROUTE
@app.route("/")
def index():
    return render_template("index.html")

#REGISTRATION ROUTE WITH PASSWORD HASHING
@app.route("/submit", methods=["POST", "GET"])
def submit():
    if request.method == "POST":
        fname = request.form["fname"]
        lname = request.form["reg-password"]
        lname_encode = lname.encode('utf-8')
        lname_hashed= bcrypt.hashpw(lname_encode,bcrypt.gensalt()).decode('utf-8')
        email = request.form["email"]
#       image = request.files["image"]

        image_path = None
        #          if image and allowed_file(image.filename):
        #              filename = secure_filename(f"{fname}_{lname}_{image.filename}")
        #              filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        #              image.save(filepath)
        #              image_path = filename

        student1 = init_test_users(fname=fname, lname=lname_hashed, email=email, image_path=image_path)
        #student1_image = init_test_pics(image_path=filepath)
        #student1.images.append(student1_image)
        db.session.add(student1)
        db.session.commit()
        flash("Registration success")
        return render_template("login.html")

#LOGIN ROUTE AND UPLOAD.HTML REDIRECT
@app.route("/search", methods=["POST", "GET"])
def search():
    if request.method == "POST":
        log_user = request.form["reqfname"]
        log_password = request.form["reqemail"].encode('utf-8')

        stored_db_password = init_test_users.query.filter_by(fname=log_user).first()

        if stored_db_password is None or stored_db_password.lname is None:
            return render_template("login.html", failed="no user found")


        else:
            stored_db_password2 = stored_db_password.lname.encode('utf-8')
            isvalid = bcrypt.checkpw(log_password,stored_db_password2)

            found_all_users = init_test_users.query.filter_by(fname=log_user).all()
            if isvalid and found_all_users:
                    session["username"] = log_user
                    return render_template("ocr_upload.html",users=found_all_users)
            else:
                    return render_template("login.html", failed="no user found")

    else:
        if "username" in session:
            flash("Already logged in")
            return render_template("ocr_upload.html")
        return render_template("login.html")

#UPLOAD ROUTE TO SAVE IMAGES TO DATABASE WITH USER REDIRECT
@app.route("/upload", methods=["POST", "GET"])
def upload():
    if "username" in session:
        if request.method == "POST":
            image = request.files.get("image")
            image_path = None

            if image and image.filename != "" and allowed_file(image.filename):
                username = session.get("username") or "user"
                #CHANGED SECURE FILENAME
                #filename = secure_filename(f"{username}_{image.filename}")
                filename = secure_filename(f"{image.filename}")
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(filepath)
                image_path = filename

                # Get the user from DB
                session_user = init_test_users.query.filter_by(fname=username).first()
                if session_user:
                    # Always add image to init_test_pics
                    new_image = init_test_pics(image_path=image_path)
                    session_user.images.append(new_image)

                    # Only set image_path if this is the first upload
                    if not session_user.image_path:
                        session_user.image_path = image_path

                    db.session.add(session_user)
                    db.session.commit()

                    found_all_users = init_test_users.query.filter_by(fname=username).first()
                    print_user_pics = found_all_users.id
                    found_all_users_id=init_test_pics.query.filter_by(user_id=print_user_pics).all()
                    return render_template("user.html", users=found_all_users_id,username=username)
                else:
                    flash("User not found.")
                    return redirect("/")

            else:
                flash("Invalid or missing image file.")
                return render_template("ocr_upload.html")
        else:
            return render_template("ocr_upload.html")

    else:
        flash("Please log in.")
        return redirect("/login-redirect")

#LOGOUT ROUTE TO BE MODIFIED LATER ON
@app.route("/logout")
def logout():
    if "username" in session:
        user = session["username"]
        flash(f"YOU HAVE BEEN LOGGED OUT {user}")
    session.pop("username", None)
    return redirect(url_for("search"))

#DOWNLOAD OCR DOCUMENT AS DOCX ROUTE
@app.route('/download', methods=['POST'])
def download_doc():

    detected_text = request.form['real-text']
    doc_name = request.form.get('download-doc-name')

    if doc_name:
        doc_name = doc_name
    else:
        doc_name = 'ocr_result'


    # Create a new document with the text
    doc = Document()
    doc.add_paragraph(detected_text)


    # Save to memory
    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    # Send the file for download
    return send_file(
        file_stream,
        as_attachment=True,
        download_name=f'{doc_name}.docx',
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

#ORGANIZATIONAL SYSTEM DOWLOAD WITH LOCK CAPABILITY
@app.route('/download2', methods=['POST'])
def download2():
    if request.method == "POST":
            edited_text = request.form['real-text']
            protect = request.form.get('lock-doc')
            doc_name = request.form.get('download-doc-name')

            if doc_name:
                doc_name = doc_name
            else:
                doc_name = 'ocr_result'

            if protect:
                    doc_lock = request.form['lock-password']
                    password =  doc_lock # you can also let the user pick the password!
                    protected_docx = create_protected_docx(edited_text, password)

                    return send_file(
                        protected_docx,
                        as_attachment=True,
                        download_name=f"{doc_name}.locked.docx",
                        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
            else:
                # Create a new document with the text
                doc = Document()
                doc.add_paragraph(edited_text)

                # Save to memory
                file_stream = io.BytesIO()
                doc.save(file_stream)
                file_stream.seek(0)

                # Send the file for download
                return send_file(
                    file_stream,
                    as_attachment=True,
                    download_name=f'{doc_name}.docx',
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )

#LOCK PDF FUNCTION
def create_protected_docx(text, password):
        # Step 1: Create a normal docx in memory
        file_stream = io.BytesIO()
        doc = docx.Document()
        doc.add_paragraph(text)
        doc.save(file_stream)

        # Step 2: Protect it with a password
        file_stream.seek(0)
        office_file = msoffcrypto.OfficeFile(file_stream)

        protected_stream = io.BytesIO()
        office_file.encrypt(password=password, outfile=protected_stream)

        protected_stream.seek(0)
        return protected_stream


#UPLOAD GOOGLE VISION OCR FILE INPUT
@app.route('/uploadocr', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return 'No image uploaded', 400

    image_file = request.files['image']
    content = image_file.read()

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

    for page in annotation.pages:
        for block in page.blocks:
            block_text = ""
            for paragraph in block.paragraphs:
                para_text = ""
                for word in paragraph.words:
                    word_text = ''.join([
                        symbol.text for symbol in word.symbols
                    ])
                    para_text += word_text + " "
                block_text += para_text.strip() + "\n"

            # This heuristic assumes short lines aligned closely may be a table row
            if len(block.paragraphs) > 1 and all(len(p.words) > 1 for p in block.paragraphs):
                doc.add_paragraph("\n[Possible Table Detected Below]", style='Intense Quote')
                table = doc.add_table(rows=0, cols=1)
                for paragraph in block.paragraphs:
                    row_cells = [ ''.join(s.text for w in paragraph.words for s in w.symbols) ]
                    row = table.add_row().cells
                    row[0].text = row_cells[0]
            else:
                doc.add_paragraph(block_text.strip())

    if detected_logos:
        doc.add_paragraph("\nDetected Logos:")
        for logo in detected_logos:
            doc.add_paragraph(f"- {logo}")

    file_stream = io.BytesIO()
    doc.save(file_stream)
    file_stream.seek(0)

    return render_template('result.html',
                           detected_text=annotation.text,
                           detected_logos=detected_logos,
                           file_stream=file_stream)

#UPLOAD GOOGLE VISION USING PERFORM OCR BUTTON
@app.route('/uploadocr2', methods=['POST'])
def upload_image2():
    image_path = request.form.get("image_path")

    if image_path:

        full_path = os.path.join("static", "uploads", image_path)

        try:
            with io.open(full_path, 'rb') as image_file:
                content = image_file.read()
        except FileNotFoundError:
            return "Image file not found."


        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=content)

        response = client.text_detection(image=image)
        texts = response.text_annotations

        if texts:
            detected_text = texts[0].description

            # Create a temporary DOCX file in memory
            doc = Document()
            doc.add_paragraph(detected_text)

            # Save to memory instead of disk
            file_stream = io.BytesIO()
            doc.save(file_stream)
            file_stream.seek(0)

            return render_template('result.html',
                                   detected_text=detected_text,
                                   file_stream=file_stream)
        else:
            return "No text detected."

    else:
        image_file = request.files['image']
        content = image_file.read()
        client = vision.ImageAnnotatorClient()
        image = vision.Image(content=content)

        response = client.text_detection(image=image)
        texts = response.text_annotations

        if texts:
            detected_text = texts[0].description

            # Create a temporary DOCX file in memory
            doc = Document()
            doc.add_paragraph(detected_text)

            # Save to memory instead of disk
            file_stream = io.BytesIO()
            doc.save(file_stream)
            file_stream.seek(0)

            return render_template('result.html',
                                   detected_text=detected_text,
                                   file_stream=file_stream)
        else:
            return "No text detected."

#REGISTER PAGE RENDER ROUTE
@app.route("/register-redirect")
def reg_redirect():
    return render_template("register.html")

#LOGIN PAGE RENDER ROUTE
@app.route("/login-redirect")
def login_redirect():
    return render_template("login.html")

#GO TO DASHBOARD REDIRECT ROUTE
@app.route("/user-redirect")
def user_redirect():
    if "username" in session:
            username = session.get("username") or "user"
            found_all_users = init_test_users.query.filter_by(fname=username).first()
            print_user_pics = found_all_users.id
            found_all_users_id = init_test_pics.query.filter_by(user_id=print_user_pics).all()
            return render_template("user.html", users=found_all_users_id,username=username)
    else:
        return redirect(url_for("reg_redirect"))

#PERFORM PDF OCR
@app.route("/pdf-upload",methods=["POST"])
def pdf_upload():
    pdf = request.files['pdf-submit']

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdf.save(temp_pdf)
        temp_pdf_path = temp_pdf.name  # Path to the temp file

    pdftest = convert_from_path(temp_pdf_path, dpi=300)

    all_text = ""
    for i, img in enumerate(pdftest):
        text = pytesseract.image_to_string(img)
        all_text += f"--- Page {i + 1} ---\n{text}\n\n"

    # CLEANUP
    if os.path.exists(temp_pdf_path):
        os.remove(temp_pdf_path)

    return render_template("result.html", detected_text=all_text)

#<------------------------------------------WORKING CODE ABOVE------------------------------------------------------>
#<------------------------------------------TEST CODE BELOW---------------------------------------------------------->




#<-------------------------------------------END OF TEST CODE-------------------------------------------------------->

#MAIN FUNCTION
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
