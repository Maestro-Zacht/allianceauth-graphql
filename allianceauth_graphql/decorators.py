from functools import wraps
from graphql_jwt.exceptions import PermissionDenied
from graphql_jwt.decorators import context, user_passes_test

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


def permissions_required(perm):
    """
    Decorator for views that checks whether a user has any particular permission
    enabled.

    This decorator is the graphql modified version of the allianceauth permission_required.
    """
    def check_perms(user):
        for perm_ in perm:
            perm_ = (perm_,)
            if user.has_perms(perm_):
                return True

        return False
    return user_passes_test(check_perms)
