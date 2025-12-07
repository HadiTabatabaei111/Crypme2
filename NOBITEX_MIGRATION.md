# تغییر از Bybit به Nobitex

این فایل خلاصه تغییرات انجام شده برای جایگزینی صرافی Bybit با Nobitex را نشان می‌دهد.

## تغییرات انجام شده

### 1. فایل‌های جدید
- ✅ `nobitex_trader.py` - ماژول جدید برای اتصال به Nobitex API

### 2. فایل‌های حذف شده
- ❌ `bybit_trader.py` - حذف شد (جایگزین با nobitex_trader.py)

### 3. فایل‌های به‌روزرسانی شده

#### `dashboard_server.py`
- تغییر import از `BybitTrader` به `NobitexTrader`
- تغییر تمام endpointها از `/api/bybit/*` به `/api/nobitex/*`
- به‌روزرسانی متغیرها و توابع

#### `static/js/futures.js`
- تغییر تمام API calls از `/api/bybit/*` به `/api/nobitex/*`
- تغییر متن دکمه‌ها از "Bybit" به "Nobitex"

#### `templates/futures.html`
- تغییر متن دکمه "ارسال به Bybit" به "ارسال به Nobitex"

#### `config.json.example`
- تغییر `bybit_api_key` به `nobitex_api_key`
- تغییر `bybit_api_secret` به `nobitex_api_secret`
- تغییر `bybit_testnet` به `nobitex_testnet`

## تنظیمات Nobitex

### API Keys
برای استفاده از Nobitex، باید API keys را در فایل `config.json` تنظیم کنید:

```json
{
  "nobitex_api_key": "YOUR_NOBITEX_API_KEY",
  "nobitex_api_secret": "YOUR_NOBITEX_API_SECRET",
  "nobitex_testnet": false
}
```

### نحوه دریافت API Keys
1. وارد حساب کاربری Nobitex خود شوید
2. به بخش API Management بروید
3. API Key و Secret Key ایجاد کنید
4. دسترسی Futures Trading را فعال کنید
5. کلیدها را در `config.json` قرار دهید

## تفاوت‌های API

### فرمت Symbol
- Bybit: `BTCUSDT`
- Nobitex: `BTC-USDT` (با خط تیره)

ماژول به صورت خودکار فرمت را تبدیل می‌کند.

### Authentication
- Nobitex از JWT token authentication استفاده می‌کند
- در صورت عدم موفقیت در authentication، برای public endpoints ادامه می‌دهد

### Endpoints
- `/v1/instruments` - دریافت اطلاعات نمادها
- `/v1/ticker` - دریافت قیمت فعلی
- `/v1/klines` - دریافت داده‌های کندل
- `/v1/orders` - ثبت سفارش

## تست سیستم

پس از تغییرات، سیستم را به این صورت تست کنید:

1. **بررسی API Keys:**
```bash
# اطمینان حاصل کنید که API keys در config.json تنظیم شده‌اند
cat config.json
```

2. **اجرای سرور:**
```bash
python dashboard_server.py
```

3. **تست Endpoints:**
- باز کردن `http://localhost:5000/futures`
- دابل کلیک روی یک ارز
- بررسی نمایش چارت
- تست محاسبه قیمت‌ها
- تست ارسال معامله

## نکات مهم

1. **API Endpoints:** ممکن است نیاز به تنظیم دقیق‌تر endpointهای Nobitex باشد بسته به نسخه API
2. **Symbol Format:** سیستم به صورت خودکار فرمت symbol را تبدیل می‌کند
3. **Authentication:** اگر authentication با خطا مواجه شد، برای public endpoints (قیمت، چارت) ادامه می‌دهد
4. **Error Handling:** تمام خطاها لاگ می‌شوند و به کاربر نمایش داده می‌شوند

## عیب‌یابی

### مشکل: "Nobitex trader not available"
- بررسی کنید که `nobitex_trader.py` در همان دایرکتوری باشد
- بررسی کنید که تمام dependencies نصب شده باشند

### مشکل: "Could not get price"
- بررسی اتصال اینترنت
- بررسی اینکه symbol به درستی وارد شده باشد
- بررسی API keys

### مشکل: "Authentication failed"
- بررسی API keys
- بررسی اینکه API keys معتبر باشند
- برای public endpoints (قیمت، چارت) authentication ضروری نیست

## پشتیبانی

در صورت بروز مشکل:
1. بررسی لاگ‌ها در کنسول
2. بررسی لاگ‌های سرور
3. بررسی مستندات API Nobitex

---

**تاریخ تغییر:** 2024  
**نسخه:** 2.0

