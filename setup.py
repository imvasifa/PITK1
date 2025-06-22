from setuptools import setup, find_packages

setup(
    name="strong-stock-scanner",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        'Flask==2.0.3',
        'pandas==1.3.5',
        'numpy==1.21.6',
        'requests==2.28.2',
        'beautifulsoup4==4.11.2',
        'lxml==4.9.2',
        'Flask-Cors==3.0.10',
        'Flask-Login==0.6.2',
        'email-validator==1.3.1',
        'Flask-WTF==1.0.1',
        'python-dotenv==0.21.1',
        'gunicorn==20.1.0',
    ],
    python_requires='>=3.9, <3.10',
)
