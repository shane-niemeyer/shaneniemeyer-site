#!/usr/bin/env python3
"""Build shaneniemeyer.com from src/site.html.

The source is one file holding every page as a <div class="view" data-view="...">.
This script writes one real page per view (index.html, doctrine/index.html, ...),
each with its own title, description, share tags and canonical URL, plus
sitemap.xml, robots.txt and 404.html.

    python3 build.py                     # build the live site into the repo root
    python3 build.py --theme ember --out /tmp/preview   # build a themed preview elsewhere

Edit src/site.html (and src/*.css), then run this and commit the output.
"""
import argparse, html, os, re, shutil, sys
from datetime import date

SITE = "https://shaneniemeyer.com"
HERE = os.path.dirname(os.path.abspath(__file__))

# Per-page share text. Anything missing falls back to the page's own heading and lead.
META = {
    "home": ("Shane Niemeyer · Training is the process of health",
             "Strength and conditioning coach in Boulder County, Colorado. Training is not working out: it is structured, progressive and directed toward outcomes, and it changes who we are."),
    "doctrine": ("The Doctrine · Shane Niemeyer",
                 "Training is not something we do a few hours a week. It is the process of health and wellbeing itself, built into the fabric of daily life."),
    "process": ("The Niemeyer Method · Shane Niemeyer",
                "You don't find yourself. You create yourself, one choice, one action, one day at a time. How we locate each person, progress the load and train for a lifetime."),
    "evidence": ("The Evidence · Shane Niemeyer",
                 "The case for training as medicine. Every claim carries a source and a label: what kind of study it comes from, and how strong it is."),
    "work": ("Work with Shane · Shane Niemeyer",
             "Concierge coaching in person and online, VO2 and metabolic testing, retreats with Dr. Jill Carnahan, and speaking."),
    "providers": ("For Providers · Shane Niemeyer",
                  "Exercise is medicine. This is how we practice it, alongside medical care and never in place of it."),
    "story": ("Story · Shane Niemeyer",
              "From a prison cell to the lava fields of Kona. How far one human being can come, and what it takes."),
    "writing": ("Writing · Shane Niemeyer",
                "One idea a week: a principle from the doctrine, the science behind it, and what it looks like on the floor."),
    "never-easy-never-hard": ("Never truly easy. Never truly hard. · Shane Niemeyer",
                              "Most people train in the middle. It feels productive. It keeps them stuck."),
    "library": ("The Library · Shane Niemeyer",
                "From the cell to the whole human being. The book, the modules and the exercise library: how training transforms us, with the evidence behind every claim."),
    "introduction": ("Introduction: Training Is the Process of Health · Shane Niemeyer",
                     "Why no intervention reaches further than the pursuit of fitness through training."),
    "meet-people-where-they-are": ("Meet People Where They Are · The Niemeyer Method",
                                   "Locating the person, progressing the load, and periodizing for a lifetime of training."),
    "exercises": ("Exercise Library · Shane Niemeyer",
                  "Every movement sits on a ladder, with a first rung anyone can stand on and a path to the top."),
}
ARTICLES = {"never-easy-never-hard", "introduction", "meet-people-where-they-are"}


def path_of(name):
    return "" if name == "home" else name + "/"


def build(theme, out):
    src = open(os.path.join(HERE, "src", "site.html"), encoding="utf-8").read()

    # --- split the source -------------------------------------------------
    first_line, rest = src.split("\n", 1)
    head_style = re.search(r"<style>.*?</style>", first_line).group(0)
    hdr = rest.index('<header class="site">')
    head_extra = rest[:hdr]
    head_extra = re.sub(r"<title>.*?</title>\s*", "", head_extra)
    head_extra = re.sub(r'<meta name="claude:[^>]*>\s*', "", head_extra)
    body = rest[hdr:]
    main_open = body.index("<main>") + len("<main>")
    main_close = body.index("</main>")
    shell_top, views_src, shell_bottom = body[:main_open], body[main_open:main_close], body[main_close:]

    starts = [m.start() for m in re.finditer(r'(?:<!-- =+[^>]*-->\s*)?<div class="view', views_src)]
    views = {}
    for i, st in enumerate(starts):
        block = views_src[st: starts[i + 1] if i + 1 < len(starts) else len(views_src)].strip()
        name = re.search(r'data-view="([^"]+)"', block).group(1)
        views[name] = block
    names = list(views)

    theme_css = ""
    if theme:
        theme_css = "<style>\n" + open(os.path.join(HERE, "src", theme + ".css"), encoding="utf-8").read() + "\n</style>\n"

    def links(text, root):
        def fix(m):
            target, jump = m.group(1), m.group(3)
            if jump:
                return 'href="#%s"%s' % (jump, m.group(2))
            if target in views:
                return 'href="%s"%s' % ((root + path_of(target)) or "./", m.group(2) or "")
            return m.group(0)
        return re.sub(r'href="#([\w-]+)"(\s+data-jump="([\w-]+)")?', fix, text)

    def router_js(root):
        return ("  var ROOT = %r, PAGES = %s;\n"
                "  var legacy = (location.hash || '').slice(1);\n"
                "  if (PAGES.indexOf(legacy) > -1) location.replace(ROOT + (legacy === 'home' ? '' : legacy + '/'));\n"
                % (root or "./", "[" + ",".join("'%s'" % n for n in names) + "]"))

    def page(name, block, root, canonical, title, desc, og_type="website", noindex=False):
        section = re.search(r'data-section="([^"]+)"', block)
        section = section.group(1) if section else name
        top = links(shell_top, root)
        top = re.sub(r'(<a href="[^"]*" data-nav="%s")' % re.escape(section), r'\1 aria-current="page"', top)
        block = re.sub(r"(<div class=\"view[^>]*?)\s+hidden>", r"\1>", block, count=1)
        block = links(block, root)
        bottom = links(shell_bottom, root)
        bottom = re.sub(r"  var views = .*?\n  show\(\);\n", lambda m: router_js(root), bottom, flags=re.S)
        e = html.escape
        meta = [
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">',
            "<title>%s</title>" % e(title),
            '<meta name="description" content="%s">' % e(desc),
            '<link rel="canonical" href="%s">' % canonical,
            '<meta property="og:type" content="%s">' % og_type,
            '<meta property="og:site_name" content="Shane Niemeyer">',
            '<meta property="og:title" content="%s">' % e(title),
            '<meta property="og:description" content="%s">' % e(desc),
            '<meta property="og:url" content="%s">' % canonical,
            '<meta property="og:image" content="%s/share.png">' % SITE,
            '<meta property="og:image:width" content="1200">',
            '<meta property="og:image:height" content="630">',
            '<meta property="og:image:alt" content="Shane Niemeyer. Training is the process of health.">',
            '<meta name="twitter:card" content="summary_large_image">',
            '<link rel="icon" href="%sfavicon.svg" type="image/svg+xml">' % root,
            '<link rel="icon" href="%sfavicon-32.png" sizes="32x32" type="image/png">' % root,
            '<link rel="apple-touch-icon" href="%sapple-touch-icon.png">' % root,
            '<meta name="theme-color" content="%s">' % ("#14110F" if theme == "ember" else "#FFFFFF"),
        ]
        if noindex:
            meta.append('<meta name="robots" content="noindex">')
        return ("<!doctype html>\n<html lang=\"en\">\n<head>\n" + "\n".join(meta) + "\n" + head_style + "\n"
                + head_extra.strip() + "\n" + theme_css + "</head>\n<body>\n"
                + top + "\n\n" + block + "\n\n" + bottom.rstrip() + "\n</body>\n</html>\n")

    os.makedirs(out, exist_ok=True)
    for name in names:
        root = "" if name == "home" else "../"
        h1 = re.sub("<.*?>", "", re.search(r"<h1[^>]*>(.*?)</h1>", views[name], re.S).group(1)).strip()
        title, desc = META.get(name, (h1 + " · Shane Niemeyer", h1))
        canonical = SITE + "/" + path_of(name)
        d = os.path.join(out, path_of(name))
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(page(name, views[name], root, canonical, title, desc,
                         "article" if name in ARTICLES else "website"))

    nf = ('<div class="view" data-view="404">\n  <section class="hero moment"><div class="wrap"><div class="copy">\n'
          '    <p class="eyebrow">404</p>\n    <h1>Nothing here.</h1>\n'
          '    <p class="lead measure">That page moved or never existed. Start from the beginning.</p>\n'
          '    <div class="actions"><a class="btn primary" href="#home">Home</a><a class="btn ghost" href="#library">The Library</a></div>\n'
          '  </div></div></section>\n</div>')
    with open(os.path.join(out, "404.html"), "w", encoding="utf-8") as f:
        f.write(page("404", nf, "/", SITE + "/404.html", "Not found · Shane Niemeyer",
                     "That page moved or never existed.", noindex=True))

    today = date.today().isoformat()
    with open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for n in names:
            f.write("  <url><loc>%s/%s</loc><lastmod>%s</lastmod></url>\n" % (SITE, path_of(n), today))
        f.write("</urlset>\n")
    with open(os.path.join(out, "robots.txt"), "w") as f:
        f.write("User-agent: *\nAllow: /\nDisallow: /src/\n\nSitemap: %s/sitemap.xml\n" % SITE)
    for asset in os.listdir(os.path.join(HERE, "src", "assets")):
        shutil.copy(os.path.join(HERE, "src", "assets", asset), os.path.join(out, asset))
    return names


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", default="")
    ap.add_argument("--out", default=HERE)
    a = ap.parse_args()
    print("built:", ", ".join(build(a.theme, a.out)))
