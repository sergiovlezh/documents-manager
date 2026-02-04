from pathlib import Path

from django.contrib.auth import get_user_model

from documents.models import Document, DocumentFile
from documents.tests.base import TemporaryMediaRootTestCase

User = get_user_model()


class DocumentModelTests(TemporaryMediaRootTestCase):
    def setUp(self):
        super().setUp()

        # Create a test user
        self.user = User.objects.create_user(
            username="testuser",
            password="password123",
        )

    def test_create_from_file_creates_document_and_file(self):
        # Arrange
        filename = "example.pdf"
        description = "Test document"

        # Act
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(name=filename),
            description=description,
        )

        # Assert
        self.assertEqual(document.owner, self.user)
        self.assertEqual(document.title, Path(filename).stem)
        self.assertEqual(document.description, description)
        self.assertEqual(document.files.count(), 1)

    def test_derive_title_from_uploaded_file(self):
        # Arrange
        filename = "my_file.name.pdf"

        # Act
        uploaded_file = self._upload_test_file(name=filename)
        title = DocumentFile.derive_title(uploaded_file)

        # Assert
        self.assertEqual(title, Path(filename).stem)

    def test_create_for_document_creates_file(self):
        # Arrange
        filename = "example.pdf"
        document = Document.objects.create(
            owner=self.user,
            title="Test doc",
        )

        # Act
        document_file = DocumentFile.create_for_document(
            document=document,
            uploaded_file=self._upload_test_file(),
        )

        # Assert
        self.assertEqual(document_file.document, document)
        self.assertTrue(document_file.file.name.endswith(Path(filename).suffix))

    def test_str_returns_title(self):
        # Arrange
        filename = "My document"

        # Act
        document = Document.objects.create(owner=self.user, title=filename)

        # Assert
        self.assertEqual(str(document), filename)


class DocumentFileModelTests(TemporaryMediaRootTestCase):
    def setUp(self):
        super().setUp()

        # Create a test user
        self.user = User.objects.create_user(
            username="testuser",
            password="password123",
        )

    def test_str_returns_original_filename(self):
        # Arrange
        filename = "test.txt"

        # Act
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(name=filename),
        )
        document_file = document.files.first()

        # Assert
        self.assertEqual(str(document_file), filename)

    def test_extract_extension_cases(self):
        cases = {
            "file.pdf": "pdf",
            "archive.tar.gz": "gz",
            "README": "",
            ".env": "",
            "IMAGE.PNG": "PNG",
        }

        for filename, expected in cases.items():
            with self.subTest(name=filename):
                document = Document.create_from_file(
                    owner=self.user,
                    uploaded_file=self._upload_test_file(name=filename),
                )
                document_file = document.files.first()

                self.assertEqual(
                    DocumentFile.extract_extension(document_file.file),
                    expected,
                )
