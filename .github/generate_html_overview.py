import re
import zipfile
from pathlib import Path

from jinja2 import Template


ROOT = Path(__file__).parent.parent  # Root is 1 down from `.github` dir


def extract_jar(jar_path, extract_path):
    with zipfile.ZipFile(jar_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)


def get_version_from_filename(filename):
    match = re.search(r"spigot-api-([\d.]+)\.jar", filename)
    return match.group(1) if match else None


def main():
    jar_dir = ROOT / "jar_files"

    versions = []

    for jar_file in jar_dir.glob("spigot-api-*.jar"):
        version = get_version_from_filename(jar_file.name)
        if version:
            print(f" > Extracting '{jar_file.name}'")

            versions.append(version)
            version_dir = ROOT / version
            version_dir.mkdir(exist_ok=True, parents=True)
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

    with open(ROOT / "index.html", "w") as f:
        f.write(html_content)


if __name__ == "__main__":
    main()
