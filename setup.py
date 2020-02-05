import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Ajani",
    version="0.0.1",
    author="Silasary",
    description="Discord bot",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/silasary/modbot",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
