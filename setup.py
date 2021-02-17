import setuptools
from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(name='kite-wrapper',
      version='0.0.1',
      description='A wrapper for kiteconnect API.',
      url='#',
      author='Akash Sasank',
      author_email='akashsasank369@gmail.com',
      license='MIT',
      packages=setuptools.find_packages(),
      classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: MIT License",
            "Operating System :: OS Independent",
      ],
      python_requires='>=3.6',)
