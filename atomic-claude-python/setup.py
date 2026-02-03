"""
ATOMIC CLAUDE - Python Implementation Setup
"""

from setuptools import setup, find_packages

setup(
    name="atomic-claude",
    version="2.0.0-alpha",
    description="Script-controlled LLM orchestration for deterministic software development",
    author="ATOMIC CLAUDE",
    python_requires=">=3.9",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "atomic-claude=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
