import graphene
from graphql_jwt.decorators import login_required, permission_required

from django.db.models import Q

from allianceauth.hrapplications.models import Application, ApplicationForm

from .types import ApplicationType, ApplicationFormType, ApplicationStatus, ApplicationAdminType


class Query:
    hr_corp_applications = graphene.List(ApplicationAdminType)
    hr_finished_corp_applications = graphene.List(ApplicationAdminType)
    hr_list_avaiable_forms = graphene.List(ApplicationFormType)
    hr_personal_applications = graphene.List(ApplicationType, status=ApplicationStatus())
    hr_search_application = graphene.List(ApplicationAdminType, search_string=graphene.String(required=True))

    @login_required
    def resolve_hr_corp_applications(self, info):
        user = info.context.user
        main_char = user.profile.main_character
        res = Application.objects.none()

        if user.is_superuser:
            res = Application.objects.filter(approved=None).order_by('-created')
        elif user.has_perm('auth.human_resources') and main_char and ApplicationForm.objects.filter(corp__corporation_id=main_char.corporation_id).exists():
            res = Application.objects.filter(form__corp__corporation_id=main_char.corporation_id, approved=None).order_by('-created')

        return res

    @login_required
    def resolve_hr_finished_corp_applications(self, info):
        user = info.context.user
        main_char = user.profile.main_character
        res = Application.objects.none()

        if user.is_superuser:
            res = Application.objects.exclude(approved=None).order_by('-created')
        elif user.has_perm('auth.human_resources') and main_char and ApplicationForm.objects.filter(corp__corporation_id=main_char.corporation_id).exists():
            res = Application.objects.filter(form__corp__corporation_id=main_char.corporation_id)\
                .exclude(approved=None).order_by('-created')

        return res

    @login_required
    def resolve_hr_list_avaiable_forms(self, info):
        return ApplicationForm.objects.exclude(applications__user=info.context.user)

    @login_required
    def resolve_hr_personal_applications(self, info, status=None):
        res = info.context.user.applications.all()
        if status is not None:
            if status == ApplicationStatus.PENDING:
                approved = None
            elif status == ApplicationStatus.APPROVED:
                approved = True
            else:
                approved = False
            res = res.filter(approved=approved)
        return res

    @login_required
    @permission_required('auth.human_resources')
    def resolve_hr_search_application(self, info, search_string: str):
        user = info.context.user
        searchstring = search_string.lower()

        app_list = Application.objects.all()
        if not user.is_superuser:
            try:
                app_list = app_list.filter(
                    form__corp__corporation_id=user.profile.main_character.corporation_id)
            except AttributeError:
                return None

        return app_list.filter(
            Q(user__profile__main_character__character_name__icontains=searchstring) |
            Q(user__profile__main_character__corporation_name__icontains=searchstring) |
            Q(user__profile__main_character__alliance_name__icontains=searchstring) |
            Q(user__character_ownerships__character__character_name__icontains=searchstring) |
            Q(user__character_ownerships__character__corporation_name__icontains=searchstring) |
            Q(user__character_ownerships__character__alliance_name__icontains=searchstring) |
            Q(user__username__icontains=searchstring)
        )
