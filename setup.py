from setuptools import setup, find_packages

__version__ = '0.1'

setup(
    name='aiogrouper',
    version=__version__,
    description="Client library for Internet2's Grouper, using asyncio.",
    long_description=open('README.md').read(),
    author='University of Oxford',
    author_email='github@it.ox.ac.uk',
    license='BSD',
    packages=find_packages(),
    install_required=['aiohttp'],
)
    
