"""Build the blog pages from the old WordPress export.

Run from the repo root:  python3 scripts/build_blog.py
Reads  blog-source/posts.json (the kept posts only, taken from the WordPress export with
       python3 scripts/build_blog.py --from-export path/to/export.xml; the full export is
       not stored here because it holds private details like email addresses)
Writes public/<post-slug>/index.html, public/blog/index.html, public/category/<cat>/index.html

The post text is copied word for word. Only the old WordPress formatting is
cleaned (shortcodes, inline styles, empty headings) so it fits the new design.
"""
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "blog-source" / "posts.json"
PUBLIC = ROOT / "public"
SITE = "https://teamonefitness.com.au"
NS = {
    "wp": "http://wordpress.org/export/1.2/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}

# The 6 categories Yves approved (26 Oct 2026), at their old addresses.
CATEGORIES = {
    "workouts": "Workouts",
    "fitness": "Fitness",
    "nutrition": "Nutrition",
    "recipes": "Recipes",
    "health": "Health",
    "motivation": "Motivation",
}

# Posts we keep, with their new categories (one or two each).
# Posts not listed here are redirected at launch (see blog-keep-or-redirect.md).
KEEP = {
    "ciabatta-or-is-it-tabata": ["workouts", "fitness"],
    "the-kettlebell-swing": ["workouts", "fitness"],
    "pushing-to-the-limits": ["fitness", "motivation"],
    "anti-aging-foods": ["nutrition", "health"],
    "benefits-bodyweight-exercises": ["workouts", "fitness"],
    "squats-benefits": ["fitness", "workouts"],
    "keeping-fit-on-holiday": ["fitness", "workouts"],
    "finding-balance-in-life": ["health", "motivation"],
    "myths-around-cardio-training": ["fitness", "workouts"],
    "slow-versus-rapid-weight-loss": ["nutrition", "health"],
    "portion-control": ["nutrition", "health"],
    "getting-the-right-results": ["fitness", "motivation"],
    "banana-blueberry-smoothie": ["recipes", "nutrition"],
    "how-to-get-through-a-tough-workout": ["fitness", "motivation"],
    "how-to-reveal-your-oblique-muscles": ["fitness", "workouts"],
    "training-in-the-right-winter-gear": ["fitness"],
    "dealing-with-injuries": ["health", "fitness"],
    "fire-up-the-central-nervous-system-before-a-workout": ["fitness", "workouts"],
    "measure-workout-intensity": ["fitness"],
    "motivation-motivation-motivation": ["motivation", "fitness"],
    "train-with-intensity": ["fitness", "motivation"],
    "how-to-get-a-six-pack": ["fitness"],
    "foods-to-boost-your-metabolism": ["nutrition"],
    "tips-on-how-to-make-waking-up-easier": ["motivation", "health"],
    "hitting-the-fat-burning-zone": ["fitness"],
    "protein-sources-for-weight-loss": ["nutrition"],
    "seven": ["workouts"],
    "the-power-of-protein": ["nutrition"],
    "why-we-get-out-of-bed-at-5-30am": ["motivation", "fitness"],
    "home-leg-workout": ["workouts"],
    "get-motivated-and-stay-motivated": ["motivation", "health"],
    "how-water-can-improve-weight-loss": ["nutrition", "health"],
    "the-best-and-worst-alcohol-drinks-for-weight-loss": ["nutrition", "health"],
    "summer-bodies-are-built-in-winter": ["fitness", "motivation"],
    "some-tips-when-fast-food-is-unavoidable": ["nutrition", "health"],
    "get-fit-for-summer-fast": ["fitness", "health"],
    "nutritional-guidelines": ["nutrition", "health"],
    "benefits-of-beach-training": ["fitness", "health"],
    "vegetarian-stir-fried-vegetables-and-quinoa-dish": ["recipes", "nutrition"],
    "what-are-your-new-years-resolutions": ["motivation"],
    "simple-changes-for-a-better-healthier-life": ["health", "motivation"],
    "things-not-to-eat": ["nutrition", "health"],
    "amrap-five-plus": ["workouts"],
    "get-your-butt-of-your-chair": ["health", "motivation"],
    "every-minute-minute": ["workouts"],
    "never-miss-a-monday-training-session": ["motivation"],
    "anzac-workout": ["workouts"],
}

# Old photo files are not available, so a few old images are swapped for Yves's own photos.
IMAGE_SWAPS = {
    "IMG_6085-web2-300x223.jpg": ('/assets/photos/community-group-1200.webp', 1200, 900),
}

BLOCK = re.compile(r"^\s*<(h[1-6]|ul|ol|li|div|p|table|blockquote|figure|img|a [^>]*><img)", re.I)


def clean(body):
    body = body.replace("\r\n", "\n").replace("\xa0", " ")
    body = re.sub(r"\[/?su_\w+[^\]]*\]", "", body)               # old plugin shortcodes
    body = re.sub(r"\[/?caption[^\]]*\]", "", body)
    body = re.sub(r"</?(span|div|font)[^>]*>", "", body)          # wrappers that only held styling
    body = re.sub(r'\s(style|class|id|align)="[^"]*"', "", body)
    body = re.sub(r"<(/?)h1\b", r"<\1h2", body)                   # the page already has its own H1
    body = re.sub(r"<(h[1-6])>\s*(&nbsp;|\s)*</\1>", "", body)    # empty headings
    body = re.sub(r"^\s*(&nbsp;)?\s*$", "", body, flags=re.M)
    body = re.sub(r'href="https?://(www\.)?teamonefitness\.com\.au/', 'href="/', body)
    body = re.sub(r"<(h[1-6])>\s+", r"<\1>", body)                # headings split over two lines
    body = re.sub(r"\s+</(h[1-6])>", r"</\1>", body)
    # old image -> new photo
    def swap(m):
        tag = m.group(0)
        for old, (new, w, h) in IMAGE_SWAPS.items():
            if old in tag:
                alt = re.search(r'alt="([^"]*)"', tag)
                return f'<img src="{new}" alt="{alt.group(1) if alt else ""}" width="{w}" height="{h}" loading="lazy">'
        return ""
    body = re.sub(r'<a [^>]*>\s*(<img[^>]*>)\s*</a>', r"\1", body)
    body = re.sub(r"<img[^>]*>", swap, body)
    # external links open normally but are marked as not endorsed
    body = re.sub(r'<a href="(https?://(?!teamonefitness)[^"]+)"', r'<a href="\1" rel="noopener"', body)
    # WordPress-style paragraphs: blank line = new paragraph, single line break = <br>
    out = []
    for block in re.split(r"\n\s*\n", body):
        block = block.strip()
        if not block:
            continue
        if BLOCK.match(block):
            # lines of loose text between block tags still need paragraphs
            parts = []
            for line in block.split("\n"):
                s = line.strip()
                if not s:
                    continue
                parts.append(s if BLOCK.match(s) or s.startswith("</") or s.startswith("<li") else f"<p>{s}</p>")
            out.append("\n".join(parts))
        else:
            out.append("<p>" + "<br>\n".join(l.strip() for l in block.split("\n") if l.strip()) + "</p>")
    body = "\n".join(out)
    body = re.sub(r"<p>\s*</p>", "", body)
    return body


def text_only(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).split()


def nice_date(d):
    return d.strftime("%-d %B %Y")


def extract(export_path):
    """Copy the public fields of the kept posts from the WordPress export into posts.json."""
    import json
    tree = ET.parse(export_path)
    out = []
    for item in tree.getroot().findall("channel/item"):
        if item.find("wp:post_type", NS).text != "post" or item.find("wp:status", NS).text != "publish":
            continue
        slug = item.find("wp:post_name", NS).text
        if slug not in KEEP:
            continue
        meta = {m.find("wp:meta_key", NS).text: (m.find("wp:meta_value", NS).text or "")
                for m in item.findall("wp:postmeta", NS)}
        out.append({
            "slug": slug,
            "title": item.find("title").text,
            "date": item.find("wp:post_date", NS).text,
            "seo_title": meta.get("_yoast_wpseo_title", ""),
            "seo_description": meta.get("_yoast_wpseo_metadesc", ""),
            "content": item.find("content:encoded", NS).text or "",
        })
    out.sort(key=lambda p: p["date"])
    SRC.parent.mkdir(exist_ok=True)
    SRC.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"saved {len(out)} posts to {SRC.relative_to(ROOT)}")


def load():
    import json
    posts = []
    for src in json.loads(SRC.read_text()):
        slug = src["slug"]
        body = clean(src["content"])
        words = text_only(body)
        desc = src["seo_description"].strip() or " ".join(words[:28]) + "..."
        seo_title = re.sub(r"\s*-\s*Team One Fitness\s*$", "", src["seo_title"].strip())
        title = html.unescape(src["title"].strip())
        posts.append({
            "slug": slug,
            "title": title,
            "seo_title": html.unescape(seo_title) if seo_title else title,
            "desc": html.unescape(desc),
            "date": datetime.strptime(src["date"], "%Y-%m-%d %H:%M:%S"),
            "cats": KEEP[slug],
            "body": body,
            "minutes": max(1, round(len(words) / 220)),
        })
    missing = set(KEEP) - {p["slug"] for p in posts}
    assert not missing, f"posts missing: {missing}"
    posts.sort(key=lambda p: p["date"], reverse=True)
    return posts


HEADER = """<header class="site-header">
  <div class="container">
    <a class="logo" href="/"><img src="/assets/logo-black.png" alt="Team One" width="171" height="162"></a>
    <nav class="main-nav" aria-label="Main">
      <a href="/">Home</a>
      <div class="nav-drop">
        <a href="/training/">Training</a>
        <div class="drop">
          <a href="/training/bootcamp-fitness-training/">Bootcamp</a>
          <a href="/training/personal-training/">Personal Training</a>
          <a href="/the-rapid-shred/">The Shred</a>
          <a href="/training/corporate-fitness-training/">Corporate Fitness</a>
        </div>
      </div>
      <a href="https://clients.mindbodyonline.com/classic/ws?studioid=188148&amp;stype=-7&amp;sView=week">Timetable</a>
      <a href="/sign-up/">Prices</a>
      <a href="/locations/">Locations</a>
      <a href="/about/">About</a>
      <a href="/blog/">Blog</a>
      <a href="/contact/">Contact</a>
    </nav>
    <a class="btn header-cta" href="/get-started/">Start your 7-day trial</a>
    <details class="menu">
      <summary>Menu</summary>
      <nav aria-label="Main (mobile)">
        <a href="/">Home</a>
        <a href="/training/">Training</a>
        <a class="sub" href="/training/bootcamp-fitness-training/">Bootcamp</a>
        <a class="sub" href="/training/personal-training/">Personal Training</a>
        <a class="sub" href="/the-rapid-shred/">The Shred</a>
        <a class="sub" href="/training/corporate-fitness-training/">Corporate Fitness</a>
        <a href="https://clients.mindbodyonline.com/classic/ws?studioid=188148&amp;stype=-7&amp;sView=week">Timetable</a>
        <a href="/sign-up/">Prices</a>
        <a href="/locations/">Locations</a>
        <a href="/about/">About</a>
        <a href="/blog/">Blog</a>
        <a href="/contact/">Contact</a>
        <a href="/get-started/">Start your 7-day trial</a>
      </nav>
    </details>
  </div>
</header>"""

FOOTER = """<footer class="site-footer">
  <div class="container">
    <div class="grid">
      <a class="logo" href="/"><img src="/assets/logo-black.png" alt="Team One" width="171" height="162" style="height:80px;width:auto"></a>
      <div class="links">
        <a href="/training/">Training</a>
        <a href="https://clients.mindbodyonline.com/classic/ws?studioid=188148&amp;stype=-7&amp;sView=week">Timetable</a>
        <a href="/sign-up/">Prices</a>
        <a href="/locations/">Locations</a>
        <a href="/about/">About</a>
        <a href="/blog/">Blog</a>
        <a href="/contact/">Contact</a>
        <a href="/referral-program/">Refer a friend</a>
        <a href="/frequently-asked-questions/">FAQ</a>
        <a href="/terms-and-conditions/">Terms</a>
      </div>
      <div class="contact">
        <a href="tel:+61424245578">0424 245 578</a>
        <a href="mailto:info@teamonefitness.com.au">info@teamonefitness.com.au</a>
        <a href="https://www.instagram.com/teamonefitness/">Instagram</a>
      </div>
    </div>
    <div class="bottom">
      <span>© 2026 Team One Fitness</span>
      <span>Bondi · Coogee · Sydney</span>
    </div>
  </div>
</footer>"""

STYLE = """<style>
  .intro { background: var(--black); color: var(--white); padding: 56px 0 48px; }
  .intro h1 { font-size: clamp(30px, 4.4vw, 50px); line-height: 1.08; color: var(--white); max-width: 22ch; }
  .intro .sub { font-size: 18px; color: #e2e2e2; margin: 14px 0 0; max-width: 56ch; }
  .crumbs { font-size: 13px; color: #cfd2d5; margin-bottom: 14px; }
  .crumbs a { color: #cfd2d5; text-decoration: none; }
  .crumbs a:hover { color: var(--orange); }
  .meta { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; margin-top: 18px; font-size: 14px; color: #cfd2d5; }
  .tag { display: inline-block; border: 1px solid var(--orange); color: var(--orange); border-radius: 999px; padding: 3px 12px; font-family: var(--head); font-weight: 600; font-size: 12.5px; text-decoration: none; }
  .tag:hover { background: var(--orange); color: var(--white); }
  .article { padding: 56px 0 72px; }
  .article .body { max-width: 720px; font-size: 17px; color: var(--body); line-height: 1.75; }
  .article .body p { margin: 0 0 18px; }
  .article .body h2, .article .body h3, .article .body h4, .article .body h5 { color: var(--ink); margin: 34px 0 12px; line-height: 1.25; }
  .article .body h2 { font-size: 26px; }
  .article .body h3 { font-size: 22px; }
  .article .body h4 { font-size: 19px; }
  .article .body h5 { font-size: 17px; }
  .article .body ul, .article .body ol { padding-left: 22px; margin: 0 0 20px; }
  .article .body li { margin-bottom: 6px; }
  .article .body li::marker { color: var(--orange); }
  .article .body a { color: var(--orange-dark); font-weight: 600; }
  .article .body img { border-radius: 6px; margin: 8px 0 24px; height: auto; }
  .article .body strong { color: var(--ink); }
  .cta-box { max-width: 720px; margin-top: 44px; background: var(--sand); border-left: 4px solid var(--orange); border-radius: 6px; padding: 28px; }
  .cta-box h2 { font-size: 22px; margin-bottom: 8px; }
  .cta-box p { color: var(--body); margin: 0 0 18px; }
  .more { padding: 64px 0 80px; background: var(--sand); }
  .more h2 { font-size: clamp(24px, 2.8vw, 32px); margin-bottom: 24px; }
  .filters { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 24px; }
  .filters a { border: 1px solid #3a3a3a; color: var(--white); border-radius: 999px; padding: 8px 16px; font-family: var(--head); font-weight: 600; font-size: 14px; text-decoration: none; }
  .filters a:hover, .filters a.on { border-color: var(--orange); background: var(--orange); }
  .list { padding: 56px 0 80px; }
  .posts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
  .post-card { display: flex; flex-direction: column; background: var(--white); border: 1px solid var(--line); border-radius: 8px; padding: 24px; text-decoration: none; color: inherit; transition: border-color .2s, transform .2s; }
  .post-card:hover { border-color: var(--orange); transform: translateY(-2px); }
  .post-card .cats { font-family: var(--head); font-weight: 700; font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--orange); margin-bottom: 10px; }
  .post-card h3 { font-size: 19px; line-height: 1.3; margin-bottom: 10px; }
  .post-card p { color: var(--body); font-size: 15px; margin: 0 0 16px; flex: 1; }
  .post-card .date { font-size: 13px; color: var(--muted); }
  @media (max-width: 960px) { .posts { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 640px) { .posts { grid-template-columns: 1fr; } .article .body { font-size: 16px; } }
  /* 2026-10-28 refresh to match the home page */
  .intro { position: relative; overflow: hidden; padding: 72px 0 64px; }
  .intro::before { content: ""; position: absolute; right: -140px; top: -180px; width: 560px; height: 560px; border-radius: 50%; background: radial-gradient(circle closest-side, rgba(246,142,31,0.30), rgba(246,142,31,0)); }
  .intro .container { position: relative; }
  .intro::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 4px; background: var(--orange); }
  .tag { background: rgba(246,142,31,0.08); }
  .article { padding: 64px 0 88px; }
  .article .container { display: grid; grid-template-columns: minmax(0, 720px) 320px; gap: 64px; align-items: start; justify-content: space-between; }
  .article .body > p:first-child { font-size: 19px; color: var(--ink); }
  .article .body h2 + br, .article .body h3 + br, .article .body h4 + br, .article .body h5 + br { display: none; }
  .article .body h4 { padding-left: 14px; border-left: 3px solid var(--orange); }
  .cta-box { position: sticky; top: 110px; margin-top: 0; overflow: hidden; background: var(--black); border-left: 0; border-top: 4px solid var(--orange); border-radius: 10px; padding: 32px 28px; box-shadow: 0 18px 44px rgba(0,0,0,0.18); }
  .cta-box::before { content: ""; position: absolute; right: -90px; top: -90px; width: 240px; height: 240px; border-radius: 50%; background: radial-gradient(circle closest-side, rgba(246,142,31,0.35), rgba(246,142,31,0)); }
  .cta-box > * { position: relative; }
  .cta-box h2 { color: var(--white); font-size: 24px; }
  .cta-box p { color: #d6d6d6; }
  .more, .list { padding: 80px 0 96px; }
  .post-card { border: 0; border-top: 4px solid var(--orange); padding: 28px 26px 24px; box-shadow: 0 8px 28px rgba(0,0,0,0.07); transition: transform .25s ease, box-shadow .25s ease; }
  .post-card:hover { transform: translateY(-4px); box-shadow: 0 18px 40px rgba(0,0,0,0.13); }
  .post-card h3 { transition: color .2s ease; }
  .post-card:hover h3 { color: var(--orange-dark); }
  .post-card .date::after { content: "Read →"; float: right; font-family: var(--head); font-weight: 700; font-size: 12.5px; letter-spacing: .06em; text-transform: uppercase; color: var(--orange); }
  @media (max-width: 960px) { .article .container { grid-template-columns: 1fr; gap: 44px; } .cta-box { position: relative; top: auto; max-width: 720px; } }
  @media (max-width: 640px) { .intro { padding: 56px 0 48px; } .more, .list { padding: 56px 0 64px; } }
</style>"""


def page(title, desc, path, og_type, jsonld, main):
    return f"""<!doctype html>
<html lang="en-AU">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<!-- TEST VERSION: remove the next line on launch day -->
<meta name="robots" content="noindex, nofollow">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(desc)}">
<link rel="canonical" href="{SITE}{path}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{html.escape(title)}">
<meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{SITE}{path}">
<meta property="og:image" content="{SITE}/assets/photos/hero-bondi-kettlebells-clean-1920.webp">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@600;700;800&family=Work+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
<script type="application/ld+json">
{jsonld}
</script>
{STYLE}
</head>
<body>

{HEADER}

<main>
{main}
</main>

{FOOTER}

</body>
</html>
"""


def ld(obj):
    import json
    return json.dumps(obj, indent=2, ensure_ascii=False)


def crumbs_ld(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": n + 1, "name": name, "item": SITE + url}
        for n, (name, url) in enumerate(items)]}


def card(p):
    cats = " · ".join(CATEGORIES[c] for c in p["cats"])
    return f"""      <a class="post-card" href="/{p['slug']}/">
        <span class="cats">{cats}</span>
        <h3>{html.escape(p['title'])}</h3>
        <p>{html.escape(p['desc'])}</p>
        <span class="date">{nice_date(p['date'])}</span>
      </a>"""


def filters(on=None):
    links = [f'<a href="/blog/"{" class=\"on\"" if on is None else ""}>All posts</a>']
    for key, name in CATEGORIES.items():
        links.append(f'<a href="/category/{key}/"{" class=\"on\"" if on == key else ""}>{name}</a>')
    return '<nav class="filters" aria-label="Blog categories">\n        ' + "\n        ".join(links) + "\n      </nav>"


def write(path, text):
    out = PUBLIC / path.strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)


def build():
    posts = load()

    for p in posts:
        path = f"/{p['slug']}/"
        tags = " ".join(f'<a class="tag" href="/category/{c}/">{CATEGORIES[c]}</a>' for c in p["cats"])
        related = [q for q in posts if q is not p and set(q["cats"]) & set(p["cats"])][:3]
        jsonld = ld({"@context": "https://schema.org", "@graph": [
            crumbs_ld([("Home", "/"), ("Blog", "/blog/"), (p["title"], path)]),
            {"@type": "BlogPosting", "headline": p["title"], "description": p["desc"],
             "datePublished": p["date"].strftime("%Y-%m-%d"), "url": SITE + path,
             "author": {"@type": "Person", "name": "Yves Minten", "url": SITE + "/about/about-yves-minten/"},
             "publisher": {"@type": "Organization", "name": "Team One Fitness", "url": SITE + "/"}},
        ]})
        main = f"""  <section class="intro">
    <div class="container">
      <p class="crumbs"><a href="/">Home</a> / <a href="/blog/">Blog</a></p>
      <h1>{html.escape(p['title'])}</h1>
      <div class="meta">
        <span>Posted {nice_date(p['date'])}</span>
        <span>{p['minutes']} min read</span>
        {tags}
      </div>
    </div>
  </section>

  <article class="article">
    <div class="container">
      <div class="body">
{p['body']}
      </div>
      <aside class="cta-box">
        <h2>Train with Team One</h2>
        <p>Outdoor bootcamp on the sand at Bondi and Coogee, for every fitness level. Try a full week for just $15.</p>
        <a class="btn" href="/get-started/">Start your 7-day trial</a>
      </aside>
    </div>
  </article>
"""
        if related:
            main += f"""
  <section class="more">
    <div class="container">
      <h2>More from the blog</h2>
      <div class="posts">
{chr(10).join(card(q) for q in related)}
      </div>
    </div>
  </section>
"""
        write(path, page(f"{p['seo_title']} | Team One Fitness", p["desc"], path, "article", jsonld, main))

    def listing(path, h1, sub, crumbs, on, items, title, desc):
        jsonld = ld({"@context": "https://schema.org", "@graph": [
            crumbs_ld(crumbs),
            {"@type": "Blog" if on is None else "CollectionPage", "name": h1, "url": SITE + path},
        ]})
        crumb_html = " / ".join(f'<a href="{u}">{n}</a>' for n, u in crumbs[:-1])
        main = f"""  <section class="intro">
    <div class="container">
      <p class="crumbs">{crumb_html}</p>
      <h1>{h1}</h1>
      <p class="sub">{sub}</p>
      {filters(on)}
    </div>
  </section>

  <section class="list">
    <div class="container">
      <div class="posts">
{chr(10).join(card(p) for p in items)}
      </div>
    </div>
  </section>
"""
        write(path, page(title, desc, path, "website", jsonld, main))

    listing("/blog/", "Team One Blog",
            "Workouts, nutrition tips, recipes and motivation from the Team One coaches.",
            [("Home", "/"), ("Blog", "/blog/")], None, posts,
            "Blog | Fitness, Nutrition & Workout Tips | Team One Fitness",
            "Workouts, nutrition tips, recipes and motivation from the Team One coaches in Bondi and Coogee.")
    for key, name in CATEGORIES.items():
        items = [p for p in posts if key in p["cats"]]
        listing(f"/category/{key}/", name,
                f"{len(items)} posts about {name.lower()} from the Team One coaches.",
                [("Home", "/"), ("Blog", "/blog/"), (name, f"/category/{key}/")], key, items,
                f"{name} | Team One Fitness Blog",
                f"{name} posts from the Team One Fitness blog: tips from our coaches in Bondi and Coogee.")
    print(f"built {len(posts)} posts, blog page and {len(CATEGORIES)} category pages")


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == "--from-export":
        extract(sys.argv[2])
    build()
