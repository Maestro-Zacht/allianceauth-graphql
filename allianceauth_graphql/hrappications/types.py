import graphene
from graphene_django import DjangoObjectType

from allianceauth.hrapplications.models import Application, ApplicationForm, ApplicationChoice, ApplicationQuestion, ApplicationResponse, ApplicationComment


class ApplicationType(DjangoObjectType):
    class Meta:
        model = Application


class ApplicationFormType(DjangoObjectType):
    class Meta:
        model = ApplicationForm


class ApplicationChoiceType(DjangoObjectType):
    class Meta:
        model = ApplicationChoice


class ApplicationQuestionType(DjangoObjectType):
    class Meta:
        model = ApplicationQuestion


class ApplicationResponseType(DjangoObjectType):
    class Meta:
        model = ApplicationResponse


class ApplicationCommentType(DjangoObjectType):
    class Meta:
        model = ApplicationComment
