from graphene_django.utils.testing import GraphQLTestCase

from allianceauth.tests.auth_utils import AuthUtils
from app_utils.testdata_factories import UserMainFactory, EveCorporationInfoFactory, EveCharacterFactory

from allianceauth.hrapplications.models import Application, ApplicationForm, ApplicationQuestion, ApplicationComment
from allianceauth.notifications.models import Notification

from ..hrapplications.types import ApplicationStatus


class TestQueriesAndTypes(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory()

        cls.character = cls.user.profile.main_character
        cls.corp = cls.character.corporation

        char2 = EveCharacterFactory(corporation=cls.corp)
        cls.user2 = UserMainFactory(main_character__character=char2)

        cls.corp2 = EveCorporationInfoFactory()

        cls.question1 = ApplicationQuestion.objects.create(title="Question 1")
        cls.choice1 = cls.question1.choices.create(choice_text="Choice 1")

        cls.form = ApplicationForm.objects.create(corp=cls.corp)
        cls.form.questions.add(cls.question1)

        cls.pending_application = Application.objects.create(
            user=cls.user,
            form=cls.form,
            approved=None
        )

        cls.form2 = ApplicationForm.objects.create(corp=cls.corp2)
        cls.form2.questions.add(cls.question1)

        cls.pending_application2 = Application.objects.create(
            user=cls.user,
            form=cls.form2,
            approved=None
        )

        cls.corp3 = EveCorporationInfoFactory()

        cls.form3 = ApplicationForm.objects.create(corp=cls.corp3)
        cls.form3.questions.add(cls.question1)

        cls.rejected_application = Application.objects.create(
            user=cls.user,
            form=cls.form3,
            approved=False
        )

        cls.approved_application = Application.objects.create(
            user=cls.user2,
            form=cls.form3,
            approved=True
        )

        cls.corp4 = EveCorporationInfoFactory()

        cls.form4 = ApplicationForm.objects.create(corp=cls.corp4)
        cls.form4.questions.add(cls.question1)

    def test_hr_corp_applications_superuser(self):
        self.client.force_login(self.user)

        self.user.is_superuser = True
        self.user.save()

        response = self.query(
            '''
            query {
                hrCorpApplications {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrCorpApplications": [
                        {
                            "id": str(self.pending_application2.id)
                        },
                        {
                            "id": str(self.pending_application.id)
                        },
                    ]
                }
            }
        )

    def test_hr_corp_applications_perms(self):
        user = AuthUtils.add_permission_to_user_by_name('auth.human_resources', self.user, False)

        self.client.force_login(user)

        response = self.query(
            '''
            query {
                hrCorpApplications {
                    id
                    status
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrCorpApplications": [
                        {
                            "id": str(self.pending_application.id),
                            "status": ApplicationStatus.PENDING.name
                        },
                    ]
                }
            }
        )

    def test_hr_corp_applications_no_access(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                hrCorpApplications {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrCorpApplications": []
                }
            }
        )

    def test_hr_finished_corp_applications_superuser(self):
        self.client.force_login(self.user)

        self.user.is_superuser = True
        self.user.save()

        response = self.query(
            '''
            query {
                hrFinishedCorpApplications {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrFinishedCorpApplications": [
                        {
                            "id": str(self.approved_application.id)
                        },
                        {
                            "id": str(self.rejected_application.id)
                        },
                    ]
                }
            }
        )

    def test_hr_finished_corp_applications_perms(self):
        user = AuthUtils.add_permission_to_user_by_name('auth.human_resources', self.user, False)

        self.client.force_login(user)

        self.character.corporation_id = self.corp3.corporation_id
        self.character.save()

        response = self.query(
            '''
            query {
                hrFinishedCorpApplications {
                    id
                    status
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrFinishedCorpApplications": [
                        {
                            "id": str(self.approved_application.id),
                            "status": ApplicationStatus.APPROVED.name
                        },
                        {
                            "id": str(self.rejected_application.id),
                            "status": ApplicationStatus.REJECTED.name
                        },
                    ]
                }
            }
        )

    def test_hr_finished_corp_applications_no_access(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                hrFinishedCorpApplications {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrFinishedCorpApplications": []
                }
            }
        )

    def test_hr_list_available_forms(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                hrListAvailableForms {
                    id
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrListAvailableForms": [
                        {
                            "id": str(self.form4.id),
                        },
                    ]
                }
            }
        )

    def test_hr_personal_applications_all(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query {
                hrPersonalApplications {
                    id
                    status
                }
            }
            '''
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrPersonalApplications": [
                        {
                            "id": str(self.pending_application.id),
                            "status": ApplicationStatus.PENDING.name
                        },
                        {
                            "id": str(self.pending_application2.id),
                            "status": ApplicationStatus.PENDING.name
                        },
                        {
                            "id": str(self.rejected_application.id),
                            "status": ApplicationStatus.REJECTED.name
                        },
                    ]
                }
            }
        )

    def test_hr_personal_applications_pending(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($status: ApplicationStatus) {
                hrPersonalApplications(status: $status) {
                    id
                }
            }
            ''',
            variables={
                "status": ApplicationStatus.PENDING.name
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrPersonalApplications": [
                        {
                            "id": str(self.pending_application.id)
                        },
                        {
                            "id": str(self.pending_application2.id)
                        },
                    ]
                }
            }
        )

    def test_hr_personal_applications_rejected(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            query($status: ApplicationStatus) {
                hrPersonalApplications(status: $status) {
                    id
                }
            }
            ''',
            variables={
                "status": ApplicationStatus.REJECTED.name
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrPersonalApplications": [
                        {
                            "id": str(self.rejected_application.id)
                        },
                    ]
                }
            }
        )

    def test_hr_personal_applications_approved(self):
        self.client.force_login(self.user2)

        response = self.query(
            '''
            query($status: ApplicationStatus) {
                hrPersonalApplications(status: $status) {
                    id
                    status
                }
            }
            ''',
            variables={
                "status": ApplicationStatus.APPROVED.name
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrPersonalApplications": [
                        {
                            "id": str(self.approved_application.id),
                            "status": ApplicationStatus.APPROVED.name
                        },
                    ]
                }
            }
        )

    def test_hr_search_application_superuser(self):
        self.client.force_login(self.user)

        self.user.is_superuser = True
        self.user.save()

        response = self.query(
            '''
            query($searchString: String!) {
                hrSearchApplication(searchString: $searchString) {
                    id
                    status
                }
            }
            ''',
            variables={
                "searchString": self.corp.corporation_name
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrSearchApplication": [
                        {
                            'id': str(self.pending_application.id),
                            'status': ApplicationStatus.PENDING.name
                        },
                        {
                            'id': str(self.pending_application2.id),
                            'status': ApplicationStatus.PENDING.name
                        },
                        {
                            "id": str(self.rejected_application.id),
                            "status": ApplicationStatus.REJECTED.name
                        },
                        {
                            'id': str(self.approved_application.id),
                            'status': ApplicationStatus.APPROVED.name
                        }
                    ]
                }
            }
        )

    def test_hr_search_application_perms(self):
        user = AuthUtils.add_permission_to_user_by_name('auth.human_resources', self.user, False)

        self.client.force_login(user)

        response = self.query(
            '''
            query($searchString: String!) {
                hrSearchApplication(searchString: $searchString) {
                    id
                }
            }
            ''',
            variables={
                "searchString": self.corp3.corporation_name
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrSearchApplication": []
                }
            }
        )

    def test_hr_search_application_error(self):
        user = AuthUtils.add_permission_to_user_by_name('auth.human_resources', self.user, False)

        self.client.force_login(user)

        self.character.delete()

        response = self.query(
            '''
            query($searchString: String!) {
                hrSearchApplication(searchString: $searchString) {
                    id
                }
            }
            ''',
            variables={
                "searchString": self.corp3.corporation_name
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrSearchApplication": None
                }
            }
        )


class TestCreateApplicationMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory()

        cls.corp = cls.user.profile.main_character.corporation

        cls.question1 = ApplicationQuestion.objects.create(title="Question 1")
        cls.choice1 = cls.question1.choices.create(choice_text="Choice 1")

        cls.form = ApplicationForm.objects.create(corp=cls.corp)
        cls.form.questions.add(cls.question1)

        cls.form_data = {
            'formId': cls.form.pk,
            'responses': [
                {
                    'questionId': cls.question1.pk,
                    'answer': ['Choice 1']
                }
            ]
        }

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($input: FormAnswerInputType!) {
                hrCreateApplication(input: $input) {
                    ok
                    application {
                        form {
                            id
                        }
                    }
                }
            }
            ''',
            input_data=self.form_data
        )

        self.assertJSONEqual(
            response.content,
            {
                "data": {
                    "hrCreateApplication": {
                        "ok": True,
                        "application": {
                            'form': {
                                'id': str(self.form.pk)
                            }
                        }
                    }
                }
            }
        )

    def test_already_existing(self):
        self.client.force_login(self.user)

        Application.objects.create(
            user=self.user,
            form=self.form
        )

        response = self.query(
            '''
            mutation($input: FormAnswerInputType!) {
                hrCreateApplication(input: $input) {
                    ok
                    application {
                        form {
                            id
                        }
                    }
                }
            }
            ''',
            input_data=self.form_data
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'hrCreateApplication': {
                        'ok': False,
                        'application': None
                    }
                }
            }
        )


class TestDeleteApplicationMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = UserMainFactory()

        corp = cls.user.profile.main_character.corporation

        form = ApplicationForm.objects.create(corp=corp)

        cls.application: Application = Application.objects.create(
            form=form,
            user=cls.user,
            approved=True
        )

    def test_ok(self):
        self.client.force_login(self.user)

        self.application.approved = None
        self.application.save()

        response = self.query(
            '''
            mutation($applicationId: ID!) {
                hrDeleteApplication(applicationId: $applicationId) {
                    ok
                }
            }
            ''',
            variables={
                'applicationId': self.application.pk
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'hrDeleteApplication': {
                        'ok': True
                    }
                }
            }
        )

        self.assertEqual(Application.objects.count(), 0)

    def test_not_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($applicationId: ID!) {
                hrDeleteApplication(applicationId: $applicationId) {
                    ok
                }
            }
            ''',
            variables={
                'applicationId': self.application.pk
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'hrDeleteApplication': {
                        'ok': False
                    }
                }
            }
        )

        self.assertEqual(Application.objects.count(), 1)


class TestAddApplicationCommentMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permissions_to_user_by_name(
            [
                'auth.human_resources',
                'hrapplications.add_applicationcomment'
            ],
            UserMainFactory(),
            False
        )

        corp = cls.user.profile.main_character.corporation

        form = ApplicationForm.objects.create(corp=corp)

        cls.application: Application = Application.objects.create(
            form=form,
            user=cls.user,
        )

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($applicationId: ID!, $comment: String!) {
                hrAddApplicationComment(applicationId: $applicationId, comment: $comment) {
                    ok
                    application {
                        comments {
                            text
                        }
                    }
                }
            }
            ''',
            variables={
                'applicationId': self.application.pk,
                'comment': "Test comment"
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'hrAddApplicationComment': {
                        'ok': True,
                        'application': {
                            'comments': [
                                {
                                    'text': "Test comment"
                                }
                            ]
                        }
                    }
                }
            }
        )

        self.assertEqual(ApplicationComment.objects.count(), 1)


class TestAdminRemoveApplicationMutation(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permissions_to_user_by_name(
            [
                'auth.human_resources',
                'hrapplications.delete_application'
            ],
            UserMainFactory(),
            False
        )

        corp = cls.user.profile.main_character.corporation

        form = ApplicationForm.objects.create(corp=corp)

        cls.application: Application = Application.objects.create(
            form=form,
            user=cls.user,
        )

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($applicationId: ID!) {
                hrAdminRemoveApplication(applicationId: $applicationId) {
                    ok
                }
            }
            ''',
            variables={
                'applicationId': self.application.pk,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'hrAdminRemoveApplication': {
                        'ok': True,
                    }
                }
            }
        )

        self.assertEqual(Notification.objects.count(), 1)

        self.assertEqual(Application.objects.count(), 0)


class TestAdminApproveAndRejectApplication(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permissions_to_user_by_name(
            [
                'auth.human_resources',
                'hrapplications.approve_application',
                'hrapplications.reject_application'
            ],
            UserMainFactory(),
            False
        )

        cls.user2 = UserMainFactory()

        corp = cls.user2.profile.main_character.corporation

        form = ApplicationForm.objects.create(corp=corp)

        cls.application: Application = Application.objects.create(
            form=form,
            user=cls.user2
        )

    def test_approve_ok(self):
        self.client.force_login(self.user)

        self.user.is_superuser = True
        self.user.save()

        response = self.query(
            '''
            mutation($applicationId: ID!) {
                hrAdminApproveApplication(applicationId: $applicationId) {
                    ok
                    application {
                        status
                    }
                }
            }
            ''',
            variables={
                'applicationId': self.application.pk,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'hrAdminApproveApplication': {
                        'ok': True,
                        'application': {
                            'status': ApplicationStatus.APPROVED.name
                        }
                    }
                }
            }
        )

        self.assertEqual(Notification.objects.count(), 1)

    def test_approve_not_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($applicationId: ID!) {
                hrAdminApproveApplication(applicationId: $applicationId) {
                    ok
                    application {
                        status
                    }
                }
            }
            ''',
            variables={
                'applicationId': self.application.pk,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'hrAdminApproveApplication': {
                        'ok': False,
                        'application': {
                            'status': ApplicationStatus.PENDING.name
                        }
                    }
                }
            }
        )

        self.assertEqual(Notification.objects.count(), 0)

    def test_reject_ok(self):
        self.client.force_login(self.user)

        self.user.is_superuser = True
        self.user.save()

        response = self.query(
            '''
            mutation($applicationId: ID!) {
                hrAdminRejectApplication(applicationId: $applicationId) {
                    ok
                    application {
                        status
                    }
                }
            }
            ''',
            variables={
                'applicationId': self.application.pk,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'hrAdminRejectApplication': {
                        'ok': True,
                        'application': {
                            'status': ApplicationStatus.REJECTED.name
                        }
                    }
                }
            }
        )

        self.assertEqual(Notification.objects.count(), 1)

    def test_reject_not_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($applicationId: ID!) {
                hrAdminRejectApplication(applicationId: $applicationId) {
                    ok
                    application {
                        status
                    }
                }
            }
            ''',
            variables={
                'applicationId': self.application.pk,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'hrAdminRejectApplication': {
                        'ok': False,
                        'application': {
                            'status': ApplicationStatus.PENDING.name
                        }
                    }
                }
            }
        )

        self.assertEqual(Notification.objects.count(), 0)


class TestAdminMarkInProgressApplication(GraphQLTestCase):
    maxDiff = None

    @classmethod
    def setUpTestData(cls):
        cls.user = AuthUtils.add_permission_to_user_by_name('auth.human_resources', UserMainFactory(), False)

        cls.user2 = UserMainFactory()

        corp = cls.user2.profile.main_character.corporation

        form = ApplicationForm.objects.create(corp=corp)

        cls.application: Application = Application.objects.create(
            form=form,
            user=cls.user2
        )

    def test_ok(self):
        self.client.force_login(self.user)

        response = self.query(
            '''
            mutation($applicationId: ID!) {
                hrAdminMarkInProgressApplication(applicationId: $applicationId) {
                    ok
                    application {
                        reviewer {
                            id
                        }
                        reviewerCharacter {
                            id
                        }
                    }
                }
            }
            ''',
            variables={
                'applicationId': self.application.pk,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'hrAdminMarkInProgressApplication': {
                        'ok': True,
                        'application': {
                            'reviewer': {
                                'id': str(self.user.id)
                            },
                            'reviewerCharacter': {
                                'id': str(self.user.profile.main_character.id)
                            }
                        }
                    }
                }
            }
        )

        self.assertEqual(Notification.objects.count(), 1)

    def test_not_ok(self):
        self.client.force_login(self.user)

        self.application.reviewer = self.user
        self.application.save()

        response = self.query(
            '''
            mutation($applicationId: ID!) {
                hrAdminMarkInProgressApplication(applicationId: $applicationId) {
                    ok
                }
            }
            ''',
            variables={
                'applicationId': self.application.pk,
            }
        )

        self.assertJSONEqual(
            response.content,
            {
                'data': {
                    'hrAdminMarkInProgressApplication': {
                        'ok': False,
                    }
                }
            }
        )

        self.assertEqual(Notification.objects.count(), 0)
