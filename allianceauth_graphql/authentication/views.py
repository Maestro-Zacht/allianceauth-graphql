from django.core import signing
from django.shortcuts import redirect, HttpResponse
from django.conf import settings
from django.contrib.auth.models import User

REGISTRATION_SALT = getattr(settings, "REGISTRATION_SALT", "registration")


def verify_email(request):
    activation_key = request.GET.get('activation_key')
    try:
        dump = signing.loads(activation_key, salt=REGISTRATION_SALT, max_age=settings.ACCOUNT_ACTIVATION_DAYS * 86400)
    except signing.BadSignature:
        return HttpResponse("Invalid signature")

    user = User.objects.get(pk=dump[0])
    user.email = dump[1]
    user.is_active = True
    user.save()

    site = getattr(settings, 'REDIRECT_SITE')
    path = getattr(settings, 'REDIRECT_PATH', '/registration/callback/')

    return redirect(site + path)
