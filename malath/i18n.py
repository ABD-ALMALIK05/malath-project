from datetime import UTC

from flask import request, url_for
from werkzeug.routing import BuildError

TRANSLATIONS = {
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
        "hero_text": "Malath helps individuals securely archive civil and official documents in "
        "the cloud.",
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
        "invalid_file_type": "Only valid PDF, PNG, JPG, and JPEG files are allowed.",
        "empty_file": "The selected file is empty.",
        "file_too_large": "The selected file is too large.",
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
        "password_policy": "Password must be at least 8 characters and include a letter and a number.",
        "csrf_error": "This form could not be verified. Please try again.",
        "too_many_attempts": "Too many attempts. Please wait and try again.",
        "storage_upload_failed": "The document could not be uploaded right now. Please try again.",
        "storage_download_failed": "The download link could not be created right now. Please try again.",
        "storage_delete_failed": "The document could not be deleted right now. Please try again.",
        "pin_verified": "PIN Verified",
        "pin_verified_temporarily": "PIN verified temporarily",
        "pin_verification_required": "PIN verification required",
        "skip_to_content": "Skip to content",
        "main_navigation": "Main navigation",
        "language_switch": "Switch language",
        "required_field": "Required",
        "field_error": "Field error",
        "file_requirements": "PDF, PNG, JPG, or JPEG. Maximum size: 5 MB.",
        "browse_file": "Browse File",
        "drag_drop_file": "Drag and drop your file here",
        "selected_file": "Selected file",
        "confirm_delete": "Are you sure you want to delete this document?",
        "no_documents": "No documents found in this category.",
        "no_documents_yet": "No documents uploaded yet.",
        "start_upload": "Upload your first document",
        "file_size": "File Size",
        "temporarily_unlocked": "Document access is temporarily unlocked.",
        "verify_to_access": "Verify your PIN to access sensitive documents.",
        "submitting": "Please wait...",
        "page_error": "Something needs your attention.",
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
        "hero_text": "تساعد منصة ملاذ الأفراد على أرشفة الوثائق المدنية والرسمية بأمان على "
        "السحابة.",
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
        "invalid_file_type": "مسموح فقط بملفات PDF و PNG و JPG و JPEG الصحيحة.",
        "empty_file": "الملف المحدد فارغ.",
        "file_too_large": "الملف المحدد كبير جدًا.",
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
        "password_policy": "يجب أن تتكون كلمة المرور من 8 أحرف على الأقل وأن تحتوي على حرف ورقم.",
        "csrf_error": "تعذر التحقق من هذا النموذج. يرجى المحاولة مرة أخرى.",
        "too_many_attempts": "محاولات كثيرة جدًا. يرجى الانتظار ثم المحاولة مرة أخرى.",
        "storage_upload_failed": "تعذر رفع الوثيقة الآن. يرجى المحاولة مرة أخرى.",
        "storage_download_failed": "تعذر إنشاء رابط التنزيل الآن. يرجى المحاولة مرة أخرى.",
        "storage_delete_failed": "تعذر حذف الوثيقة الآن. يرجى المحاولة مرة أخرى.",
        "pin_verified": "تم تأكيد الرقم السري",
        "pin_verified_temporarily": "تم تأكيد الرقم السري مؤقتًا",
        "pin_verification_required": "تأكيد الرقم السري مطلوب",
        "skip_to_content": "تجاوز إلى المحتوى",
        "main_navigation": "التنقل الرئيسي",
        "language_switch": "تغيير اللغة",
        "required_field": "مطلوب",
        "field_error": "خطأ في الحقل",
        "file_requirements": "PDF أو PNG أو JPG أو JPEG. الحد الأقصى: 5 ميجابايت.",
        "browse_file": "استعراض الملف",
        "drag_drop_file": "اسحب الملف وأفلته هنا",
        "selected_file": "الملف المحدد",
        "confirm_delete": "هل أنت متأكد من حذف هذه الوثيقة؟",
        "no_documents": "لا توجد وثائق في هذا التصنيف.",
        "no_documents_yet": "لم يتم رفع أي وثائق بعد.",
        "start_upload": "ارفع أول وثيقة",
        "file_size": "حجم الملف",
        "temporarily_unlocked": "الوصول إلى الوثائق مفتوح مؤقتًا.",
        "verify_to_access": "أكد الرقم السري للوصول إلى الوثائق الحساسة.",
        "submitting": "يرجى الانتظار...",
        "page_error": "هناك أمر يحتاج إلى انتباهك.",
    },
}

SUPPORTED_LANGUAGES = frozenset(TRANSLATIONS)


def get_lang():
    lang = request.args.get("lang", "en")
    if lang not in SUPPORTED_LANGUAGES:
        return "en"
    return lang


def get_translations(lang=None):
    return TRANSLATIONS[lang or get_lang()]


def localized_url_for(endpoint, lang=None, **values):
    values.setdefault("lang", lang or get_lang())
    return url_for(endpoint, **values)


def switch_language_url(target_lang):
    endpoint = request.endpoint or "main.index"
    values = dict(request.view_args or {})
    values.update(request.args.to_dict())
    values["lang"] = target_lang
    try:
        return url_for(endpoint, **values)
    except BuildError:
        return url_for("main.index", lang=target_lang)


def category_label(category, lang=None):
    translations = get_translations(lang)
    return translations.get(category, category)


def format_file_size(size):
    try:
        size = int(size)
    except (TypeError, ValueError):
        return "0 B"

    units = ("B", "KB", "MB", "GB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024


def format_upload_date(upload_date, lang=None):
    if upload_date is None:
        return ""

    if upload_date.tzinfo is None:
        localized = upload_date
    else:
        localized = upload_date.astimezone(UTC)

    if (lang or get_lang()) == "ar":
        return localized.strftime("%Y-%m-%d %H:%M")
    return localized.strftime("%b %d, %Y %H:%M")
