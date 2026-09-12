from err_api import _parse_sitemap_urls, fetch_sitemap_index

SAMPLE_XML = (
    '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    "<url><loc>https://lasteekraan.err.ee/1608776941/vilda</loc><lastmod>2026-01-01</lastmod></url>"
    "<url><loc>https://lasteekraan.err.ee/1038778/porsas-peppa</loc><lastmod>2026-01-01</lastmod></url>"
    "</urlset>"
)

parsed = _parse_sitemap_urls(SAMPLE_XML)
assert parsed == [(1608776941, "vilda"), (1038778, "porsas-peppa")], parsed

sitemap_urls = fetch_sitemap_index()
assert any(url.endswith("sitemap0.xml") for url in sitemap_urls), sitemap_urls

print(f"OK: sitemap parser correct, index lists {len(sitemap_urls)} content sitemap(s)")
