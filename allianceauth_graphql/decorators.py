from functools import wraps
from graphql_jwt.exceptions import PermissionDenied
from graphql_jwt.decorators import context

from esi.models import Token


def tokens_required(scopes, exc=PermissionDenied):
    def decorator(func):
        @wraps(func)
        @context(func)
        def _wrapped_func(context, *args, **kwargs):
            tokens = Token.objects\
                .filter(user__pk=context.user.pk)\
                .require_scopes(scopes)\
                .require_valid()

            if tokens.exists():
                return func(*args, **kwargs)
            else:
                raise exc('Required token missing')
        return _wrapped_func
    return decorator
