# راهنمای سریع شروع - Quick Start Guide

## نصب و راه‌اندازی سریع

### روی Linux/Mac:

```bash
# 1. دانلود و رفتن به پوشه پروژه
cd "New folder"

# 2. اجرای اسکریپت نصب و راه‌اندازی
chmod +x run_bot.sh
./run_bot.sh

# 3. اجرای ربات
./run_bot.sh --run
```

### روی Windows:

```bash
# 1. باز کردن Command Prompt یا PowerShell
cd "C:\Users\98912\Downloads\New folder"

# 2. اجرای اسکریپت Windows
setup_and_run.bat

# 3. یا اجرای مستقیم
python crypto_futures_bot.py
```

## تنظیمات اولیه

### 1. تنظیم API Keys

فایل `config.json` را باز کنید و کلیدهای API خود را اضافه کنید:

```json
{
  "bybit_api_key": "YOUR_API_KEY_HERE",
  "bybit_api_secret": "YOUR_API_SECRET_HERE",
  "testnet": true,
  "auto_trade": false
}
```

### 2. حالت‌های اجرا

#### حالت تحلیل (توصیه می‌شود برای شروع):
```json
{
  "auto_trade": false
}
```
ربات فقط تحلیل می‌کند و معامله انجام نمی‌دهد.

#### حالت معامله خودکار:
```json
{
  "auto_trade": true,
  "testnet": true
}
```
ربات معاملات را به صورت خودکار انجام می‌دهد (در حالت تست).

### 3. تنظیمات مهم

- `scan_interval`: فاصله اسکن (ثانیه) - پیش‌فرض: 300 (5 دقیقه)
- `min_confidence`: حداقل اعتماد برای سیگنال (0.0-1.0) - پیش‌فرض: 0.7
- `max_position_size`: حداکثر حجم معامله (USDT) - پیش‌فرض: 100
- `stop_loss_percent`: درصد Stop Loss - پیش‌فرض: 5%
- `take_profit_percent`: درصد Take Profit - پیش‌فرض: 10%

## ساختار فایل‌ها

```
New folder/
├── crypto_futures_bot.py    # کد اصلی ربات
├── requirements.txt          # وابستگی‌های Python
├── config.json              # فایل پیکربندی
├── config.json.example      # نمونه فایل پیکربندی
├── setup_and_run.sh         # اسکریپت نصب (Linux/Mac)
├── setup_and_run.bat        # اسکریپت نصب (Windows)
├── run_bot.sh              # اسکریپت اصلی همه‌کاره
├── README.md               # مستندات کامل
├── QUICKSTART.md           # این فایل
├── trading_bot.db          # دیتابیس (پس از اولین اجرا)
└── trading_bot.log         # فایل لاگ
```

## دستورات مفید

### مشاهده لاگ‌ها
```bash
# Linux/Mac
tail -f trading_bot.log

# Windows
type trading_bot.log
```

### مشاهده دیتابیس
```bash
# استفاده از sqlite3
sqlite3 trading_bot.db

# در sqlite3:
.tables                    # مشاهده جداول
SELECT * FROM tokens;      # مشاهده توکن‌ها
SELECT * FROM signals;     # مشاهده سیگنال‌ها
SELECT * FROM trades;      # مشاهده معاملات
```

### تست اتصال
```bash
# Linux/Mac
./run_bot.sh --test

# Windows
python -c "from crypto_futures_bot import *; print('OK')"
```

## نکات مهم

1. **همیشه از Testnet شروع کنید**: قبل از معامله واقعی، در Testnet تست کنید
2. **محدود کردن سرمایه**: فقط بخش کوچکی از سرمایه را برای معامله خودکار استفاده کنید
3. **نظارت مداوم**: ربات را تحت نظر داشته باشید
4. **بکاپ دیتابیس**: به طور منظم از دیتابیس بکاپ بگیرید

## عیب‌یابی

### مشکل: "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### مشکل: "API Key not working"
- بررسی کنید که API Key درست باشد
- بررسی کنید که دسترسی Futures Trading فعال باشد
- اگر از Testnet استفاده می‌کنید، API Key را از Testnet دریافت کنید

### مشکل: "No tokens found"
- بررسی اتصال اینترنت
- بررسی دسترسی به DexScreener API
- بررسی لاگ‌ها

## پشتیبانی

برای اطلاعات بیشتر، فایل README.md را مطالعه کنید.

## هشدار

⚠️ **هشدار**: معامله در بازار کریپتو پرریسک است. این ربات تنها یک ابزار است و تضمینی برای سودآوری ندارد. همیشه با احتیاط عمل کنید.

