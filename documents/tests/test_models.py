from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from documents.models import Document, DocumentFile
from documents.tests.base import TemporaryMediaTestCase

User = get_user_model()


class DocumentModelTests(TemporaryMediaTestCase):
    def setUp(self):
        super().setUp()

        # Create a test user
        self.user = User.objects.create_user(
            username="testuser",
            password="password123",
        )

    def test_str_returns_title(self):
        # Arrange
        filename = "My document"

        # Act
        document = Document.objects.create(owner=self.user, title=filename)

        # Assert
        self.assertEqual(str(document), filename)

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

    def test_create_from_multiple_files_creates_document_and_files(self):
        # Arrange
        filenames = ["file1.pdf", "file2.pdf"]

        # Act
        document = Document.create_from_multiple_files(
            owner=self.user,
            uploaded_files=[self._upload_test_file(name=name) for name in filenames],
        )

        # Assert
        self.assertEqual(document.owner, self.user)
        self.assertEqual(document.title, Path(filenames[0]).stem)
        self.assertEqual(document.files.count(), len(filenames))

    def test_remove_file_deletes_document_file(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file()
        )
        document_file = document.files.first()

        # Act & Assert
        with self.assertRaises(ValidationError):
            document.remove_file(document_file=document_file)

    def test_remove_file_multifile_document_deletes_document_file(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file()
        )
        document.add_file(
            uploaded_file=self._upload_test_file(name="second.pdf"),
        )

        document_to_delete = document.files.first()

        # Act
        document.remove_file(document_file=document_to_delete)

        # Assert
        self.assertFalse(document.files.filter(id=document_to_delete.id).exists())

    def test_add_note_creates_document_note(self):
        # Arrange
        content = "This is a test note."

        document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file()
        )

        # Act
        note = document.add_note(content=content, author=self.user)

        # Assert
        self.assertEqual(note.document, document)
        self.assertEqual(note.author, self.user)
        self.assertEqual(note.content, content)
        self.assertEqual(document.notes.count(), 1)

    def test_remove_note_deletes_document_note(self):
        # Arrange
        content = "This is a test note."

        document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file()
        )
        note = document.add_note(content=content, author=self.user)

        # Act
        document.remove_note(note_id=note.id)

        # Assert
        self.assertFalse(document.notes.filter(id=note.id).exists())

    def test_add_metadata(self):
        # Arrange
        key = "category"
        value = "report"

        document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file()
        )

        # Act
        document.add_metadata(key=key, value=value)

        # Assert
        self.assertEqual(document.metadata.count(), 1)

    def test_add_metadata_is_idempotent(self):
        # Arrange
        key = "category"
        value = "report"

        document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file()
        )

        # Act
        metadata1 = document.add_metadata(key=key, value=value)
        metadata2 = document.add_metadata(key=key, value=value)

        # Assert
        self.assertEqual(metadata1.id, metadata2.id)
        self.assertEqual(document.metadata.count(), 1)

    def test_remove_metadata(self):
        # Arrange
        key = "category"
        value = "report"

        document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file()
        )
        metadata = document.add_metadata(key=key, value=value)

        # Act
        document.remove_metadata(key=key)

        # Assert
        self.assertFalse(document.metadata.filter(id=metadata.id).exists())

    def test_add_tag_for_user(self):
        # Arrange
        tag_name = "important"

        document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file()
        )

        # Act
        document.add_tag_for_user(name=tag_name, owner=self.user)

        # Assert
        self.assertEqual(document.document_tags.count(), 1)
        self.assertEqual(document.document_tags.first().tag.name, tag_name)

    def test_remove_tag_for_user_deletes_canonical_tag(self):
        # Arrange
        tag_name = "important"

        document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file()
        )
        document.add_tag_for_user(name=tag_name, owner=self.user)

        # Act
        document.remove_tag_for_user(name=tag_name, owner=self.user)

        # Assert
        self.assertEqual(document.document_tags.count(), 0)
        self.assertFalse(
            Document.objects.filter(document_tags__tag__name=tag_name).exists()
        )

    def test_merge_documents_combines_files_notes_metadata_tags_and_deletes_source(
        self,
    ):
        # Arrange
        main_document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file(name="main.pdf")
        )
        main_document.add_note(content="Main note", author=self.user)
        main_document.add_metadata(key="type", value="main")
        main_document.add_tag_for_user(name="main-tag", owner=self.user)

        source_document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file(name="source.pdf")
        )
        source_document.add_note(content="Source note", author=self.user)
        source_document.add_metadata(key="type", value="source")
        source_document.add_tag_for_user(name="source-tag", owner=self.user)

        # Act
        main_document.merge_documents(source_documents=[source_document])

        # Assert
        self.assertEqual(main_document.files.count(), 2)
        self.assertEqual(main_document.notes.count(), 2)
        self.assertTrue(
            main_document.document_tags.filter(tag__name="source-tag").exists()
        )
        self.assertFalse(Document.objects.filter(id=source_document.id).exists())


class DocumentFileModelTests(TemporaryMediaTestCase):
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

    def test_delete_removes_file_from_storage(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )
        document_file = document.files.first()
        file_path = Path(document_file.file.path)

        self.assertTrue(file_path.exists())

        document.add_file(uploaded_file=self._upload_test_file())

        # Act
        document_file.delete()

        # Assert
        self.assertFalse(file_path.exists())
