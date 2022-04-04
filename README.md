# allianceauth-graphql

[![version](https://img.shields.io/pypi/v/allianceauth_graphql.svg)](https://pypi.python.org/pypi/allianceauth_graphql)
[![GitHub issues](https://img.shields.io/github/issues/Maestro-Zacht/allianceauth-graphql)](https://github.com/Maestro-Zacht/allianceauth-graphql/issues)
[![github](https://img.shields.io/badge/docs-github-brightgreen)](https://github.com/Maestro-Zacht/allianceauth-graphql)


GraphQL integration for AllianceAuth


Free software: GNU General Public License v3


Usage
=====

This version is still in pre-alpha, as of v0.1.1 it does nothing.


Setup
=====

The following is assuming you have a functioning AllianceAuth installation.


Install plugin
--------------

1. `pip install allianceauth-graphql`.
2. Add the following apps to the bottom of your `INSTALLED_APPS` in the local.py settings file:
    ``` python
    'allianceauth_graphql',
    'graphene_django',
    ```
3. Add the following settings to your local.py file:
    ``` python
    from datetime import timedelta

    # ...

    GRAPHENE = {
        'SCHEMA': 'allianceauth_graphql.schema.schema',
        "MIDDLEWARE": [
            "graphql_jwt.middleware.JSONWebTokenMiddleware",
        ],
    }

    AUTHENTICATION_BACKENDS += [
        "graphql_jwt.backends.JSONWebTokenBackend",
    ]

    GRAPHQL_JWT = {
        "JWT_VERIFY_EXPIRATION": True,
        "JWT_EXPIRATION_DELTA": timedelta(days=1),
    }
    ```
4. Edit your projects url.py file:

   > It should looks something like this

    ``` python
    from django.conf.urls import include, url
    from allianceauth import urls

    urlpatterns = [
        url(r'', include(urls)),
    ]

    handler500 = 'allianceauth.views.Generic500Redirect'
    handler404 = 'allianceauth.views.Generic404Redirect'
    handler403 = 'allianceauth.views.Generic403Redirect'
    handler400 = 'allianceauth.views.Generic400Redirect'
    ```

   > After the edit:
    
    ``` python
    from django.conf.urls import include, url
    from allianceauth import urls
    from allianceauth_graphql import urls as aa_gql_urls

    urlpatterns = [
        url(r'', include(urls)),
        url(r'graphql/', include(aa_gql_urls)),
    ]

    handler500 = 'allianceauth.views.Generic500Redirect'
    handler404 = 'allianceauth.views.Generic404Redirect'
    handler403 = 'allianceauth.views.Generic403Redirect'
    handler400 = 'allianceauth.views.Generic400Redirect'
    ```
5. Restart AllianceAuth.


Settings
--------

| Setting              | Default          | Description                                                                                                                                 |
| -------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| SHOW_GRAPHIQL        | `True`           | Shows the graphiql UI in the browser                                                                                                        |
| GRAPHQL_LOGIN_SCOPES | `['publicData']` | Tokens needed. Unlike AllianceAuth pages, you need to login with the scopes you'll use, otherwise you won't be able to perform some queries |




Credits
=======
This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage) project template.