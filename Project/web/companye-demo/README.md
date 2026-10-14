# CompanyE web demo

Static, independent snapshot presentation. No authentication; anyone with the URL can visit or forward it. HTML noindex/nofollow/noarchive is the primary indexing control; _headers supplies equivalent headers on supporting hosts. robots.txt allows crawlers to see noindex; no sitemap. These controls do not guarantee secrecy or removal from every search engine.

The source-code button links to https://github.com/tranphu1508/DE-CaseCompanyE, configured in site-config.json. The public repository can be indexed independently of this website's noindex directive. Do not identify visitor roles in public copy.

From this directory:
- Run Python UTF-8 export.py to regenerate sanitized data.json from verified project results.
- Run node --check dist/app.js and Python UTF-8 verify.py.
- Preview dist using a local HTTP server.
- GitHub Pages publishes ONLY `dist/`, not CompanyE raw data, credentials, backups, or the main project repository.

The static demo exposes 104 verified SQL contexts and 48 engine/month result rows. Each context is a complete saved scenario; arbitrary cross-combinations are not supported. The saved semantic report records Oracle values and asserts exact equality for Iceberg and raw reference, so a shared payload represents both engines. Monthly data comes from actual DAX result rows per engine. SQL quantities and money stay decimal strings until display. Chart money is explicitly scaled to billions. Unsupported chart slices show a message instead of unrelated global data.

This is not live Oracle/Spark serving or a benchmark. All raw/ETL remains local. The main project is consolidated in DE-CaseCompanyE.

## GitHub Pages deployment

Canonical demo: https://tranphu1508.github.io/DE-CaseCompanyE/

The repository's `.github/workflows/pages.yml` checks JavaScript syntax and runs `verify.py` against committed evidence before uploading only `dist/` and deploying it to the `github-pages` environment. It runs on relevant changes to `main`, or manually through Actions > Publish CompanyE web demo > Run workflow. Repository Settings > Pages must use GitHub Actions as the source. No custom deployment credential is stored in the repository; deployment uses the workflow's short-lived GitHub token and OIDC.

This workflow does not regenerate the databases, run ETL, or query live engines. When refreshing results, run `export.py` and `verify.py` locally and commit the sanitized output together with its matching evidence. A failed verification prevents deployment. To restore a prior website, revert the relevant web changes together with their matching evidence and deploy again.

All browser assets and JSON use relative URLs, so they work below `/DE-CaseCompanyE/`. Hash-based navigation needs no server rewrite. GitHub Pages does not process the retained `_headers` file; the HTML robots/googlebot meta tags provide the indexing directives here. The project-local `robots.txt` is not a domain-root robots policy. These directives do not make the site private; the public repository can still appear in search results.

The earlier ChatGPT Sites deployment records are retained as historical evidence, not the canonical hosting configuration.

