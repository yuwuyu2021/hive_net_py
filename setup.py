"""
HiveNet 安装配置
"""
from setuptools import setup, find_packages

setup(
    name="hive_net_py",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'dataclasses;python_version<"3.7"',
    ],
    python_requires='>=3.6',
) 