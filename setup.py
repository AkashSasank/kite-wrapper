import setuptools
from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(name='kite-wrapper',
      version='0.0.3',
      description='A wrapper for kiteconnect API.',
      url='https://github.com/AkashSasank/kite-wrapper',
      author='Akash Sasank',
      author_email='akashsasank369@gmail.com',
      license='MIT',
      packages=setuptools.find_packages(),
      classifiers=[
          "Programming Language :: Python :: 3",
          "License :: OSI Approved :: MIT License",
          "Operating System :: OS Independent",
      ],
      python_requires='>=3.6',
      install_requires=['kiteconnect', 'selenium==3.141.0', 'numpy==1.20.2', 'pandas==1.2.2', 'stockstats==0.3.2',
                        'mplfinance==0.12.7a7', 'seaborn==0.11.1'], )
