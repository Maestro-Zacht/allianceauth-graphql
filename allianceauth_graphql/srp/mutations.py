import graphene
from graphql_jwt.decorators import login_required, permission_required
from graphene_django.forms.mutation import DjangoFormMutation

from django.utils import timezone
from django.contrib.humanize.templatetags.humanize import intcomma

from allianceauth.srp.form import SrpFleetMainForm
from allianceauth.srp.models import SrpFleetMain, SrpUserRequest
from allianceauth.srp.views import random_string
from allianceauth.srp.managers import SRPManager
from allianceauth.srp.providers import esi
from allianceauth.notifications import notify

from ..decorators import permissions_required
from .types import SrpFleetMainType
from .forms import GQLSrpFleetUserRequestForm


class AddFleetMutation(DjangoFormMutation):
    class Meta:
        form_class = SrpFleetMainForm

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @permissions_required(('auth.srp_management', 'srp.add_srpfleetmain'))
    def perferm_mutate(cls, form: SrpFleetMainForm, info):
        srp_fleet_main = SrpFleetMain()
        srp_fleet_main.fleet_name = form.cleaned_data['fleet_name']
        srp_fleet_main.fleet_doctrine = form.cleaned_data['fleet_doctrine']
        srp_fleet_main.fleet_time = form.cleaned_data['fleet_time']
        srp_fleet_main.fleet_srp_code = random_string(8)
        srp_fleet_main.fleet_commander = info.context.user.profile.main_character

        srp_fleet_main.save()

        return cls(ok=True)


class RemoveFleetMutation(graphene.Mutation):
    class Meta:
        fleet_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @permission_required('auth.srp_management')
    def mutate(cls, root, info, fleet_id):
        SrpFleetMain.objects.filter(pk=fleet_id).delete()
        return cls(ok=True)


class DisableFleetMutation(graphene.Mutation):
    class Meta:
        fleet_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    srp_fleet = graphene.Field(SrpFleetMainType)

    @classmethod
    @login_required
    @permission_required('auth.srp_management')
    def mutate(cls, root, info, fleet_id):
        srpfleetmain = SrpFleetMain.objects.get(pk=fleet_id)
        srpfleetmain.fleet_srp_code = ""
        srpfleetmain.save()
        return cls(ok=True, srp_fleet=srpfleetmain)


class EnableFleetMutation(graphene.Mutation):
    class Meta:
        fleet_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    srp_fleet = graphene.Field(SrpFleetMainType)

    @classmethod
    @login_required
    @permission_required('auth.srp_management')
    def mutate(cls, root, info, fleet_id):
        srpfleetmain = SrpFleetMain.objects.get(pk=fleet_id)
        srpfleetmain.fleet_srp_code = random_string(8)
        srpfleetmain.save()
        return cls(ok=True, srp_fleet=srpfleetmain)


class CompletedFleetMutation(graphene.Mutation):
    class Meta:
        fleet_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    srp_fleet = graphene.Field(SrpFleetMainType)

    @classmethod
    @login_required
    @permission_required('auth.srp_management')
    def mutate(cls, root, info, fleet_id):
        srpfleetmain = SrpFleetMain.objects.get(pk=fleet_id)
        srpfleetmain.fleet_srp_status = "Completed"
        srpfleetmain.save()
        return cls(ok=True, srp_fleet=srpfleetmain)


class UncompletedFleetMutation(graphene.Mutation):
    class Meta:
        fleet_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    srp_fleet = graphene.Field(SrpFleetMainType)

    @classmethod
    @login_required
    @permission_required('auth.srp_management')
    def mutate(cls, root, info, fleet_id):
        srpfleetmain = SrpFleetMain.objects.get(pk=fleet_id)
        srpfleetmain.fleet_srp_status = ""
        srpfleetmain.save()
        return cls(ok=True, srp_fleet=srpfleetmain)


class SrpFleetUserRequestFormMutation(DjangoFormMutation):
    class Meta:
        form_class = GQLSrpFleetUserRequestForm

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @permission_required('srp.access_srp')
    def perform_mutate(cls, form: GQLSrpFleetUserRequestForm, info):
        request_killboard_link = form.cleaned_data['killboard_link']
        killmail_id = SRPManager.get_kill_id(killboard_link=request_killboard_link)

        # check if the killmail_id is already present
        if SrpUserRequest.objects.filter(killboard_link__icontains="/kill/" + killmail_id).exists():
            return cls(ok=False)

        character = info.context.user.profile.main_character
        srp_fleet_main = SrpFleetMain.objects.get(fleet_srp_code=form.cleaned_data['fleet_srp_code'])
        post_time = timezone.now()

        srp_request = SrpUserRequest()
        srp_request.killboard_link = request_killboard_link
        srp_request.additional_info = form.cleaned_data['additional_info']
        srp_request.character = character
        srp_request.srp_fleet_main = srp_fleet_main

        try:
            srp_kill_link = SRPManager.get_kill_id(srp_request.killboard_link)
            (ship_type_id, ship_value, victim_id) = SRPManager.get_kill_data(srp_kill_link)
        except ValueError:
            return cls(ok=False)

        if info.context.user.character_ownerships.filter(character__character_id=str(victim_id)).exists():
            item_type = esi.client.Universe.get_universe_types_type_id(type_id=ship_type_id).result()
            srp_request.srp_ship_name = item_type['name']
            srp_request.kb_total_loss = ship_value
            srp_request.post_time = post_time
            srp_request.save()
            return cls(ok=True)
        else:
            return cls(ok=False)


class SrpRequestRemoveMutation(graphene.Mutation):
    class Arguments:
        request_ids = graphene.List(graphene.ID, required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @permission_required('auth.srp_management')
    def mutate(cls, root, info, request_ids):
        SrpUserRequest.objects.filter(id__in=request_ids).delete()
        return cls(ok=True)


class SrpRequestApproveMutation(graphene.Mutation):
    class Arguments:
        request_ids = graphene.List(graphene.ID, required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @permission_required('auth.srp_management')
    def mutate(cls, root, info, request_ids):
        for srp_request_id in request_ids:
            if SrpUserRequest.objects.filter(id=srp_request_id).exists():
                srpuserrequest = SrpUserRequest.objects.get(id=srp_request_id)
                srpuserrequest.srp_status = "Approved"
                if srpuserrequest.srp_total_amount == 0:
                    srpuserrequest.srp_total_amount = srpuserrequest.kb_total_loss
                srpuserrequest.save()
                notify(
                    srpuserrequest.character.character_ownership.user,
                    'SRP Request Approved',
                    level='success',
                    message='Your SRP request for a {} lost during {} has been approved for {} ISK.'.format(
                        srpuserrequest.srp_ship_name, srpuserrequest.srp_fleet_main.fleet_name,
                        intcomma(srpuserrequest.srp_total_amount))
                )
        return cls(ok=True)


class SrpRequestRejectMutation(graphene.Mutation):
    class Arguments:
        request_ids = graphene.List(graphene.ID, required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @permission_required('auth.srp_management')
    def mutate(cls, root, info, request_ids):
        for srp_request_id in request_ids:
            if SrpUserRequest.objects.filter(id=srp_request_id).exists():
                srpuserrequest = SrpUserRequest.objects.get(id=srp_request_id)
                srpuserrequest.srp_status = "Rejected"
                srpuserrequest.save()
                notify(
                    srpuserrequest.character.character_ownership.user,
                    'SRP Request Rejected',
                    level='danger',
                    message='Your SRP request for a {} lost during {} has been rejected.'.format(
                        srpuserrequest.srp_ship_name, srpuserrequest.srp_fleet_main.fleet_name)
                )
        return cls(ok=True)


class SrpUpdateAmountMutation(graphene.Mutation):
    class Arguments:
        fleet_srp_request_id = graphene.ID(required=True)
        srp_total_amount = graphene.Float(required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @permission_required('auth.srp_management')
    def mutate(cls, root, info, fleet_srp_request_id, srp_total_amount):
        ok = False
        if SrpUserRequest.objects.filter(id=fleet_srp_request_id).exists():
            srp_request = SrpUserRequest.objects.get(id=fleet_srp_request_id)
            srp_request.srp_total_amount = srp_total_amount
            srp_request.save()
            ok = True
        return cls(ok=ok)


class SrpUpdateAARMutation(graphene.Mutation):
    class Arguments:
        fleet_id = graphene.ID(required=True)
        fleet_srp_aar_link = graphene.String(required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @permission_required('auth.srp_management')
    def mutate(cls, root, info, fleet_id, fleet_srp_aar_link):
        srpfleetmain = SrpFleetMain.objects.get(id=fleet_id)
        srpfleetmain.fleet_srp_aar_link = fleet_srp_aar_link
        srpfleetmain.save()
        return cls(ok=True)


class Mutation:
    srp_add_fleet = AddFleetMutation.Field()
    srp_remove_fleet = RemoveFleetMutation.Field()
    srp_disable_fleet = DisableFleetMutation.Field()
    srp_enable_fleet = EnableFleetMutation.Field()
    srp_mark_completed = CompletedFleetMutation.Field()
    srp_mark_uncompleted = UncompletedFleetMutation.Field()
    srp_request = SrpFleetUserRequestFormMutation.Field()
    srp_remove_requests = SrpRequestRemoveMutation.Field()
    srp_approve_requests = SrpRequestApproveMutation.Field()
    srp_reject_requests = SrpRequestRejectMutation.Field()
    srp_update_amount = SrpUpdateAmountMutation.Field()
    srp_update_aar = SrpUpdateAARMutation.Field()
