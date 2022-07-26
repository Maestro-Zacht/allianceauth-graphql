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


def permissions_required(perm, raise_exception=False):
    """
    Decorator for views that checks whether a user has a particular permission
    enabled.
    If the raise_exception parameter is given the PermissionDenied exception
    is raised.

    This decorator is the graphql version of the allianceauth permission_required.
    """
    def check_perms(user):
        if isinstance(perm, str):
            perms = (perm,)
        else:
            perms = perm

        for perm_ in perms:
            perm_ = (perm_,)
            if user.has_perms(perm_):
                return True

        if raise_exception:
            raise PermissionDenied

        return False
    return user_passes_test(check_perms)
