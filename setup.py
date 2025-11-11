"""
Setup script for ALM Traceability MCP Server
"""
from setuptools import setup, find_packages

setup(
    name="alm-traceability-mcp",
    version="1.0.5",
    description="ALM Traceability MCP Tools - Azure DevOps, Jira, and Vector Search integration",
    author="Mridula",
    author_email="mridulait67@gmail.com",
    python_requires=">=3.8",
    packages=find_packages(),
    include_package_data=True,
    py_modules=[
        "mcp_main",
        "mcp_tools",
        "ado_client",
        "jira_client",
        "traceability_manager",
        "mcp_traceability_tools",
        "vector_service",
        "database_manager",
        "config"
    ],
    install_requires=[
        "mcp>=1.0.0",
        "aiohttp>=3.9.0",
        "pydantic>=2.5.0",
        "python-dotenv>=1.0.0",
        "asyncpg>=0.29.0",
        "psycopg2-binary>=2.9.9",
        "structlog>=23.1.0",
    ],
    extras_require={
        "vector": [
            "google-cloud-aiplatform",
            "sentence-transformers"
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black",
            "isort",
            "flake8",
        ],
    },
    entry_points={
        "console_scripts": [
            "alm-traceability-mcp=mcp_main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)