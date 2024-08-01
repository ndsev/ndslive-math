import setuptools
from pathlib import Path

# Read the contents of README.md
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read the contents of requirements.txt
with open('requirements.txt') as f:
    required = f.read().splitlines()

# Read the version from VERSION file
with open('VERSION') as f:
    version = f.read().strip()

setuptools.setup(
    name="ndsmath",
    version=version,
    author="Navigation Data Standard e.V.",
    author_email="support@nds-association.org",
    description="Math utilities for NDS.Live",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ndsev/ndsmath",
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=required,
)