import ast

from setuptools import setup

author = author_email = version = None
with open("wait_for2/__init__.py", encoding="utf-8") as f:
    for line in f:
        if line.startswith("__author__ = "):
            author = ast.literal_eval(line[len("__author__ = ") :])
        elif line.startswith("__author_email__ = "):
            author_email = ast.literal_eval(line[len("__author_email__ = ") :])
        elif line.startswith("__version__ = "):
            version = ast.literal_eval(line[len("__version__ = ") :])


description = "Asyncio wait_for that can handle simultaneous cancellation and future completion."
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="wait_for2",
    version=version,
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Traktormaster/wait-for2",
    author=author,
    author_email=author_email,
    license="Apache 2.0",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
    ],
    packages=["wait_for2"],
)
