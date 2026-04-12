import os
import uuid
from datetime import datetime
from functools import wraps

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_

app = Flask(__name__)
app.config['SECRET_KEY'] = 'malath_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///malath.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ========= AWS CONFIG =========
# ضع المفاتيح الجديدة هنا أو انقلها إلى config.py
app.config['AWS_ACCESS_KEY'] = 'AKIA2UC27MZMC6VACHWE'
app.config['AWS_SECRET_KEY'] = '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'
app.config['AWS_BUCKET_NAME'] = 'malath-documents-2026'
app.config['AWS_REGION'] = 'eu-north-1'

# ========= LOCAL CONFIG =========
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ========= EXTENSIONS =========
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ========= S3 CLIENT =========
s3 = boto3.client(
    's3',
    aws_access_key_id=app.config['AWS_ACCESS_KEY'],
    aws_secret_access_key=app.config['AWS_SECRET_KEY'],
    region_name=app.config['AWS_REGION']
)

translations = {
    "en": {
        "brand": "Malath",
        "brand_ar": "ملاذ",
        "get_started": "Get Started",
        "login": "Login",
        "register": "Register",
        "logout": "Logout",
        "dashboard": "Dashboard",
        "upload": "Upload Document",
        "documents": "My Documents",
        "email_or_username": "Email or Username",
        "password": "Password",
        "username": "Username",
        "email": "Email",
        "welcome_back": "Welcome Back",
        "login_subtitle": "Access your secure digital vault",
        "register_subtitle": "Create your secure account",
        "language": "العربية",
        "hero_title": "Protect Your Documents, Preserve Your Rights",
        "hero_text": "Malath helps individuals securely archive civil and official documents in the cloud.",
        "feature_1": "Encrypted document storage",
        "feature_2": "Fast access from anywhere",
        "feature_3": "Organized by category",
        "feature_4": "Built for sensitive records",
        "full_name": "Full Name",
        "create_account": "Create Account",
        "already_have_account": "Already have an account?",
        "no_account": "Don't have an account?",
        "welcome_user": "Welcome",
        "login_success": "Login successful.",
        "logout_success": "You have been logged out.",
        "register_success": "Account created successfully. Please log in.",
        "invalid_credentials": "Invalid username/email or password.",
        "username_exists": "Username already exists.",
        "email_exists": "Email already exists.",
        "all_fields_required": "All fields are required.",
        "secure_pin": "Secure PIN (6 digits)",
        "verify_pin": "Verify PIN",
        "pin_subtitle": "Enter your secure PIN to access sensitive documents.",
        "pin_success": "PIN verified successfully.",
        "pin_invalid": "Incorrect PIN.",
        "pin_required": "PIN must be exactly 6 digits.",
        "statistics": "Statistics",
        "quick_actions": "Quick Actions",
        "recent_documents": "Recent Documents",
        "all_documents": "All Documents",
        "government": "Government",
        "medical": "Medical",
        "property": "Property",
        "personal": "Personal",
        "title": "Title",
        "category": "Category",
        "description": "Description",
        "choose_file": "Choose File",
        "upload_date": "Upload Date",
        "file_name": "File Name",
        "actions": "Actions",
        "download": "Download",
        "edit": "Edit",
        "delete": "Delete",
        "save_changes": "Save Changes",
        "document_uploaded": "Document uploaded successfully.",
        "document_updated": "Document updated successfully.",
        "document_deleted": "Document deleted successfully.",
        "not_authorized": "You are not authorized to access this document.",
        "invalid_file_type": "Only PDF, PNG, JPG, and JPEG files are allowed.",
        "file_required": "Please choose a file.",
        "doc_title_required": "Document title is required.",
        "documents_protected": "Sensitive document area protected by secure PIN.",
        "enter_pin_first": "Please verify your PIN first.",
        "total_docs": "Total Documents",
        "manage_archive": "Manage your secure archive and protected files.",
        "notes_optional": "Notes (optional)",
        "update_document": "Update Document",
        "view_archive": "View Archive",
        "security_layer": "Security Layer",
        "pin_verified": "PIN Verified"
    },
    "ar": {
        "brand": "Malath",
        "brand_ar": "ملاذ",
        "get_started": "ابدأ الآن",
        "login": "تسجيل الدخول",
        "register": "إنشاء حساب",
        "logout": "تسجيل الخروج",
        "dashboard": "لوحة التحكم",
        "upload": "رفع وثيقة",
        "documents": "وثائقي",
        "email_or_username": "البريد الإلكتروني أو اسم المستخدم",
        "password": "كلمة المرور",
        "username": "اسم المستخدم",
        "email": "البريد الإلكتروني",
        "welcome_back": "مرحبًا بعودتك",
        "login_subtitle": "ادخل إلى خزنتك الرقمية الآمنة",
        "register_subtitle": "أنشئ حسابك الآمن",
        "language": "English",
        "hero_title": "احمِ وثائقك، واحفظ حقوقك",
        "hero_text": "تساعد منصة ملاذ الأفراد على أرشفة الوثائق المدنية والرسمية بأمان على السحابة.",
        "feature_1": "تخزين مشفر للوثائق",
        "feature_2": "وصول سريع من أي مكان",
        "feature_3": "تنظيم حسب التصنيف",
        "feature_4": "مناسب للملفات الحساسة",
        "full_name": "الاسم الكامل",
        "create_account": "إنشاء حساب",
        "already_have_account": "لديك حساب بالفعل؟",
        "no_account": "ليس لديك حساب؟",
        "welcome_user": "مرحبًا",
        "login_success": "تم تسجيل الدخول بنجاح.",
        "logout_success": "تم تسجيل الخروج.",
        "register_success": "تم إنشاء الحساب بنجاح. يمكنك الآن تسجيل الدخول.",
        "invalid_credentials": "اسم المستخدم أو البريد الإلكتروني أو كلمة المرور غير صحيحة.",
        "username_exists": "اسم المستخدم موجود بالفعل.",
        "email_exists": "البريد الإلكتروني موجود بالفعل.",
        "all_fields_required": "جميع الحقول مطلوبة.",
        "secure_pin": "الرقم السري الآمن (6 أرقام)",
        "verify_pin": "تأكيد الرقم السري",
        "pin_subtitle": "أدخل الرقم السري الآمن للوصول إلى الوثائق الحساسة.",
        "pin_success": "تم تأكيد الرقم السري بنجاح.",
        "pin_invalid": "الرقم السري غير صحيح.",
        "pin_required": "يجب أن يكون الرقم السري 6 أرقام بالضبط.",
        "statistics": "الإحصائيات",
        "quick_actions": "إجراءات سريعة",
        "recent_documents": "أحدث الوثائق",
        "all_documents": "كل الوثائق",
        "government": "حكومي",
        "medical": "طبي",
        "property": "ملكية",
        "personal": "شخصي",
        "title": "العنوان",
        "category": "التصنيف",
        "description": "الوصف",
        "choose_file": "اختر الملف",
        "upload_date": "تاريخ الرفع",
        "file_name": "اسم الملف",
        "actions": "الإجراءات",
        "download": "تنزيل",
        "edit": "تعديل",
        "delete": "حذف",
        "save_changes": "حفظ التعديلات",
        "document_uploaded": "تم رفع الوثيقة بنجاح.",
        "document_updated": "تم تحديث الوثيقة بنجاح.",
        "document_deleted": "تم حذف الوثيقة بنجاح.",
        "not_authorized": "غير مصرح لك بالوصول إلى هذه الوثيقة.",
        "invalid_file_type": "مسموح فقط بملفات PDF و PNG و JPG و JPEG.",
        "file_required": "يرجى اختيار ملف.",
        "doc_title_required": "عنوان الوثيقة مطلوب.",
        "documents_protected": "منطقة الوثائق الحساسة محمية برقم سري آمن.",
        "enter_pin_first": "يرجى تأكيد الرقم السري أولًا.",
        "total_docs": "إجمالي الوثائق",
        "manage_archive": "أدر أرشيفك الآمن وملفاتك المحمية.",
        "notes_optional": "ملاحظات (اختياري)",
        "update_document": "تحديث الوثيقة",
        "view_archive": "عرض الأرشيف",
        "security_layer": "طبقة الحماية",
        "pin_verified": "تم تأكيد الرقم السري"
    }
}


def get_lang():
    lang = request.args.get("lang", "en")
    if lang not in translations:
        lang = "en"
    return lang


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def pin_required_route(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        lang = get_lang()
        t = translations[lang]
        if not session.get('pin_verified'):
            flash(t["enter_pin_first"], "warning")
            return redirect(url_for('verify_pin', next=request.path, lang=lang))
        return view_func(*args, **kwargs)
    return wrapper


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    pin_hash = db.Column(db.String(255), nullable=False)

    documents = db.relationship('Document', backref='owner', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def set_pin(self, pin):
        self.pin_hash = generate_password_hash(pin)

    def check_pin(self, pin):
        return check_password_hash(self.pin_hash, pin)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=True)
    file_url = db.Column(db.String(500), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_globals():
    lang = get_lang()
    return dict(current_lang=lang)


def get_category_counts(user_id):
    docs = Document.query.filter_by(user_id=user_id).all()
    return {
        'total': len(docs),
        'government': sum(1 for d in docs if d.category == 'government'),
        'medical': sum(1 for d in docs if d.category == 'medical'),
        'property': sum(1 for d in docs if d.category == 'property'),
        'personal': sum(1 for d in docs if d.category == 'personal')
    }


@app.route('/')
def index():
    lang = get_lang()
    if current_user.is_authenticated:
        return redirect(url_for('dashboard', lang=lang))
    return render_template('index.html', t=translations[lang], lang=lang)


@app.route('/register', methods=['GET', 'POST'])
def register():
    lang = get_lang()
    t = translations[lang]

    if current_user.is_authenticated:
        return redirect(url_for('dashboard', lang=lang))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        pin = request.form.get('pin', '').strip()

        if not full_name or not username or not email or not password or not pin:
            flash(t["all_fields_required"], "danger")
            return redirect(url_for('register', lang=lang))

        if not pin.isdigit() or len(pin) != 6:
            flash(t["pin_required"], "danger")
            return redirect(url_for('register', lang=lang))

        if User.query.filter_by(username=username).first():
            flash(t["username_exists"], "danger")
            return redirect(url_for('register', lang=lang))

        if User.query.filter_by(email=email).first():
            flash(t["email_exists"], "danger")
            return redirect(url_for('register', lang=lang))

        user = User(
            full_name=full_name,
            username=username,
            email=email
        )
        user.set_password(password)
        user.set_pin(pin)

        db.session.add(user)
        db.session.commit()

        flash(t["register_success"], "success")
        return redirect(url_for('login', lang=lang))

    return render_template('register.html', t=t, lang=lang)


@app.route('/login', methods=['GET', 'POST'])
def login():
    lang = get_lang()
    t = translations[lang]

    if current_user.is_authenticated:
        return redirect(url_for('dashboard', lang=lang))

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        password = request.form.get('password', '').strip()

        if not identifier or not password:
            flash(t["all_fields_required"], "danger")
            return redirect(url_for('login', lang=lang))

        user = User.query.filter(
            or_(User.email == identifier.lower(), User.username == identifier)
        ).first()

        if user and user.check_password(password):
            login_user(user)
            session.pop('pin_verified', None)
            flash(t["login_success"], "success")
            return redirect(url_for('dashboard', lang=lang))

        flash(t["invalid_credentials"], "danger")
        return redirect(url_for('login', lang=lang))

    return render_template('login.html', t=t, lang=lang)


@app.route('/verify-pin', methods=['GET', 'POST'])
@login_required
def verify_pin():
    lang = get_lang()
    t = translations[lang]
    next_url = request.args.get('next') or url_for('documents', lang=lang)

    if request.method == 'POST':
        pin = request.form.get('pin', '').strip()

        if not pin.isdigit() or len(pin) != 6:
            flash(t["pin_required"], "danger")
            return redirect(url_for('verify_pin', next=next_url, lang=lang))

        if current_user.check_pin(pin):
            session['pin_verified'] = True
            flash(t["pin_success"], "success")
            return redirect(next_url)

        flash(t["pin_invalid"], "danger")

    return render_template('verify_pin.html', t=t, lang=lang, next_url=next_url)


@app.route('/logout')
@login_required
def logout():
    lang = get_lang()
    t = translations[lang]
    logout_user()
    session.pop('pin_verified', None)
    flash(t["logout_success"], "success")
    return redirect(url_for('login', lang=lang))


@app.route('/dashboard')
@login_required
def dashboard():
    lang = get_lang()
    t = translations[lang]
    counts = get_category_counts(current_user.id)
    recent_documents = (
        Document.query
        .filter_by(user_id=current_user.id)
        .order_by(Document.upload_date.desc())
        .limit(5)
        .all()
    )

    return render_template(
        'dashboard.html',
        t=t,
        lang=lang,
        counts=counts,
        recent_documents=recent_documents,
        pin_verified=session.get('pin_verified', False)
    )


@app.route('/upload', methods=['GET', 'POST'])
@login_required
@pin_required_route
def upload():
    lang = get_lang()
    t = translations[lang]

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        file = request.files.get('file')

        if not title:
            flash(t["doc_title_required"], "danger")
            return redirect(url_for('upload', lang=lang))

        if not file or not file.filename:
            flash(t["file_required"], "danger")
            return redirect(url_for('upload', lang=lang))

        if not allowed_file(file.filename):
            flash(t["invalid_file_type"], "danger")
            return redirect(url_for('upload', lang=lang))

        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        stored_filename = f"users/{current_user.id}/{category}/{uuid.uuid4().hex}.{extension}"
       # stored_filename = f"{uuid.uuid4().hex}.{extension}"

        # احسب الحجم قبل الرفع
        file.stream.seek(0, os.SEEK_END)
        file_size = file.stream.tell()
        file.stream.seek(0)

        try:
            s3.upload_fileobj(
                file.stream,
                app.config['AWS_BUCKET_NAME'],
                stored_filename,
                ExtraArgs={
                    "ContentType": file.content_type or "application/octet-stream"
                }
            )
        except (BotoCoreError, ClientError, Exception) as e:
            flash(f"S3 upload failed: {str(e)}", "danger")
            return redirect(url_for('upload', lang=lang))

        file_url = (
            f"https://{app.config['AWS_BUCKET_NAME']}.s3."
            f"{app.config['AWS_REGION']}.amazonaws.com/{stored_filename}"
        )

        document = Document(
            title=title,
            category=category,
            description=description,
            file_url=file_url,
            stored_filename=stored_filename,
            original_filename=original_filename,
            file_type=extension,
            file_size=file_size,
            user_id=current_user.id
        )

        db.session.add(document)
        db.session.commit()

        flash(t["document_uploaded"], "success")
        return redirect(url_for('documents', lang=lang))

    return render_template('upload.html', t=t, lang=lang)


@app.route('/documents')
@login_required
@pin_required_route
def documents():
    lang = get_lang()
    t = translations[lang]

    selected_category = request.args.get('category', '').strip()
    query = Document.query.filter_by(user_id=current_user.id)

    if selected_category in ['government', 'medical', 'property', 'personal']:
        query = query.filter_by(category=selected_category)

    documents_list = query.order_by(Document.upload_date.desc()).all()
    counts = get_category_counts(current_user.id)

    return render_template(
        'documents.html',
        t=t,
        lang=lang,
        documents=documents_list,
        counts=counts,
        selected_category=selected_category
    )


@app.route('/documents/download/<int:document_id>')
@login_required
@pin_required_route
def download_document(document_id):
    lang = get_lang()
    t = translations[lang]
    document = Document.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash(t["not_authorized"], "danger")
        return redirect(url_for('documents', lang=lang))

    try:
        presigned_url = s3.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': app.config['AWS_BUCKET_NAME'],
                'Key': document.stored_filename
            },
            ExpiresIn=300  # 5 minutes
        )
        return redirect(presigned_url)

    except Exception as e:
        flash(f"Download link generation failed: {str(e)}", "danger")
        return redirect(url_for('documents', lang=lang))


@app.route('/documents/edit/<int:document_id>', methods=['GET', 'POST'])
@login_required
@pin_required_route
def edit_document(document_id):
    lang = get_lang()
    t = translations[lang]
    document = Document.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash(t["not_authorized"], "danger")
        return redirect(url_for('documents', lang=lang))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()

        if not title:
            flash(t["doc_title_required"], "danger")
            return redirect(url_for('edit_document', document_id=document.id, lang=lang))

        document.title = title
        document.category = category
        document.description = description

        db.session.commit()
        flash(t["document_updated"], "success")
        return redirect(url_for('documents', lang=lang))

    return render_template('edit_document.html', t=t, lang=lang, document=document)


@app.route('/documents/delete/<int:document_id>', methods=['POST'])
@login_required
@pin_required_route
def delete_document(document_id):
    lang = get_lang()
    t = translations[lang]
    document = Document.query.get_or_404(document_id)

    if document.user_id != current_user.id:
        flash(t["not_authorized"], "danger")
        return redirect(url_for('documents', lang=lang))

    try:
        s3.delete_object(
            Bucket=app.config['AWS_BUCKET_NAME'],
            Key=document.stored_filename
        )
    except (BotoCoreError, ClientError, Exception) as e:
        flash(f"S3 delete failed: {str(e)}", "danger")
        return redirect(url_for('documents', lang=lang))

    db.session.delete(document)
    db.session.commit()

    flash(t["document_deleted"], "success")
    return redirect(url_for('documents', lang=lang))


@app.route('/documents/clear-pin')
@login_required
def clear_pin():
    session.pop('pin_verified', None)
    flash(translations[get_lang()]["documents_protected"], "info")
    return redirect(url_for('dashboard', lang=get_lang()))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)