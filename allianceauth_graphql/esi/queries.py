import graphene
from graphql_jwt.decorators import login_required

from .types import TokenType


class Query:
    user_tokens = graphene.List(TokenType)

    @login_required
    def resolve_user_tokens(self, info):
        return info.context.user.token_set.all()
