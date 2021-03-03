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


description = "Asyncio wait_for with more control over cancellation."
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="wait_for2",
    version=version,
    description=description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    author=author,
    author_email=author_email,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
    ],
    packages=["wait_for2"],
)
