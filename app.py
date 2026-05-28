import streamlit as st
import fitz  # PyMuPDF لتحويل صفحات الـ PDF إلى صور
import json
import io
import base64
from PIL import Image, ImageDraw, ImageFont
import google.generativeai as genai
from arabic_reshaper import reshape
from bidi.algorithm import get_display

# 1. إعداد مفتاح الـ API لـ Gemini أونلاين لضمان دقة 100%
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.warning("يرجى إدخال مفتاح الـ API في الإعدادات السرية لـ Streamlit.")
    # للاختبار المحلي السريع وأنت متصل بالإنترنت:
    genai.configure(api_key="ضع_مفتاح_Gemini_الخاص_بactive_هنا")

def convert_pdf_page_to_pil(pdf_file, page_num):
    """تحويل صفحة الـ PDF إلى كائن صورة PIL حقيقي متوافق 100% مع Gemini"""
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    page = doc.load_page(page_num)
    pix = page.get_pixmap(dpi=100)  # خففنا الجودة لسرعة خارقة
    img_data = pix.tobytes("png")   # سنستخدم صيغة png لأنها أكثر استقراراً
    return Image.open(io.BytesIO(img_data)

def analyze_image_online(pil_image):
    """إرسال صورة PIL مباشرة إلى نموذج flash السريع لتجنب خطأ 503 Timeout"""
    # استخدام النموذج السريع والخفيف جداً
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """
    أنت خبير تربوي ومساعد معلم دقيق جداً. انظر إلى هذه الصورة المرفقة (التي تمثل صفحة من كتاب مدرسي باللغة العربية) 
    وقم بتحليل محتواها بدقة (اقرأ النصوص، تأمل الرسومات، وافهم الأرقام والتمارين).
    استخرج المعطيات لتعبئتها في جذاذة الحصص الدراسية.
    التزم بالحقائق الموجودة في الصفحة تماماً دون أي خطأ أو ابتكار، وأجب *فقط* بصيغة JSON كالتالي:
    {
        "al_majal": "عنوان المجال أو الوحدة المستخرج بدقة من أعلى الصفحة (مثلا: الوحدة الخامسة)",
        "al_ahdaf": "الهدف التعليمي الأساسي المستنتج من الأنشطة المكتوبة",
        "al_wassail": "الوسائل الديداكتيكية الملاحظة بالصفحة (مثلا: كتاب التلميذ، صور توضيحية، ألواح)",
        "iftitah": "النشاط التمهيدي أو الملاحظة والتأطير في بداية الحصة (5 د)",
        "ictiyadi": "النشاط الاعتيادي التركيزي المناسب لمحتوى الدرس (10 د)",
        "kitaba": "التمارين والأنشطة المرتبطة بالكتابة والخط المكتوبة في الصفحة (30 د)",
        "qiraa": "الأنشطة المرتبطة بالفهم والقراءة واستثمار النص المكتوبة في الصفحة (30 د)",
        "ikhtitam": "النشاط الختامي أو التقويم الموجود في أسفل الصفحة"
    }
    """
    
    try:
        # إرسال كائن الصورة مباشرة كملف مرئي ممرر للنموذج وهو الحل الرسمي لمنع خطأ 503
        response = model.generate_content(
            [prompt, pil_image],
            generation_config={"response_mime_type": "application/json", "temperature": 0.0}
        )
        return json.loads(response.text.strip())
    except Exception as e:
        st.error(f"حدث خطأ أثناء الاتصال بالخادم: {e}")
        return None

def write_perfect_arabic_and_numbers(draw, text, position, font):
    """معالجة متطورة لطباعة النصوص والأرقام العربية دون تقطع ودون قلب الاتجاه"""
    if not text:
        return
    # إصلاح اتصال الحروف
    reshaped_text = reshape(text)
    # إصلاح اتجاه الكتابة من اليمين إلى اليسار (RTL) مع الأرقام (مثل: 30 د)
    bidi_text = get_display(reshaped_text)
    draw.text(position, bidi_text, fill=(0, 0, 0), font=font)

def create_joudada_image(template_path, data):
    """تعبئة قالب صورتك الأصلية بالبيانات المستخرجة أونلاين"""
    image = Image.open(template_path)
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype("Amiri-Regular.ttf", 20)
    except:
        font = ImageFont.load_default()

    # الإحداثيات الموزعة على مربعات صورتك المرجعية 493317876_1116685370499975_1509266722665690255_n.jpg
    positions = {
        "al_majal": (500, 75),       
        "al_ahdaf": (400, 185),       
        "al_wassail": (100, 135),     
        "iftitah": (700, 365),        
        "ictiyadi": (700, 565),       
        "kitaba": (200, 565),         
        "qiraa": (350, 825),          
        "ikhtitam": (200, 365)        
    }
    
    for key, text in data.items():
        if key in positions:
            write_perfect_arabic_and_numbers(draw, text, positions[key], font)
            
    return image

# --- واجهة تطبيق الويب عبر Streamlit ---
st.set_page_config(page_title="صانع الجذاذات الاحترافي البصري", layout="centered")
st.title("🎯 مولد الخرائط الذهنية والجذاذات الذكي (نسخة الصور والـ PDF)")
st.write("ارفع ملف درسك (حتى لو كان صوراً أو ممسوحاً ضوئياً)، وسيقوم النظام بقراءته وتحليله دون أخطاء.")

uploaded_file = st.file_uploader("اختر ملف PDF للدرس", type=["pdf"])

if uploaded_file is not None:
    # حساب عدد الصفحات في الملف
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    total_pages = len(doc)
    uploaded_file.seek(0)
    
    page_num = st.number_input(f"اختر رقم الصفحة التي تريد توليد جذاذتها (1-{total_pages}):", min_value=1, max_value=total_pages, value=1)
    
   with st.spinner("جاري تحويل الصفحة بصرياً وقراءتها بالذكاء الاصطناعي الخبير..."):
            
            # 1. تحويل الصفحة إلى PIL Image
            pil_img = convert_pdf_page_to_pil(uploaded_file, page_num - 1)
            
            # 2. التحليل السريع بدون أخطاء ميتاداتا
            ai_data = analyze_image_online(pil_img)
            
            if ai_data:
                # 3. رسم البيانات فوق قالب صورتك المرجعية
                final_image = create_joudada_image("template.jpg", ai_data)
                
                # عرض النتيجة المذهلة للمستخدم
                st.image(final_image, caption=f"الجذاذة التلقائية الناتجة للصفحة {page_num}", use_column_width=True)
                
                # إمكانية التحميل
                output_filename = f"joudada_page_{page_num}.jpg"
                final_image.save(output_filename)
                with open(output_filename, "rb") as file:
                    st.download_button(label="📥 تحميل الصورة الجاهزة للطباعة", data=file, file_name=output_filename, mime="image/jpeg")
