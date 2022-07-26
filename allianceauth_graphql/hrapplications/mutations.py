import graphene
from graphql_jwt.decorators import login_required, user_passes_test, permission_required

from allianceauth.hrapplications.views import create_application_test
from allianceauth.hrapplications.models import ApplicationForm, Application, ApplicationResponse, ApplicationComment
from allianceauth.notifications import notify

from .inputs import FormAnswerInputType
from .types import ApplicationAdminType, ApplicationType


class CreateApplicationMutation(graphene.Mutation):
    class Arguments:
        input = FormAnswerInputType(required=True)

    ok = graphene.Boolean()
    application = graphene.Field(ApplicationType)

    @classmethod
    @login_required
    @user_passes_test(create_application_test)
    def mutate(cls, root, info, input):
        user = info.context.user
        app_form = ApplicationForm.objects.get(pk=input.form_id)
        if Application.objects.filter(user=user).filter(form=app_form).exists():
            ok = False
            application = None
        else:
            responses = {ans.question_id: ans.answer for ans in input.responses}

            application = Application.objects.create(user=user, form=app_form)
            for question in app_form.questions.all():
                response = ApplicationResponse(question=question, application=application)
                response.answer = "\n".join(responses.get(question.pk, []))
                response.save()

        return cls(ok=ok, application=application)


class DeleteApplicationMutation(graphene.Mutation):
    class Arguments:
        application_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    def mutate(cls, root, info, application_id):
        app = Application.objects.get(pk=application_id)

        if app.user == info.context.user and app.approved is None:
            app.delete()
            ok = True
        else:
            ok = False

        return cls(ok=ok)


class AddApplicationCommentMutation(graphene.Mutation):
    class Arguments:
        comment = graphene.String(required=True)
        application_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    application = graphene.Field(ApplicationAdminType)

    @classmethod
    @login_required
    @permission_required('auth.human_resources')
    @permission_required('hrapplications.add_applicationcomment')
    def mutate(cls, root, info, comment, application_id):
        user = info.context.user
        app = Application.objects.get(pk=application_id)

        ApplicationComment.objects.create(
            application=app,
            user=user,
            text=comment,
        )

        return cls(ok=True, application=app)


class AdminRemoveApplicationMutation(graphene.Mutation):
    class Arguments:
        application_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    @classmethod
    @login_required
    @permission_required('auth.human_resources')
    @permission_required('hrapplications.delete_application')
    def mutate(cls, root, info, application_id):
        app = Application.objects.get(pk=application_id)
        app.delete()
        notify(app.user, "Application Deleted", message="Your application to %s was deleted." % app.form.corp)
        return cls(ok=True)


class AdminApproveApplication(graphene.Mutation):
    class Arguments:
        application_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    application = graphene.Field(ApplicationAdminType)

    @classmethod
    @login_required
    @permission_required('auth.human_resources')
    @permission_required('hrapplications.approve_application')
    def mutate(cls, root, info, application_id):
        user = info.context.user
        app = Application.objects.get(pk=application_id)
        if user.is_superuser or user == app.reviewer:
            app.approved = True
            app.save()
            notify(app.user, "Application Accepted", message="Your application to %s has been approved." % app.form.corp, level="success")
            ok = True
        else:
            ok = False

        return cls(ok=ok, application=app)


class AdminRejectApplication(graphene.Mutation):
    class Arguments:
        application_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    application = graphene.Field(ApplicationAdminType)

    @classmethod
    @login_required
    @permission_required('auth.human_resources')
    @permission_required('hrapplications.reject_application')
    def mutate(cls, root, info, application_id):
        user = info.context.user
        app = Application.objects.get(pk=application_id)
        if user.is_superuser or user == app.reviewer:
            app.approved = False
            app.save()
            notify(app.user, "Application Accepted", message="Your application to %s has been approved." % app.form.corp, level="success")
            ok = True
        else:
            ok = False

        return cls(ok=ok, application=app)


class AdminMarkInProgressApplication(graphene.Mutation):
    class Arguments:
        application_id = graphene.ID(required=True)

    ok = graphene.Boolean()
    application = graphene.Field(ApplicationAdminType)

    @classmethod
    @login_required
    @permission_required('auth.human_resources')
    def mutate(cls, root, info, application_id):
        user = info.context.user
        app = Application.objects.get(pk=application_id)
        if not app.reviewer:
            app.reviewer = user
            app.reviewer_character = user.profile.main_character
            app.save()
            notify(app.user, "Application In Progress", message=f"Your application to {app.form.corp} is being reviewed by {app.reviewer_str}")
            ok = True
        else:
            ok = False

        return cls(ok=ok, application=app)


class Mutation:
    hr_create_application = CreateApplicationMutation.Field()
    hr_delete_application = DeleteApplicationMutation.Field()
    hr_add_application_comment = AddApplicationCommentMutation.Field()
    hr_admin_remove_application = AdminRemoveApplicationMutation.Field()
    hr_admin_approve_application = AdminApproveApplication.Field()
    hr_admin_reject_application = AdminRejectApplication.Field()
    hr_admin_mark_in_progress_application = AdminMarkInProgressApplication.Field()
