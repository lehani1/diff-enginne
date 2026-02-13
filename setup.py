from setuptools import setup, find_packages

setup(
    name="schema-detector",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": ["pytest>=7.0.0"],
    },
    python_requires=">=3.8",
    description="Schema Change Detector for YAML Config Files",
    author="Schema Detector Team",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
