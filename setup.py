from setuptools import setup, find_packages

setup(
    name="KOV",
    version="0.1.0",
    description="KOV - Local AI Developer Agent",
    packages=find_packages(),
    install_requires=[
        "langchain>=0.0.350",
        "ollama",
        "typer>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "kov=KOV.cli.main:app",
        ],
    },
    python_requires=">=3.8",
)
