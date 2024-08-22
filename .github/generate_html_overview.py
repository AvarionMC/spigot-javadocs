import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Template

base_url = "https://dev.avarion.org"  # Replace with your actual base URL
output_dir = Path(__file__).parent.parent
os.chdir(output_dir)


def extract_jar(jar_path, extract_path):
    if extract_path.exists() and any(extract_path.iterdir()):
        return

    print(f" > Extracting '{jar_path.name}'")
    with zipfile.ZipFile(jar_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)


def get_version_from_filename(filename):
    match = re.search(r"spigot-api-([\d.]+)\.jar", filename)
    return match.group(1) if match else None


def generate_sitemap(base_url, versions):
    print("Generating sitemaps")
    current_date = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")

    # Generate individual sitemaps for each version
    for version in versions:
        sitemap_template = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{{ base_url }}/{{ version }}/index.html</loc>
        <lastmod>{{ current_date }}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>
</urlset>
"""
        template = Template(sitemap_template)
        sitemap_content = template.render(
            base_url=base_url, version=version, current_date=current_date
        )

        with open(output_dir / f"sitemap_{version}.xml", "w") as f:
            f.write(sitemap_content)

    # Generate sitemap index
    sitemap_index_template = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <sitemap>
        <loc>{{ base_url }}/sitemap_main.xml</loc>
        <lastmod>{{ current_date }}</lastmod>
    </sitemap>
    {% for version in versions %}
    <sitemap>
        <loc>{{ base_url }}/sitemap_{{ version }}.xml</loc>
        <lastmod>{{ current_date }}</lastmod>
    </sitemap>
    {% endfor %}
</sitemapindex>
"""
    template = Template(sitemap_index_template)
    sitemap_index_content = template.render(
        base_url=base_url, versions=versions, current_date=current_date
    )

    with open(output_dir / "sitemap_index.xml", "w") as f:
        f.write(sitemap_index_content)

    # Generate main sitemap
    main_sitemap_template = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{{ base_url }}/</loc>
        <lastmod>{{ current_date }}</lastmod>
        <changefreq>weekly</changefreq>
        <priority>1.0</priority>
    </url>
</urlset>
"""
    template = Template(main_sitemap_template)
    main_sitemap_content = template.render(base_url=base_url, current_date=current_date)

    with open(output_dir / "sitemap_main.xml", "w") as f:
        f.write(main_sitemap_content)


def generate_robots_txt(base_url):
    print("Generating robots.txt")

    robots_txt_content = f"""User-agent: *
Allow: /

Sitemap: {base_url}/sitemap_index.xml
"""
    with open(output_dir / "robots.txt", "w") as f:
        f.write(robots_txt_content)


def main():
    jar_dir = Path("jar_files")

    versions = []

    for jar_file in jar_dir.glob("spigot-api-*.jar"):
        version = get_version_from_filename(jar_file.name)
        if version:
            versions.append(version)
            version_dir = output_dir / version
            version_dir.mkdir(exist_ok=True)
            extract_jar(jar_file, version_dir)

    versions.sort(key=lambda v: [int(x) for x in v.split(".")], reverse=True)

    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Spigot API JavaDoc Overview</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            h1 { color: #333; }
            ul { list-style-type: none; padding: 0; }
            li { margin-bottom: 10px; }
            a { color: #0066cc; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <h1>Spigot API JavaDoc Overview</h1>
        <ul>
        {% for version in versions %}
            <li><a href="{{ version }}/index.html">Version {{ version }}</a></li>
        {% endfor %}
        </ul>
    </body>
    </html>
    """

    template = Template(html_template)
    html_content = template.render(versions=versions)

    with open(output_dir / "index.html", "w") as f:
        f.write(html_content)

    generate_sitemap(base_url, versions)
    generate_robots_txt(base_url)


if __name__ == "__main__":
    main()
