from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="devjourney",
    version="0.1.0",
    author="Tautik Agrahari",
    author_email="tautikagrahari@gmail.com",
    description="A personal progress tracking system that integrates AI conversations into Notion",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tautik/DevJourney",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.12",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "devjourney=devjourney.main:main",
        ],
    },
)
