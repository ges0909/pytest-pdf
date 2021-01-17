from setuptools import setup


def install_requires():
    with open("requirements.txt") as fp:
        return fp.read()


with open("README.md", "r") as fh:
    long_description = fh.read()


setup(
    name="pytest-pdf",
    version="0.1.0",
    packages=[
        "pytest_pdf",
    ],
    description="A pytest plugin to generated PDF test reports.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=install_requires(),
    entry_points={"pytest11": ["pytest-pdf = pytest_pdf.plugin"]},
)
