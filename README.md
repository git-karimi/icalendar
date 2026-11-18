# تقویم شمسی برای آیفون

تقویم‌های قابل اشتراک (Subscribe) برای تقویم آیفون، مک و گوگل:

| تقویم | فارسی | لاتین |
|---|---|---|
| تقویم کامل (همه با هم) | `all-fa.ics` | `all-en.ics` |
| تاریخ شمسی هر روز | `dates-fa.ics` | `dates-en.ics` |
| تعطیلات رسمی ایران | `holidays-fa.ics` | `holidays-en.ics` |
| جشن‌ها و مناسبت‌های ایرانی | `events-fa.ics` | `events-en.ics` |

بازه: یک سال گذشته تا پنج سال آینده. هر ماه خودکار به‌روز می‌شود.

## ویرایش مناسبت‌ها (ادمین)

1. در GitHub فایل `data/events.yaml` را باز کن و روی آیکون مداد بزن.
2. یک خط مثل بقیه اضافه یا حذف کن، مثلاً:
   `- {month: 8, day: 4, fa: "زادروز محمدرضا شاه", en: "Birthday of Mohammad Reza Shah"}`
3. Commit changes را بزن. چند دقیقه بعد تقویم همهٔ کاربرها آپدیت می‌شود.

فایل‌های دیگر:

- `data/holidays.yaml`: تعطیلات رسمی (خورشیدی و قمری)
- `data/config.yaml`: آدرس سایت، بازهٔ سال‌ها و آخرین سال تقویم رسمی (`official_last_year`)
- `data/lunar_months.json`: شروع ماه‌های قمری رسمی ایران

وقتی تقویم رسمی سال بعد منتشر شد، `official_last_year` را یکی زیاد کن و در صورت نیاز تاریخ شروع ماه‌های قمری جدید را به `lunar_months.json` اضافه کن.

## ساخت محلی

```
pip install -r requirements.txt
python scripts/build.py
```

خروجی در پوشهٔ `site/` ساخته می‌شود.

## منابع داده

- شروع ماه‌های قمری رسمی ایران: [persian-calendar/calendar](https://github.com/persian-calendar/calendar) و [roozbehp/qamari](https://github.com/roozbehp/qamari) (CC0)
- فهرست تعطیلات رسمی: [persian-calendar/events](https://github.com/persian-calendar/events) (CC0)
- تعطیلات قمری بعد از آخرین تقویم رسمی، با محاسبهٔ نجومی تخمین زده می‌شوند و «تقریبی» علامت می‌خورند.
