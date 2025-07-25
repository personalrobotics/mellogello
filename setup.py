from setuptools import setup, find_packages

setup(
    name="mellogello",
    version="0.1.0",
    description="Mello teleoperation interface and test script.",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        'pyserial',
    ],
    entry_points={
        'console_scripts': [
            'mellogello-test = mellogello.test_mello:main',
        ],
    },
    python_requires='>=3.7',
)
