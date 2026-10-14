# CompanyE web demo

Static, independent snapshot presentation. No authentication; anyone with the URL can visit or forward it. HTML noindex/nofollow/noarchive is the primary indexing control; _headers supplies equivalent headers on supporting hosts. robots.txt allows crawlers to see noindex; no sitemap. These controls do not guarantee secrecy or removal from every search engine.

Repository URL is intentionally blank in site-config.json. The source-code button is hidden until a real HTTPS URL is supplied. Do not invent a repository or identify visitor roles in public copy.

From this directory:
- Run Python UTF-8 export.py to regenerate sanitized data.json from verified project results.
- Run node --check dist/app.js and Python UTF-8 verify.py.
- Preview dist using a local HTTP server.
- Sites source sync includes ONLY this isolated directory, not CompanyE raw data, credentials, backups, or the main project repository.

The static demo exposes 104 verified SQL contexts and 48 engine/month result rows. Each context is a complete saved scenario; arbitrary cross-combinations are not supported. The saved semantic report records Oracle values and asserts exact equality for Iceberg and raw reference, so a shared payload represents both engines. Monthly data comes from actual DAX result rows per engine. SQL quantities and money stay decimal strings until display. Chart money is explicitly scaled to billions. Unsupported chart slices show a message instead of unrelated global data.

This is not live Oracle/Spark serving or a benchmark. All raw/ETL remains local. The main project Git repository will be consolidated later; the hosting source repository is an isolated transport required by Sites.

