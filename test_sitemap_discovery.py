import re

from err_api import LASTEEKRAAN_BASE_URL, _has_playable_content, _parse_sitemap_urls

SAMPLE_XML = (
    '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    "<url><loc>https://lasteekraan.err.ee/1608776941/vilda</loc><lastmod>2026-01-01</lastmod></url>"
    "<url><loc>https://lasteekraan.err.ee/1038778/porsas-peppa</loc><lastmod>2026-01-01</lastmod></url>"
    "</urlset>"
)

parsed = _parse_sitemap_urls(SAMPLE_XML)
assert parsed == [(1608776941, "vilda"), (1038778, "porsas-peppa")], parsed

SAMPLE_INDEX_XML = (
    '<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    "<sitemap><loc>https://lasteekraan.err.ee/sitemap/sitemap0.xml</loc></sitemap>"
    "<sitemap><loc>https://lasteekraan.err.ee/sitemap/sitemap1.xml</loc></sitemap>"
    "<sitemap><loc>https://lasteekraan.err.ee/sitemap/videos0.xml</loc></sitemap>"
    "</sitemapindex>"
)

index_pattern = rf"<loc>({re.escape(LASTEEKRAAN_BASE_URL)}/sitemap/sitemap\d+\.xml)</loc>"
index_urls = re.findall(index_pattern, SAMPLE_INDEX_XML)
assert index_urls == [
    "https://lasteekraan.err.ee/sitemap/sitemap0.xml",
    "https://lasteekraan.err.ee/sitemap/sitemap1.xml",
], index_urls

assert _has_playable_content({"data": {"mainContent": {"medias": [{"src": {}}]}}}) is True
assert _has_playable_content({"data": {"seasonList": {"items": [{"firstContentId": 1}]}}}) is True
assert _has_playable_content({"data": {"mainContent": {"medias": []}, "seasonList": {"items": []}}}) is False

print("OK: sitemap parser, index regex and _has_playable_content all correct")
