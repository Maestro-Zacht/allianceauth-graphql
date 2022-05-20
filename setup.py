#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.md') as readme_file:
    readme = readme_file.read()

requirements = [
    'allianceauth>=2.11.2,<3.0.0',
    'graphene-django>=2.13,<3.0.0',
    'django-graphql-jwt>=0.3.0,<0.4.0',
    # 'django-cors-headers>=3.7,<4.0.0',
]

test_requirements = []

setup(
    author="Matteo Ghia",
    author_email='matteo.ghia@yahoo.it',
    python_requires='>=3.6',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Operating System :: POSIX :: Linux',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    description="GraphQL integration for AllianceAuth",
    install_requires=requirements,
    extras_require={
        'allianceauth-pve': [
            'graphene-django-extras>=0.4.6,<0.5.0',
            'allianceauth-pve>=1.1.0,<1.2.0',
        ]
    },
    license="GNU General Public License v3",
    long_description=readme,
    long_description_content_type='text/markdown',
    include_package_data=True,
    keywords='allianceauth_graphql',
    name='allianceauth_graphql',
    packages=find_packages(include=['allianceauth_graphql', 'allianceauth_graphql.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/Maestro-Zacht/allianceauth-graphql',
    version='0.9.0',
    zip_safe=False,
)
