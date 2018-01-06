from setuptools import setup

requires = {
    "core": ["blessings", "six"],
    "tests": ["pytest", "pytest-timeout", "mock"],
    "validation": ["jsonschema"],
}

requires["full"] = list(requires.values())

setup(
    name="pyout",
    version="0.1.0",
    author="Kyle Meyer",
    author_email="kyle@kyleam.com",
    description="Terminal styling for tabular data",
    license="MIT",
    url="https://github.com/pyout/pyout.git",
    py_modules=["pyout"],
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
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "License :: OSI Approved :: MIT License",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: User Interfaces",
        "Topic :: Terminals"
    ],
    keywords=["terminal", "tty", "console", "formatting", "style", "color"]
)
