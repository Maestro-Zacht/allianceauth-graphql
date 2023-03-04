# Django
from django.urls import include, re_path

# Alliance Auth
from allianceauth import urls

from allianceauth_graphql import urls as aa_gql_urls

urlpatterns = [
    # Alliance Auth URLs
    re_path(r"", include(urls)),

    re_path(r'graphql', include(aa_gql_urls)),
]
