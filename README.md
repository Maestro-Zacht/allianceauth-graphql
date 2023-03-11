# allianceauth-graphql

[![version](https://img.shields.io/pypi/v/allianceauth_graphql.svg)](https://pypi.python.org/pypi/allianceauth_graphql)
[![GitHub issues](https://img.shields.io/github/issues/Maestro-Zacht/allianceauth-graphql)](https://github.com/Maestro-Zacht/allianceauth-graphql/issues)
[![github](https://img.shields.io/badge/docs-github-brightgreen)](https://github.com/Maestro-Zacht/allianceauth-graphql)
[![codecov](https://codecov.io/gh/Maestro-Zacht/allianceauth-graphql/branch/main/graph/badge.svg?token=S138BBQ4XA)](https://codecov.io/gh/Maestro-Zacht/allianceauth-graphql)


GraphQL integration for AllianceAuth


Free software: GNU General Public License v3


This version is in beta, please open an issue if you face any bug.

Compatibility
=============

Versions `>=0.16` are only compatible with AllianceAuth v3.

Setup
=====

The following is assuming you have a functioning AllianceAuth installation.


Install plugin
--------------

1. `pip install allianceauth-graphql`.
2. Add the following apps to the bottom of your `INSTALLED_APPS` in the local.py settings file:
    ```python
    'allianceauth_graphql',
    'graphene_django',
    "graphql_jwt.refresh_token.apps.RefreshTokenConfig",
    ```
3. Add the following settings to your local.py file:
    ```python
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
        "JWT_LONG_RUNNING_REFRESH_TOKEN": True,
        "JWT_EXPIRATION_DELTA": timedelta(days=1),
        "JWT_REFRESH_EXPIRATION_DELTA": timedelta(days=7),
    }
    ```
    Feel free to edit the expiration limits of your tokens.
4. Edit your projects url.py file:

   > It should looks something like this

    ```python
    from django.conf.urls import include
    from allianceauth import urls
    from django.urls import re_path

    urlpatterns = [
        re_path(r'', include(urls)),
    ]

    handler500 = 'allianceauth.views.Generic500Redirect'
    handler404 = 'allianceauth.views.Generic404Redirect'
    handler403 = 'allianceauth.views.Generic403Redirect'
    handler400 = 'allianceauth.views.Generic400Redirect'
    ```

   > After the edit:
    
    ```python
    from django.conf.urls import include
    from allianceauth import urls
    from allianceauth_graphql import urls as aa_gql_urls
    from django.urls import re_path

    urlpatterns = [
        re_path(r'', include(urls)),
        re_path(r'graphql/', include(aa_gql_urls)),
    ]

    handler500 = 'allianceauth.views.Generic500Redirect'
    handler404 = 'allianceauth.views.Generic404Redirect'
    handler403 = 'allianceauth.views.Generic403Redirect'
    handler400 = 'allianceauth.views.Generic400Redirect'
    ```
5. Run migrations.
6. If you have `SHOW_GRAPHIQL` setting set to `True` (see below), run collectstatics
7. Restart AllianceAuth.


Community Creations Integration
-------------------------------

Currently the package supports the integration with the following community packages:
* allianceauth-pve: v1.11.x

Be sure to check if you have the right versions of these package or the GraphQL will not have the same behaviour as the apps.


Settings
--------

| Setting              | Default                   | Description                                                                                                                                 |
| -------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| SHOW_GRAPHIQL        | `True`                    | Shows the graphiql UI in the browser                                                                                                        |
| GRAPHQL_LOGIN_SCOPES | `['publicData']`          | Tokens needed. Unlike AllianceAuth pages, you need to login with the scopes you'll use, otherwise you won't be able to perform some queries |
| REDIRECT_SITE        | No default                | The URL domain for redirecting after email verification. It has to have the protocol and not the slash at the end: `http(s)://<yoursite>`   |
| REDIRECT_PATH        | `/registration/callback/` | Path to append to REDIRECT_SITE for building the redirect URL                                                                               |



Credits
=======
This package was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) and the [audreyr/cookiecutter-pypackage](https://github.com/audreyr/cookiecutter-pypackage) project template.