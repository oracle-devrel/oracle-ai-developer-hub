from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="oracle-ragcli",
    version="2.0.1",
    author="jasperan",
    author_email="dev@example.com",
    description="Production RAG system with multi-agent reasoning, knowledge graph, and hybrid search for Oracle DB 26ai",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jasperan/ragcli",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=[
        "typer>=0.9.0",
        "click>=8.1.0",
        "rich>=13.7.0",
        "gradio>=4.0.0",
        "oracledb>=1.4.0",
        "pyyaml>=6.0.1",
        "aiohttp>=3.9.0",
        "requests>=2.31.0",
        "plotly>=5.17.0",
        "matplotlib>=3.8.0",
        "langchain-community>=0.0.20",
        "pypdf2>=3.0.1",
        "pdfplumber>=0.10.3",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "watchdog>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.0.0",
            "isort>=5.12.0",
        ],
    },
    entry_points={},
)
