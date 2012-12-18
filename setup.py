from setuptools import setup, find_packages

setup(
    name="gunicorn-websocket",
    version="0.0.1",
    description="Websocket handler for the gunicorn server, a Python network library",
    author="CMGS",
    author_email="ilskdw@gmail.me",
    license="BSD",
    url="http://code.dapps.douban.com/gunicorn-websocket",
    install_requires=("gunicorn", ),
    packages=find_packages(exclude=["examples","tests"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Intended Audience :: Developers",
    ],
)
