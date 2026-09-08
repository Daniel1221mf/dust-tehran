# dust-tehran
# Tehran: Shadows of the Realm — نسخه اندروید

این پوشه شامل بازی بازنویسی‌شده با **Kivy** (به‌جای pygame) است، چون pygame مستقیماً روی اندروید اجرا نمی‌شود ولی Kivy برای همین منظور ساخته شده و با ابزار **Buildozer** به APK تبدیل می‌شود.

## فایل‌ها
- `main.py` — کد کامل بازی با کنترل لمسی (جوی‌استیک سمت چپ پایین برای حرکت، لمس/نگه‌داشتن سمت راست صفحه برای شلیک، دکمه‌های Horse/Deliver/Talk/Crack/Pay/Map سمت راست).
- `buildozer.spec` — تنظیمات بسته‌بندی اندروید (نام برنامه، ورژن پایتون/کیوی، حالت landscape و ...).
- `.github/workflows/build.yml` — ساخت خودکار APK در فضای ابری گیت‌هاب (نیازی به لینوکس یا نصب Android SDK روی سیستم خودتان نیست).

> ⚠️ ساخت APK به Android SDK/NDK و ابزارهای لینوکسی نیاز دارد که در این محیط چت در دسترس نیست، پس خود فایل قابل دانلود apk را اینجا نمی‌توانم بسازم. دو راه ساده برای گرفتن apk وجود دارد:

## روش ۱ (پیشنهادی، بدون نیاز به لینوکس): GitHub Actions
1. یک ریپازیتوری جدید در گیت‌هاب بسازید و تمام فایل‌های این پوشه (`main.py`, `buildozer.spec`, `.github/`) را در آن push کنید.
2. به تب **Actions** بروید؛ ورک‌فلو «Build Android APK» به‌طور خودکار اجرا می‌شود (حدود ۱۵-۲۵ دقیقه طول می‌کشد چون SDK/NDK را دانلود می‌کند).
3. بعد از پایان، وارد همان اجرا (run) شوید و از بخش **Artifacts** فایل `tehran-shadows-apk` را دانلود کنید — داخلش `.apk` قابل نصب است.

## روش ۲: ساخت محلی (لینوکس یا WSL روی ویندوز)
```bash
pip install --user buildozer cython
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config \
    zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
cd tehran_android
buildozer android debug
