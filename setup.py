from setuptools import setup

requires = {
    "core": [
        # formergly blessings were used, code allows for either
        # see https://github.com/pyout/pyout/issues/136
        "blessed; sys_platform != 'win32'",
        "jsonschema>=3.0.0",
    ],
    "tests": ["pytest", "pytest-timeout"],
}

requires["full"] = list(requires.values())

setup(
    name="pyout",
    version="0.7.3",
    author="Kyle Meyer",
    author_email="kyle@kyleam.com",
    description="Terminal styling for tabular data",
    license="MIT",
    url="https://github.com/pyout/pyout.git",
    packages=["pyout", "pyout.tests"],
    python_requires=">=3.7",
    tests_require=requires["tests"],
    setup_requires=["pytest-runner"],
    install_requires=requires["core"],
    extras_require=requires,
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
