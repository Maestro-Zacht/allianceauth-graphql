import graphene
from graphene_django import DjangoObjectType

from allianceauth.hrapplications.models import Application, ApplicationForm, ApplicationChoice, ApplicationQuestion, ApplicationResponse, ApplicationComment


class ApplicationStatus(graphene.Enum):
    PENDING = 1
    APPROVED = 2
    REJECTED = 3


class ApplicationType(DjangoObjectType):
    status = graphene.Field(ApplicationStatus, required=True)

    class Meta:
        model = Application
        fields = ('id', 'user', 'form', 'created', 'responses')

    def resolve_status(self, info):
        if self.approved is None:
            return ApplicationStatus.PENDING
        if self.approved:
            return ApplicationStatus.APPROVED
        return ApplicationStatus.REJECTED


class ApplicationAdminType(DjangoObjectType):
    status = graphene.Field(ApplicationStatus, required=True)

    class Meta:
        model = Application
        exclude = ('approved',)

    def resolve_status(self, info):
        if self.approved is None:
            return ApplicationStatus.PENDING
        if self.approved:
            return ApplicationStatus.APPROVED
        return ApplicationStatus.REJECTED


class ApplicationFormType(DjangoObjectType):
    class Meta:
        model = ApplicationForm
        fields = ('id', 'questions', 'corp', )


class ApplicationChoiceType(DjangoObjectType):
    class Meta:
        model = ApplicationChoice


class ApplicationQuestionType(DjangoObjectType):
    class Meta:
        model = ApplicationQuestion
        fields = ('id', 'title', 'help_text', 'multi_select', 'choices',)


class ApplicationResponseType(DjangoObjectType):
    class Meta:
        model = ApplicationResponse


class ApplicationCommentType(DjangoObjectType):
    class Meta:
        model = ApplicationComment
