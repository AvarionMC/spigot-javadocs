import os
import subprocess
import json
import xml.etree.ElementTree as ET

import requests
import re
from pathlib import Path
from bs4 import BeautifulSoup

CWD = Path.cwd().resolve().absolute()
BASE_URL = "https://hub.spigotmc.org/versions/"
BUILD_TOOLS_JAR = Path.home() / "BuildTools/BuildTools.jar"
OUTPUT_DIR = CWD / "jar_files"
SPIGOT_DIR = BUILD_TOOLS_JAR.parent / "Spigot"

BUILD_TOOLS_JAR.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

JAVA_PATHS = {
    8: Path(os.getenv("JAVA_HOME_8_X64", "/usr/lib/jvm/java-8-openjdk-amd64")),
    11: Path(os.getenv("JAVA_HOME_11_X64", "/usr/lib/jvm/java-11-openjdk-amd64")),
    16: Path(os.getenv("JAVA_HOME_16_X64", "/usr/lib/jvm/jdk-16.0.2")),
    17: Path(os.getenv("JAVA_HOME_17_X64", "/usr/lib/jvm/java-17-openjdk-amd64")),
    18: Path(os.getenv("JAVA_HOME_18_X64", "/usr/lib/jvm/java-18-openjdk-amd64")),
    19: Path(os.getenv("JAVA_HOME_19_X64", "/usr/lib/jvm/java-19-openjdk-amd64")),
    21: Path(os.getenv("JAVA_HOME_21_X64", "/usr/lib/jvm/java-21-openjdk-amd64")),
}


def download_build_tools():
    url = "https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar"
    response = requests.get(url)
    BUILD_TOOLS_JAR.write_bytes(response.content)


def get_available_versions():
    response = requests.get(BASE_URL)
    soup = BeautifulSoup(response.text, "html.parser")

    versions = []
    for link in soup.find_all("a"):
        href = link.get("href")
        if href and (
            match := re.match(
                r"^(\d+\.\d+(?:\.\d+)?)\.json$", href, flags=re.IGNORECASE
            )
        ):
            versions.append(match.group(1))

    return sorted(versions, key=lambda v: [int(i) for i in v.split(".")], reverse=True)


def get_java_version_range(version):
    response = requests.get(f"{BASE_URL}{version}.json")
    data = json.loads(response.text)
    java_versions = data.get("javaVersions", [51, 52])

    if len(java_versions) != 2:
        raise ValueError(
            f"Unexpected javaVersions format for version {version}: {java_versions}"
        )

    min_version = java_versions[0] - 44  # Convert Java class version to Java version
    max_version = java_versions[1] - 44
    return min_version, max_version


def get_java_path(min_version, max_version):
    available_versions = sorted(JAVA_PATHS.keys(), reverse=True)
    for version in available_versions:
        if min_version <= version <= max_version:
            return JAVA_PATHS[version]
    raise Exception(
        f"No suitable Java version found for range {min_version}-{max_version}"
    )


def run_build_tools(version, java_path):
    run_command(f"rm -rf {SPIGOT_DIR}/Spigot-API/target")
    command = f"{java_path}/bin/java -jar {BUILD_TOOLS_JAR} --rev {version}"
    return run_command(command)


def modify_pom(pom_path):
    # Register the namespace
    ET.register_namespace("", "http://maven.apache.org/POM/4.0.0")

    tree = ET.parse(pom_path)
    root = tree.getroot()

    # Define namespace map
    ns = {"maven": "http://maven.apache.org/POM/4.0.0"}

    build = root.find("maven:build", ns)
    if build is None:
        build = ET.SubElement(root, "{http://maven.apache.org/POM/4.0.0}build")

    plugins = build.find("maven:plugins", ns)
    if plugins is None:
        plugins = ET.SubElement(build, "{http://maven.apache.org/POM/4.0.0}plugins")

    # Check if javadoc plugin already exists
    javadoc_plugin = plugins.find(
        ".//maven:plugin[maven:artifactId='maven-javadoc-plugin']", ns
    )
    if javadoc_plugin is None:
        javadoc_plugin = ET.SubElement(plugins, "plugin")
        ET.SubElement(javadoc_plugin, "groupId").text = "org.apache.maven.plugins"
        ET.SubElement(javadoc_plugin, "artifactId").text = "maven-javadoc-plugin"
        ET.SubElement(javadoc_plugin, "version").text = "3.8.0"

        configuration = ET.SubElement(javadoc_plugin, "configuration")
        ET.SubElement(configuration, "source").text = "1.8"
        ET.SubElement(configuration, "quiet").text = "true"
        ET.SubElement(configuration, "detectLinks").text = "false"
        ET.SubElement(configuration, "doclint").text = "none"

    # Use a custom function to write the XML to avoid added prefixes
    write_xml_without_ns_prefix(tree, pom_path)


def write_xml_without_ns_prefix(tree, file_path):
    xml_string = ET.tostring(tree.getroot(), encoding="unicode", method="xml")

    # Remove namespace prefix from tags
    xml_string = xml_string.replace("ns0:", "").replace(":ns0", "")

    # Write the modified XML string to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write(xml_string)


def copy_javadocs(version):
    target = OUTPUT_DIR / f"spigot-api-{version}.jar"

    src = next(
        iter(
            SPIGOT_DIR.joinpath("Spigot-API/target").glob(
                "spigot-api-*-R0.1-SNAPSHOT-javadoc.jar"
            )
        )
    )
    if not src.exists():
        run_command(f"find {SPIGOT_DIR} -type f")
        raise FileNotFoundError(
            f"Javadoc jar file for version '{version}' wasn't found."
        )

    target.write_bytes(src.read_bytes())


def is_version_processed(version):
    version_file = OUTPUT_DIR / f"spigot-api-{version}.jar"
    return version_file.exists()


def run_command(command, env=None):
    print(" >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ")
    print(" ", command)
    print(" >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        env=env,
    )

    for line in process.stdout:
        print(line, end="", flush=True)

    process.wait()

    if process.returncode != 0:
        print(" >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ")
        print(" FAILURE!!")
        print(" >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> ")

    return process.returncode == 0


def generate_javadoc(java_path):
    mvn_path = java_path.parent / "bin" / "mvn"

    if mvn_path.exists():
        command = mvn_path
    else:
        # Fallback to using mvn from PATH
        command = "mvn"

    command += " javadoc:jar source:jar"

    # Set up the environment with JAVA_HOME
    env = os.environ.copy()
    env["JAVA_HOME"] = str(java_path)

    # Change to Spigot directory before running Maven
    original_dir = Path.cwd()
    os.chdir(SPIGOT_DIR)

    try:
        return run_command(command, env=env)
    finally:
        # Change back to the original directory
        os.chdir(original_dir)


def process_version(version):
    if is_version_processed(version):
        print(f"Version {version} has already been processed. Skipping.")
        return

    print(f"Processing version {version}")
    try:
        min_java_version, max_java_version = get_java_version_range(version)
        java_path = get_java_path(min_java_version, max_java_version)
        if run_build_tools(version, java_path):
            pom_path = SPIGOT_DIR / "pom.xml"
            if pom_path.exists():
                modify_pom(pom_path)
                generate_javadoc(java_path)
            else:
                raise FileNotFoundError(f"pom.xml not found at {pom_path}")
            copy_javadocs(version)
            print(f"Completed processing version {version}")
        else:
            print(f"Failed to build version {version}")
    except Exception as e:
        print(f"Error processing version {version}: {str(e)}")
        raise


def main():
    os.chdir(BUILD_TOOLS_JAR.parent)

    if not BUILD_TOOLS_JAR.exists():
        print("Downloading BuildTools.jar...")
        download_build_tools()

    versions = get_available_versions()
    print(f"Found {len(versions)} versions to process")

    for version in versions:
        process_version(version)

    print("All versions processed")


if __name__ == "__main__":
    main()
