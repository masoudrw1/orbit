# ساخت ریپوزیتوری Orbit در GitHub

کد محلی و ریپوزیتوری GitHub دو چیز جدا هستند. داشتن پوشهٔ `.git` یعنی تاریخچهٔ محلی؛
تا وقتی ریپوزیتوری آنلاین ساخته و push نشده، چیزی در GitHub منتشر نشده است.

## قبل از اولین انتشار

- README را بخوان؛ نسخه فعلی alpha و محدودیت‌ها باید روشن باشند.
- مجوز فعلی کد MIT است؛ نام صاحب اثر فعلاً عمومی «Orbit contributors» است.
- `.venv`، `.models`، `.runtime`، فایل صوتی و تنظیمات شخصی نباید وارد Git شوند.
- در Git وضعیت و diff را ببین. فایل‌های source، تست‌ها و مستندات باید در فهرست باشند.
- مدل Vosk و وابستگی‌ها جدا از کد مجوز خودشان را دارند.

```bash
git status
git diff
```

## هویت commit

اگر Git موقع commit گفت نام و ایمیل مشخص نیست، برای همین ریپوزیتوری تنظیم کن:

```bash
git config user.name "YOUR_NAME"
git config user.email "YOUR_GITHUB_NOREPLY_EMAIL"
```

مقادیر بالا نمونه هستند و باید جایگزین شوند. ایمیل noreply را از تنظیمات ایمیل GitHub خودت بگیر.
این تنظیمات را بدون `--global` فقط برای همین پروژه اعمال می‌کنیم.

## ساخت آنلاین

اگر اتصال GitHub در محیط کار فعال شود، ادامهٔ ساخت ریپوزیتوری را می‌توان از همان اتصال انجام داد.
صرف پیشنهاد اتصال به معنی اتصال موفق نیست.

مسیر دستی طبق [مستندات GitHub](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository):

۱. وارد GitHub شو و New repository را باز کن.
۲. Owner را حساب خودت و نام را `orbit` بگذار، اگر در حسابت آزاد است.
۳. چون پروژه اپن‌سورس است، Public انتخاب کن.
۴. README، gitignore و license را در این فرم ایجاد نکن؛ در کد محلی داریم.
۵. Create repository را بزن و نشانی دقیق مخزن خودت را بردار.

در پوشهٔ همین پروژه:

```bash
git add .
git commit -m "Start Orbit alpha foundation"
```

سپس نشانی نمونهٔ زیر را با نشانی واقعی ریپوزیتوری خودت جایگزین کن:

```bash
git remote add origin https://github.com/YOUR_USERNAME/orbit.git
git push -u origin main
```

اگر origin از قبل وجود دارد، دوباره آن را اضافه نکن. ابتدا `git remote -v` را ببین.
برای احراز هویت از اتصال رسمی، GitHub CLI یا SSH استفاده کن؛ توکن را در کد یا نشانی remote نگذار.
اگر commit اولیه از قبل ساخته شده باشد، تغییرات بعدی را با پیام جدید commit کن.
