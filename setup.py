import codecs
import os.path

from setuptools import find_packages, setup

HERE = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    return codecs.open(os.path.join(HERE, *parts), 'r').read()


setup(
    name='aws-iam-generator',
    version='0.9.2',
    packages=find_packages(exclude=(
        'tests'
    )),
    install_requires=[
        "marshmallow==3.3.0",
        "troposphere==2.6.3 ",
        "PyYAML==5.3"
    ],
    author="Michal Murawski",
    author_email="mmurawski777@gmail.com",
    description="Utilities package for pynamodb.",
    long_description=read('README.md'),
    long_description_content_type="text/markdown",
    url="https://github.com/micmurawski/aws-iam-generator",
    include_package_data=True,
    python_requires='>=3.6',
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8"
    ],
)
