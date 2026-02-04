from django.contrib.auth import get_user_model

from documents.models import Document, DocumentFile, DocumentTag, Tag
from documents.tests.base import TemporaryMediaRootTestCase

User = get_user_model()


class DocumentQuerySetTests(TemporaryMediaRootTestCase):
    def setUp(self):
        super().setUp()

        self.user = User.objects.create_user(
            username="user1",
            password="password",
        )

        self.other_user = User.objects.create_user(
            username="user2",
            password="password",
        )

    def test_for_user_filters_documents(self):
        # Arrange & Act
        Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(name="file1.pdf"),
        )
        Document.create_from_file(
            owner=self.other_user,
            uploaded_file=self._upload_test_file(name="file2.pdf"),
        )

        user_documents = Document.objects.for_user(self.user)

        # Assert
        self.assertEqual(user_documents.count(), 1)
        self.assertEqual(user_documents.first().owner, self.user)

    def test_with_files_ordering_from_first_to_last(self):
        # Arrange & Act
        document = Document.objects.create(
            owner=self.user,
            title="Test doc",
        )

        document_file1 = DocumentFile.create_for_document(
            document=document,
            uploaded_file=self._upload_test_file(name="first.pdf"),
        )
        document_file2 = DocumentFile.create_for_document(
            document=document,
            uploaded_file=self._upload_test_file(name="last.pdf"),
        )

        # Assert
        document = Document.objects.with_files().get(id=document.id)
        files = list(document.files.all())

        self.assertEqual(files[0].id, document_file1.id)
        self.assertEqual(files[1].id, document_file2.id)

    def test_with_files_count_annotates_correctly(self):
        # Arrange & Act
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(name="file1.pdf"),
        )

        DocumentFile.create_for_document(
            document=document,
            uploaded_file=self._upload_test_file(name="file2.pdf"),
        )

        document = Document.objects.with_files_count().get(id=document.id)

        # Assert
        self.assertEqual(document.files_count, 2)

    def test_with_user_tags_prefetches_only_users_tags(self):
        # Arrange
        tag1_name = "finance"
        tag1 = Tag.objects.create(name=tag1_name)

        tag2_name = "private"
        tag2 = Tag.objects.create(name=tag2_name)

        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )

        DocumentTag.objects.create(
            document=document,
            tag=tag1,
            owner=self.user,
        )
        DocumentTag.objects.create(
            document=document,
            tag=tag2,
            owner=self.other_user,
        )

        # Act
        document = Document.objects.with_user_tags(self.user).get(id=document.id)

        tags = [document_tag.tag.name for document_tag in document.document_tags.all()]

        # Assert
        self.assertEqual(tags, [tag1_name])


class DocumentFileQuerySetTests(TemporaryMediaRootTestCase):
    def setUp(self):
        super().setUp()

        self.user = User.objects.create_user(
            username="user1",
            password="password",
        )

    def test_most_recent_returns_most_recent(self):
        # Arrange & Act
        document = Document.objects.create(
            owner=self.user,
            title="Test doc",
        )

        DocumentFile.create_for_document(
            document=document,
            uploaded_file=self._upload_test_file(name="first.pdf"),
        )
        last_document_file = DocumentFile.create_for_document(
            document=document,
            uploaded_file=self._upload_test_file(name="last.pdf"),
        )

        # Assert
        self.assertEqual(DocumentFile.objects.most_recent().id, last_document_file.id)

    def test_most_recent_empty(self):
        # Assert
        self.assertIsNone(DocumentFile.objects.most_recent())

    def test_most_recent_for_document_returns_most_recent(self):
        # Arrange & Act
        document = Document.objects.create(
            owner=self.user,
            title="Test doc",
        )

        DocumentFile.create_for_document(
            document=document,
            uploaded_file=self._upload_test_file(name="first.pdf"),
        )
        last_document_file = DocumentFile.create_for_document(
            document=document,
            uploaded_file=self._upload_test_file(name="last.pdf"),
        )

        # Assert
        self.assertEqual(
            DocumentFile.objects.most_recent_for_document(document=document).id,
            last_document_file.id,
        )

    def test_most_recent_for_document_empty(self):
        # Arrange & Act
        document = Document.objects.create(
            owner=self.user,
            title="Test doc",
        )

        # Assert
        self.assertIsNone(
            DocumentFile.objects.most_recent_for_document(document=document)
        )
