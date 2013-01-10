from setuptools import setup, find_packages

setup(
    name="gunicorn-websocket",
    version="0.0.2",
    description="Websocket handler for the gunicorn server, a Python wsgi server, fork and modify from gevent-websocket",
    long_description=open("README.rst").read(),
    author="CMGS",
    author_email="ilskdw@gmail.com",
    license="BSD",
    url="http://code.dapps.douban.com/gunicorn-websocket",
    install_requires=("gunicorn", "gevent"),
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
