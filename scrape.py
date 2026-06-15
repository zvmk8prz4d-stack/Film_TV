#!/usr/bin/env python3
"""
Palinsesto film TV - scraper.
Fonte palinsesto: guidatv.org (HTML statico, 1 fetch per canale = giornata intera).
Arricchimento trama completa: TMDB (opzionale, via TMDB_API_KEY).
Output: data/palinsesto.json
"""
import json, os, re, time, sys, urllib.parse, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
BASE = "https://guidatv.org/canali/{slug}"
TMDB_KEY = os.environ.get("TMDB_API_KEY", "").strip()
ROME = timezone(timedelta(hours=2))  # CEST; il sito e' IT, l'offset preciso non e' critico per la data

# (etichetta UI, gruppo, slug guidatv.org)
CHANNELS = [
    # --- SKY CINEMA / film ---
    ("Sky Cinema Uno", "sky", "sky-cinema-uno-hd"),
    ("Sky Cinema Due", "sky", "sky-cinema-due-hd"),
    ("Sky Cinema Collection", "sky", "sky-cinema-collection-hd"),
    ("Sky Cinema Action", "sky", "sky-cinema-action-hd"),
    ("Sky Cinema Comedy", "sky", "sky-cinema-comedy-hd"),
    ("Sky Cinema Drama", "sky", "sky-cinema-drama-hd"),
    ("Sky Cinema Romance", "sky", "sky-cinema-romance-hd"),
    ("Sky Cinema Suspense", "sky", "sky-cinema-suspense-hd"),
    ("Sky Cinema Family", "sky", "sky-cinema-family-hd"),
    ("Sky Investigation", "sky", "sky-investigation-hd"),
    ("Sky Crime", "sky", "sky-crime"),
    # --- TV IN CHIARO ---
    ("Rai 1", "chiaro", "rai-1"),
    ("Rai 2", "chiaro", "rai-2"),
    ("Rai 3", "chiaro", "rai-3"),
    ("Rai 4", "chiaro", "rai-4"),
    ("Rai 5", "chiaro", "rai-5"),
    ("Rai Movie", "chiaro", "rai-movie"),
    ("Rai Premium", "chiaro", "rai-premium"),
    ("Rai Gulp", "chiaro", "rai-gulp"),
    ("Rai YoYo", "chiaro", "rai-yoyo"),
    ("Rete 4", "chiaro", "rete4"),
    ("Canale 5", "chiaro", "canale-5"),
    ("Italia 1", "chiaro", "italia-uno"),
    ("Italia 2", "chiaro", "mediaset-italia-due"),
    ("La7", "chiaro", "la7"),
    ("La7 Cinema", "chiaro", "la7-cinema"),
    ("TV8", "chiaro", "tv8"),
    ("Nove", "chiaro", "nove"),
    ("Iris", "chiaro", "iris"),
    ("Cielo", "chiaro", "cielo"),
    ("20 Mediaset", "chiaro", "canale-20"),
    ("TwentySeven", "chiaro", "mediaset-27"),
    ("Cine34", "chiaro", "cine-34"),
    ("La5", "chiaro", "la-5"),
    ("Top Crime", "chiaro", "topcrime"),
    ("Focus", "chiaro", "focus"),
    ("Giallo", "chiaro", "giallo"),
    ("Real Time", "chiaro", "real-time"),
    ("Mediaset Extra", "chiaro", "mediaset-extra"),
    ("TV2000", "chiaro", "tv2000"),
    ("Boing", "chiaro", "boing"),
    ("Cartoonito", "chiaro", "cartoonito"),
    ("Frisbee", "chiaro", "frisbee"),
    ("K2", "chiaro", "k2"),
]

# Numero canale (LCN). Chiaro = digitale terrestre; Sky = numerazione bouquet Sky.
LCN = {
    "Sky Cinema Uno":301, "Sky Cinema Due":302, "Sky Cinema Collection":303,
    "Sky Cinema Action":305, "Sky Cinema Comedy":306, "Sky Cinema Drama":304,
    "Sky Cinema Romance":307, "Sky Cinema Suspense":308, "Sky Cinema Family":309,
    "Sky Investigation":114, "Sky Crime":110,
    "Rai 1":1, "Rai 2":2, "Rai 3":3, "Rai 4":21, "Rai 5":23,
    "Rai Movie":24, "Rai Premium":25, "Rai Gulp":42, "Rai YoYo":43,
    "Rete 4":4, "Canale 5":5, "Italia 1":6, "Italia 2":49,
    "La7":7, "La7 Cinema":10, "TV8":8, "Nove":9,
    "Iris":22, "Cielo":26, "20 Mediaset":20, "TwentySeven":27, "Cine34":34,
    "La5":30, "Top Crime":39, "Focus":35, "Giallo":38, "Real Time":31,
    "Mediaset Extra":55, "TV2000":28, "Boing":40, "Cartoonito":46,
    "Frisbee":44, "K2":41,
}

GENRE_LABELS = {"Film","Serie TV","Serie","Telefilm","Programma","Documentario","Show",
                "Cartoni","Sport","Notiziario","Rubrica","Soap Opera","Film TV","Miniserie",
                "Talk Show","Intrattenimento","Reality","Musica","Cartoni Animati","Fiction"}

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1.5 * (i + 1))
        except Exception:
            time.sleep(1.5 * (i + 1))
    return None

def parse_duration(s):
    if not s: return None
    h = re.search(r'(\d+)\s*ore', s); m = re.search(r'(\d+)\s*min', s)
    tot = (int(h.group(1))*60 if h else 0) + (int(m.group(1)) if m else 0)
    return tot or None

def poster_from_img(img):
    if not img: return None
    src = img.get("srcSet") or img.get("srcset") or img.get("src") or ""
    m = re.search(r'url=(https%3A[^&\s]+)', src)
    if m:
        return urllib.parse.unquote(m.group(1))
    m2 = re.search(r'(https?://[^\s"]+\.jpg)', src)
    return m2.group(1) if m2 else None

def parse_channel(html):
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select('[data-testid="channel-program-card"]')
    # gli orari stanno in h3.hour, nello stesso ordine delle card
    hours = [x.get_text(strip=True) for x in soup.select('h3.hour')]
    progs = []
    for i, card in enumerate(cards):
        texts = [t.strip() for t in card.stripped_strings if t.strip()]
        if not texts:
            continue
        title = texts[0]
        year  = next((t for t in texts if re.fullmatch(r'(19|20)\d{2}', t)), None)
        durtxt= next((t for t in texts if re.search(r'\bore\b|\bmin\b', t)), None)
        genre = next((t for t in texts if t in GENRE_LABELS), None)
        rating= next((t for t in texts if re.fullmatch(r'\d\.\d', t)), None)
        plot  = next((t for t in texts if len(t) > 40), None)
        hour  = hours[i] if i < len(hours) else None
        progs.append({
            "time": hour,
            "title": title,
            "year": int(year) if year else None,
            "duration_min": parse_duration(durtxt),
            "genre": genre,
            "rating": float(rating) if rating else None,
            "plot_short": plot,
            "plot": plot,                       # default = breve; TMDB lo sovrascrive
            "poster": poster_from_img(card.find("img")),
        })
    return progs

# ---------- TMDB enrichment ----------
_tmdb_cache = {}
_genre_map = None

# rinomina/pulisce alcuni nomi genere TMDB poco felici in italiano
GENRE_FIX = {
    "televisione film": "Film TV",
    "fantascienza": "Fantascienza",
    "azione e avventura": "Azione e Avventura",
}
def clean_genre(name):
    if not name:
        return name
    n = name.strip()
    low = n.lower()
    if low in GENRE_FIX:
        return GENRE_FIX[low]
    # altrimenti capitalizza la prima lettera lasciando il resto
    return n[0].upper() + n[1:] if n else n

def tmdb_genre_map():
    """Scarica una volta la lista id->nome generi (in italiano)."""
    global _genre_map
    if _genre_map is not None:
        return _genre_map
    _genre_map = {}
    if not TMDB_KEY:
        return _genre_map
    try:
        url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={TMDB_KEY}&language=it-IT"
        data = json.loads(fetch(url) or "{}")
        _genre_map = {g["id"]: clean_genre(g["name"]) for g in data.get("genres", [])}
    except Exception:
        _genre_map = {}
    return _genre_map

def tmdb_lookup(title, year):
    """Ritorna dict con trama completa, generi, attori principali, trailer YouTube.
    Usa 2 chiamate: search (per l'id) + details con append_to_response (credits+videos)."""
    empty = {"plot": None, "genres": [], "cast": [], "trailer": None,
             "director": None, "age": None}
    if not TMDB_KEY:
        return empty
    key = (title, year)
    if key in _tmdb_cache:
        return _tmdb_cache[key]
    gmap = tmdb_genre_map()
    q = urllib.parse.quote(title)
    search_url = (f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_KEY}"
                  f"&language=it-IT&query={q}" + (f"&year={year}" if year else ""))
    res = dict(empty)
    try:
        data = json.loads(fetch(search_url) or "{}")
        results = data.get("results", [])
        if results:
            r = results[0]
            mid = r.get("id")
            res["plot"] = (r.get("overview") or "").strip() or None
            res["genres"] = [gmap.get(i) for i in r.get("genre_ids", []) if gmap.get(i)]
            if mid:
                det_url = (f"https://api.themoviedb.org/3/movie/{mid}?api_key={TMDB_KEY}"
                           f"&language=it-IT&append_to_response=credits,videos,release_dates")
                det = json.loads(fetch(det_url) or "{}")
                creds = det.get("credits", {})
                cast = creds.get("cast", [])
                res["cast"] = [c.get("name") for c in cast[:5] if c.get("name")]
                # regista (può essercene più d'uno)
                dirs = [c.get("name") for c in creds.get("crew", [])
                        if c.get("job")=="Director" and c.get("name")]
                if dirs:
                    res["director"] = ", ".join(dict.fromkeys(dirs))
                # trailer YouTube
                vids = det.get("videos", {}).get("results", [])
                yt = [v for v in vids if v.get("site")=="YouTube"]
                pick = next((v for v in yt if v.get("type")=="Trailer"), None) or (yt[0] if yt else None)
                if pick and pick.get("key"):
                    res["trailer"] = "https://www.youtube.com/watch?v="+pick["key"]
                # età consigliata: cerca certificazione IT, poi US come fallback
                res["age"] = pick_certification(det.get("release_dates", {}).get("results", []))
    except Exception:
        pass
    _tmdb_cache[key] = res
    return res

def pick_certification(results):
    """Estrae la classificazione per età e la normalizza in formato '14+'/'Tutti'.
    Preferisce la certificazione italiana, poi quella USA."""
    # mappa codici -> etichetta età minima
    IT_MAP = {"T":"Tutti", "BA":"Tutti", "VM14":"14+", "VM18":"18+", "14":"14+", "18":"18+"}
    US_MAP = {"G":"Tutti", "PG":"Tutti", "PG-13":"13+", "R":"17+", "NC-17":"18+"}
    by_country = {r.get("iso_3166_1"): r.get("release_dates", []) for r in results}
    for cc, m in (("IT", IT_MAP), ("US", US_MAP)):
        for rd in by_country.get(cc, []):
            cert = (rd.get("certification") or "").strip().upper()
            if not cert:
                continue
            if cert in m:
                return m[cert]
            # codici IT puramente numerici tipo "14"/"18"
            if cc=="IT" and cert.isdigit():
                return cert+"+"
    return None

def main():
    today = datetime.now(ROME).date().isoformat()
    out = {"updated_at": datetime.now(ROME).isoformat(timespec="seconds"),
           "date": today, "source": "guidatv.org",
           "tmdb_enriched": bool(TMDB_KEY), "channels": []}
    ok = miss = 0
    for label, group, slug in CHANNELS:
        html = fetch(BASE.format(slug=slug))
        if not html:
            print(f"  SKIP {label} ({slug}) - no html", file=sys.stderr)
            miss += 1
            continue
        progs = parse_channel(html)
        # arricchimento TMDB solo per i Film (le serie hanno trame per-episodio, fuori scope)
        for p in progs:
            p["genres"] = []; p["cast"] = []; p["trailer"] = None
            p["director"] = None; p["age"] = None
            if p["genre"] == "Film" and p["title"]:
                info = tmdb_lookup(p["title"], p["year"])
                if info["plot"]:     p["plot"]     = info["plot"]
                if info["genres"]:   p["genres"]   = info["genres"]
                if info["cast"]:     p["cast"]     = info["cast"]
                if info["trailer"]:  p["trailer"]  = info["trailer"]
                if info["director"]: p["director"] = info["director"]
                if info["age"]:      p["age"]      = info["age"]
                time.sleep(0.05)  # gentile con l'API
        out["channels"].append({"name": label, "group": group, "slug": slug,
                                 "lcn": LCN.get(label), "programs": progs})
        ok += 1
        print(f"  OK {label}: {len(progs)} programmi", file=sys.stderr)
        time.sleep(0.4)  # gentile con guidatv.org
    os.makedirs("data", exist_ok=True)
    with open("data/palinsesto.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\nFatto: {ok} canali ok, {miss} mancanti -> data/palinsesto.json", file=sys.stderr)

if __name__ == "__main__":
    main()
