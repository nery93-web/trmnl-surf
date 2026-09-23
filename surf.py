import json
import os
import re
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

TRMNL_WEBHOOK_URL = (
    "https://trmnl.com/api/custom_plugins/37c611d4-1b97-4e82-935d-48867bf20424"
)
CONFIG_FILE = "config.json"

BEACHES = {
    # צפון
    "betzet": "בצת",
    "nahariya": "נהריה - סוקולוב",
    "shavei-zion": "שבי ציון",
    "akko": "עכו - חוף הסוסים",
    "kiriat-haim": "קריית חיים",
    "haifa-peak": "חיפה - הפיק",
    "haifa-backdoor": "חיפה - בקדור",
    "haifa-casino": "חיפה - קזינו בת גלים",
    "haifa-kedarim": "חיפה - קדרים",
    "atlit": "עתלית",
    "neve-yam": "נווה ים",
    "habonim": "הבונים",
    "nahsholim": "נחשולים",
    "dor": "דור / טנטורה",
    "jisr": "ג'סר א-זרקא",

    # מרכז / שרון
    "caesarea": "קיסריה",
    "sdot-yam": "שדות ים",
    "olga": "חוף אולגה (חדרה)",
    "michmoret": "מכמורת",
    "beit-yanai": "בית ינאי",
    "blue-bay": "נתניה - בלוי ביי",
    "sironit": "נתניה - סירונית",
    "poleg": "נתניה - פולג",
    "herzliya": "הרצליה - דבוש / מרינה",
    "herzliya-zabulon": "הרצליה - זבולון",

    # תל אביב והסביבה
    "hatsuk": "תל אביב - הצוק",
    "country": "תל אביב - קאנטרי",
    "tel-baruch": "תל אביב - תל ברוך",
    "hilton": "תל אביב - הילטון",
    "gordon": "תל אביב - גורדון",
    "dolphinarium": "תל אביב - דולפינריום",
    "maravi": "תל אביב - חוף מערבי",
    "bat-yam": "בת ים - החוף הנפרד",
    "rishon": "ראשון לציון",
    "palmachim": "פלמחים",

    # דרום
    "ashdod": "אשדוד - חוף הקשתות",
    "ashdod-gil": "אשדוד - חוף גיל",
    "ashdod-mi-ami": "אשדוד - מי עמי",
    "ashdod-citadel": "אשדוד - המצודה",
    "ashqelon": "אשקלון - דלילה",
    "zikim": "זיקים",

    # מים מתוקים / אחר
    "kinneret": "כנרת",
    "eilat": "אילת",
}


def get_active_beach():
  """מזהה את החוף מתוך הפרמטר שנשלח או שומר אותו בקובץ הקונפיגורציה"""
  if len(sys.argv) > 1 and sys.argv[1].strip():
    beach = sys.argv[1].strip()
    try:
      with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"beach": beach}, f)
    except Exception:
      pass
    return beach

  if os.path.exists(CONFIG_FILE):
    try:
      with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("beach", "olga")
    except Exception:
      pass
  return "olga"


def get_wax(temp_str):
  try:
    val = float(re.search(r"[\d\.]+", temp_str).group())
    if val >= 24:
      return "שעוות קיץ"
    elif val >= 18:
      return "שעוות מעבר"
    else:
      return "שעוות חורף"
  except Exception:
    return "שעוות מעבר"


def extract_summary_and_astro(anchor):
  curr = anchor
  summary_txt = ""
  astro_txt = ""

  for _ in range(40):
    if not curr:
      break
    t = curr.get_text(" ", strip=True) if hasattr(curr, "get_text") else ""

    if "זריחה" in t and "שקיעה" in t:
      astro_m = re.search(
          r"זריחה:\s*(\d+:\d+).*?שקיעה:\s*(\d+:\d+).*?ירח:\s*(\d+%)", t
      )
      if astro_m:
        astro_txt = f"זריחה {astro_m.group(1)} · שקיעה {astro_m.group(2)} · ירח {astro_m.group(3)}"

      if "בבוקר" in t:
        raw_summary = "בבוקר" + t.split("בבוקר")[1].split("זריחה")[0]
        clean_s = re.sub(
            r'[\U00010000-\U0010ffff\u2600-\u27ff\u2b50\u2190-\u21ff]',
            '',
            raw_summary,
        )
        summary_txt = re.sub(r"\s+", " ", clean_s).strip(" -.")

      return summary_txt, astro_txt

    curr = curr.next_element
  return "", ""


def get_tides_data():
  try:
    url = "https://gosurf.co.il/tides"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    res = requests.get(url, headers=headers, timeout=5)
    if res.status_code == 200:
      soup = BeautifulSoup(res.text, "html.parser")
      page_text = soup.get_text()

      raw_matches = re.findall(r"(גאות|שפל)[^\d]*(\d{1,2}:\d{2})", page_text)
      highs, lows = [], []
      for t_type, t_time in raw_matches:
        if t_type == "גאות" and t_time not in highs:
          highs.append(t_time)
        elif t_type == "שפל" and t_time not in lows:
          lows.append(t_time)

      if not highs and not lows:
        all_times = re.findall(r"\b(\d{1,2}:\d{2})\b", page_text)
        if len(all_times) >= 2:
          return f" · גאות {all_times[1]} · שפל {all_times[0]}"

      parts = []
      if highs:
        parts.append(f"גאות {', '.join(highs[:2])}")
      if lows:
        parts.append(f"שפל {', '.join(lows[:2])}")

      if parts:
        return " · " + " · ".join(parts)
  except Exception as e:
    print(f"Notice: Could not fetch tides ({e})")
  return ""


def get_live_data(beach_slug):
  url = f"https://gosurf.co.il/forecast/{beach_slug}"
  headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

  print(f"1. מוריד נתונים מעודכנים עבור {beach_slug} מ-GoSurf...", flush=True)
  res = requests.get(url, headers=headers, timeout=10)
  res.raise_for_status()

  soup = BeautifulSoup(res.text, "html.parser")
  page_text = soup.get_text()

  tides_txt = get_tides_data()

  wt, at = "28°C", "29°C"
  wm = re.search(r"מים\s*[\.\:]?\s*([\d\.]+°?)", page_text)
  if wm:
    wt = wm.group(1) if "°" in wm.group(1) else wm.group(1) + "°C"

  am = re.search(r"אוויר\s*[\.\:]?\s*([\d\.]+°?)", page_text)
  if am:
    at = am.group(1) if "°" in am.group(1) else am.group(1) + "°C"

  # חישוב השעה לפי שעון ישראל
  current_hour = datetime.now(ZoneInfo("Asia/Jerusalem")).hour
  forecast = []
  current_data = {}

  for d in range(7):
    anchor = soup.find(id=f"day_{d}")
    if not anchor:
      continue

    h2 = anchor.find_next("h2")
    h2_text = h2.text.strip() if h2 else ""
    parts = h2_text.split()
    day_name = parts[0] if parts else (f"היום" if d == 0 else f"יום {d}")
    day_date = parts[1] if len(parts) > 1 else ""

    summary_txt, astro_txt = extract_summary_and_astro(anchor)

    wave_12, desc_12, swell_12, wind_12, icon_12 = 0, "", "", "", ""
    day_rows, star_details = [], []

    curr = anchor.next_sibling
    while curr:
      if hasattr(curr, "id") and curr.id == f"day_{d+1}":
        break

      if hasattr(curr, "select"):
        for tr in curr.select(".chart_tr, tr"):
          row_text = " ".join(tr.stripped_strings)
          hm = re.search(r"\b(00|03|06|09|12|15|18|21)\b", row_text)
          if not hm:
            continue
          hour_str = hm.group(1)

          wm_val = re.search(r'(\d+(?:\s*-\s*\d+)?\s*ס[״"]מ)', row_text)
          wave_txt = wm_val.group(1) if wm_val else ""

          wave_desc = ""
          for w in [
              "ברך",
              "קרסול",
              "חזה",
              "ראש",
              "ים גלי",
              "ים נוח",
              "מפתח",
              "פלטה",
          ]:
            if w in row_text:
              wave_desc = w
              break

          ws = re.search(r'(\d+\s*קמ[״"]ש)', row_text)
          wd = re.search(
              r"\b(צפון מערבית|דרום מערבית|צפון מזרחית|דרום"
              r" מזרחית|מערבית|מזרחית|צפונית|דרומית)\b",
              row_text,
          )

          w_dir_short = wd.group(1) if wd else ""
          w_dir_short = (
              w_dir_short.replace("צפון מערבית", "צפ-מע")
              .replace("דרום מערבית", "דר-מע")
              .replace("צפון מזרחית", "צפ-מז")
              .replace("דרום מזרחית", "דר-מז")
          )
          wind_str = f"{w_dir_short} {ws.group(1) if ws else ''}".strip()

          sd = re.search(
              r"\b(צפון מערבי|דרום מערבי|צפון מזרחי|דרום"
              r" מזרחי|מערבי|מזרחי|צפוני|דרומי)\b",
              row_text,
          )
          sp = re.search(r"(\d+(?:\.\d+)?\s*שניות)", row_text)
          swell_str = (
              f"{sd.group(1) if sd else ''} ({sp.group(1) if sp else ''})".strip()
          )

          w_icon = ""
          if any(w in row_text for w in ["גשם", "ממטרים", "סערה"]):
            w_icon = "☂"

          if "star1.svg" in str(tr):
            star_details.append(
                f"{hour_str}:00 ({wave_desc})"
                if wave_desc
                else f"{hour_str}:00"
            )

          day_rows.append({
              "hour_num": int(hour_str),
              "hour": hour_str,
              "wave": wave_txt,
              "desc": wave_desc,
              "wind": wind_str,
              "swell": swell_str,
              "icon": w_icon,
          })

          if hour_str in ["12", "12:00"]:
            nums = re.findall(r"\d+", wave_txt)
            if nums:
              wave_12 = int(nums[-1])
            desc_12 = wave_desc if wave_desc else ""
            if swell_str:
              swell_12 = swell_str
            if wind_str:
              wind_12 = wind_str
            icon_12 = w_icon
      curr = curr.next_sibling

    if d == 0 and day_rows:
      closest = max(
          [r for r in day_rows if r["hour_num"] <= current_hour],
          key=lambda x: x["hour_num"],
          default=day_rows[0],
      )
      current_data = {
          "day_name": day_name,
          "date": day_date,
          "air_temp": at,
          "water_temp": wt,
          "wax": get_wax(wt),
          "summary": summary_txt,
          "astro": astro_txt,
          "tides": tides_txt,
          "stars": ", ".join(star_details) if star_details else "",
          "hour": closest["hour"],
          "wave": closest["wave"],
          "desc": closest["desc"],
          "wind": closest["wind"],
          "swell": closest["swell"],
      }

    stars_formatted = f"★ {', '.join(star_details)}" if star_details else ""

    forecast.append({
        "day": day_name,
        "date": day_date,
        "wave": wave_12 if wave_12 > 0 else 40,
        "desc": desc_12 if desc_12 else "ים גלי",
        "swell": swell_12
        if swell_12
        else (day_rows[0]["swell"] if day_rows else ""),
        "wind": wind_12
        if wind_12
        else (day_rows[0]["wind"] if day_rows else ""),
        "stars": stars_formatted,
        "icon": icon_12,
    })

  return {
      "beach_name": BEACHES.get(beach_slug, beach_slug),
      "battery": 100,
      "current": current_data,
      "forecast": forecast,
  }


if __name__ == "__main__":
  active_beach = get_active_beach()
  live_data = get_live_data(active_beach)
  print(
      f"נאספו {len(live_data['forecast'])} ימים עבור {live_data['beach_name']}. שולח ל-TRMNL...",
      flush=True,
  )

  payload = {"merge_variables": live_data}
  res = requests.post(TRMNL_WEBHOOK_URL, json=payload, timeout=10)
  print(f"תגובת השרת: {res.status_code} - {res.text}", flush=True)
