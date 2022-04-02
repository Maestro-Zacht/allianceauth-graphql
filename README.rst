####################
allianceauth-graphql
####################


.. image:: https://img.shields.io/pypi/v/allianceauth_graphql.svg
        :target: https://pypi.python.org/pypi/allianceauth_graphql



GraphQL integration for AllianceAuth


* Free software: GNU General Public License v3


Usage
=====

This version is still in pre-alpha, as of v0.1.1 it does nothing.


Setup
=====

The following is assuming you have a functioning AllianceAuth installation.


Install plugin
--------------

1. :code:`pip install allianceauth-graphql`.
2. Add :code:`'allianceauth_graphql'` (note the underscore) to the bottom of your :code:`INSTALLED_APPS` in the local.py settings file.
3. Edit your projects url.py file:

   > It should look something like this

   .. code:: python
    from django.conf.urls import include, url
    from allianceauth import urls

    urlpatterns = [
        url(r'', include(urls)),
    ]

    handler500 = 'allianceauth.views.Generic500Redirect'
    handler404 = 'allianceauth.views.Generic404Redirect'
    handler403 = 'allianceauth.views.Generic403Redirect'
    handler400 = 'allianceauth.views.Generic400Redirect'

   > After the edit:


   .. code:: python
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




Settings
--------

test


Credits
=======
This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
