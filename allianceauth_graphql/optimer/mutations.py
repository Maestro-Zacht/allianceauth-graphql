import graphene
from graphene_django.forms.mutation import DjangoFormMutation
from graphql_jwt.decorators import login_required, permission_required

from allianceauth.optimer.form import OpForm
from allianceauth.optimer.models import OpTimer, OpTimerType

from .forms import EditOpForm


class OpFormMutation(DjangoFormMutation):
    class Meta:
        form_class = OpForm

    @classmethod
    @login_required
    @permission_required('auth.optimer_management')
    def perform_mutate(cls, form: OpForm, info):
        optimer_type = None
        if form.cleaned_data['type'] != '':
            try:
                optimer_type = OpTimerType.objects.get(
                    type__iexact=form.cleaned_data['type']
                )
            except OpTimerType.DoesNotExist:
                optimer_type = OpTimerType.objects.create(
                    type=form.cleaned_data['type']
                )

        character = info.context.user.profile.main_character
        op = OpTimer()
        op.doctrine = form.cleaned_data['doctrine']
        op.system = form.cleaned_data['system']
        op.start = form.cleaned_data['start']
        op.duration = form.cleaned_data['duration']
        op.operation_name = form.cleaned_data['operation_name']
        op.fc = form.cleaned_data['fc']
        op.eve_character = character
        op.type = optimer_type
        op.description = form.cleaned_data['description']
        op.save()

        return cls(**form.cleaned_data)


class RemoveOpTimerMutation(graphene.Mutation):
    class Arguments:
        optimer_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @permission_required('auth.optimer_management')
    def mutate(cls, root, info, optimer_id):
        op = OpTimer.objects.get(pk=optimer_id)
        op.delete()
        return cls(ok=True)


class OpFormEditMutation(DjangoFormMutation):
    class Meta:
        form_class = EditOpForm

    @classmethod
    @login_required
    @permission_required('auth.optimer_management')
    def perform_mutate(cls, form: OpForm, info):
        op: OpTimer = OpTimer.objects.get(pk=form.cleaned_data['id'])

        character = info.context.user.profile.main_character

        optimer_type = None

        if form.cleaned_data['type'] != '':
            try:
                optimer_type = OpTimerType.objects.get(
                    type__iexact=form.cleaned_data['type']
                )
            except OpTimerType.DoesNotExist:
                optimer_type = OpTimerType.objects.create(
                    type=form.cleaned_data['type']
                )

        op.doctrine = form.cleaned_data['doctrine']
        op.system = form.cleaned_data['system']
        op.start = form.cleaned_data['start']
        op.duration = form.cleaned_data['duration']
        op.operation_name = form.cleaned_data['operation_name']
        op.fc = form.cleaned_data['fc']
        op.eve_character = character
        op.type = optimer_type
        op.description = form.cleaned_data['description']
        op.save()

        return cls(**form.cleaned_data)


class Mutation:
    optimer_new_op = OpFormMutation.Field()
    optimer_remove_op = RemoveOpTimerMutation.Field()
    optimer_edit_op = OpFormEditMutation.Field()
