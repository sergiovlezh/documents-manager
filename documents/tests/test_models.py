import shutil
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from documents.models import Document, DocumentFile

User = get_user_model()


# @override_settings(MEDIA_ROOT=TEMP_MEDIA_DIR)
class DocumentModelTests(TestCase):
    def setUp(self):
        # Create a temporary directory for MEDIA_ROOT
        self._temp_media_dir = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self._temp_media_dir)
        self.override.enable()

        # Create a test user
        self.user = User.objects.create_user(
            username="testuser",
            password="password123",
        )

    def tearDown(self):
        self.override.disable()

        # Remove the temporary directory after tests
        shutil.rmtree(self._temp_media_dir, ignore_errors=True)

    def _upload_test_file(self, name: str = "example.pdf"):
        return SimpleUploadedFile(
            name=name,
            content=b"dummy content",
            content_type="application/pdf",
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
