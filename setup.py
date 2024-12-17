from setuptools import setup
import versioneer

setup(
    name="pyout",
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    author="Kyle Meyer",
    author_email="kyle@kyleam.com",
    description="Terminal styling for tabular data",
    license="MIT",
    url="https://github.com/pyout/pyout.git",
    packages=["pyout", "pyout.tests"],
    python_requires=">=3.7",
    install_requires=[
        "blessed; sys_platform != 'win32'",
        "jsonschema>=3.0.0",
    ],
    long_description=open("README.rst").read(),
    classifiers=[
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Environment :: Console",
        "Development Status :: 1 - Planning",
        "Topic :: Utilities",
        "Operating System :: POSIX",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: User Interfaces",
        "Topic :: Terminals"
    ],
    keywords=["terminal", "tty", "console", "formatting", "style", "color"]
)
