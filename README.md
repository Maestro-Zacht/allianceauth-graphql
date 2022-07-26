# allianceauth-graphql

[![version](https://img.shields.io/pypi/v/allianceauth_graphql.svg)](https://pypi.python.org/pypi/allianceauth_graphql)
[![GitHub issues](https://img.shields.io/github/issues/Maestro-Zacht/allianceauth-graphql)](https://github.com/Maestro-Zacht/allianceauth-graphql/issues)
[![github](https://img.shields.io/badge/docs-github-brightgreen)](https://github.com/Maestro-Zacht/allianceauth-graphql)


GraphQL integration for AllianceAuth


Free software: GNU General Public License v3


This version is in alpha, please open an issue if you face any bug.

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
    
    ```python
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
5. Run migrations.
6. If you have `SHOW_GRAPHIQL` setting set to `True` (see below), run collectstatics
7. Restart AllianceAuth.


Community Creations Integration
-------------------------------

Currently the package supports the integration with the following community packages:
* allianceauth-pve v1.1.x

To install the dependencies needed, run `pip install allianceauth-graphql[package1,package2]` for all the packages you want to integrate.


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