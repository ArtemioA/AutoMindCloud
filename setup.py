import io
import os
from setuptools import setup
from setuptools import find_packages

#https://widdowquinn.github.io/coding/update-pypi-package/

def read(rel_path: str) -> str:
    here = os.path.abspath(os.path.dirname(__file__))
    # intentionally *not* adding an encoding option to open, See:
    #   https://github.com/pypa/virtualenv/issues/201#issuecomment-3145690
    with open(os.path.join(here, rel_path)) as fp:
        return fp.read()


def get_version(rel_path: str) -> str:
    for line in read(rel_path).splitlines():
        if line.startswith("__version__"):
            # __version__ = "0.12.2"
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    raise RuntimeError("Unable to find version string.")

version = "5.389" #python setup.py sdist bdist_wheel"#get_version("Artemix/__about__.py")

with io.open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r") as f:
    install_requires = [x.strip() for x in f.readlines()]

#
setup(
    name="AutoMindCloud",
    version=version,
    description="A library for Industrial Engineering",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Artemio Araya Day",
    author_email="arthemioxz@gmail.com",
    url="",
    download_url="",
    license="MIT",
    install_requires=install_requires,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU Lesser General Public License v2 (LGPLv2)",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Mathematics",
    ],
    keywords=[
        "Computer Algebra Render",
    ],
    packages=find_packages(),
    include_package_data=True,
)


#Code from lululxvi
