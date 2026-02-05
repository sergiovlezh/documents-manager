from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status

from documents.models import Document
from documents.tests.base import TemporaryMediaAPITestCase

User = get_user_model()


class DocumentAPITestCase(TemporaryMediaAPITestCase):
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

        self.client.force_authenticate(user=self.user)

        self.list_url = reverse("document-list")

    def test_create_document_with_single_file(self):
        # Arrange
        payload = {
            "file": self._upload_test_file(name="test.pdf"),
            "description": "My first document",
        }

        # Act
        response = self.client.post(self.list_url, payload, format="multipart")

        document_id = response.data["id"]

        # Assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        document = Document.objects.get(id=document_id)
        self.assertEqual(document.owner, self.user)
        self.assertEqual(document.title, "test")
        self.assertEqual(document.description, "My first document")
        self.assertEqual(document.files.count(), 1)

    def test_create_document_with_multiple_files(self):
        # Arrange
        payload = {
            "files": [
                self._upload_test_file(name="file1.pdf"),
                self._upload_test_file(name="file2.pdf"),
            ],
            "description": "Document with multiple files",
        }

        url = reverse("document-upload-multiple")

        # Act
        response = self.client.post(url, payload, format="multipart")

        document_id = response.data["id"]

        # Assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        document = Document.objects.get(id=document_id)
        self.assertEqual(document.owner, self.user)
        self.assertEqual(document.title, "file1")
        self.assertEqual(document.description, "Document with multiple files")
        self.assertEqual(document.files.count(), 2)

    def test_list_documents_only_returns_user_documents(self):
        # Arrange
        Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(name="user.pdf"),
        )
        Document.create_from_file(
            owner=self.other_user,
            uploaded_file=self._upload_test_file(name="other.pdf"),
        )

        # Act
        response = self.client.get(self.list_url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["title"], "user")

    def test_retrieve_document_detail(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )
        url = reverse("document-detail", args=[document.id])

        # Act
        response = self.client.get(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], document.id)
        self.assertEqual(len(response.data["files"]), 1)

    def test_user_cannot_access_other_users_document(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.other_user,
            uploaded_file=self._upload_test_file(),
        )
        url = reverse("document-detail", args=[document.id])

        # Act
        response = self.client.get(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_update_document_title_and_description(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(name="original.pdf"),
            description="Original description",
        )

        url = reverse("document-detail", args=[document.id])

        payload = {
            "title": "Updated title",
            "description": "Updated description",
        }

        # Act
        response = self.client.patch(url, payload, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        document.refresh_from_db()
        self.assertEqual(document.title, "Updated title")
        self.assertEqual(document.description, "Updated description")
        self.assertEqual(document.files.count(), 1)

    def test_user_cannot_update_other_users_document(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.other_user,
            uploaded_file=self._upload_test_file(),
        )
        url = reverse("document-detail", args=[document.id])

        payload = {"title": "Hacked title"}

        # Act
        response = self.client.patch(url, payload, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_delete_document(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )
        url = reverse("document-detail", args=[document.id])

        # Act
        response = self.client.delete(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Document.objects.filter(id=document.id).exists())

    def test_document_file_includes_download_url(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(name="preview.pdf"),
        )
        url = reverse("document-detail", args=[document.id])

        # Act
        response = self.client.get(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        file_data = response.data["files"][0]
        self.assertIn("url", file_data)
        self.assertTrue(file_data["url"].endswith(".pdf"))

    def test_partial_update_does_not_allow_file_changes(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )
        url = reverse("document-detail", args=[document.id])

        payload = {
            "file": self._upload_test_file(name="new.pdf"),
        }

        # Act
        response = self.client.patch(url, payload, format="multipart")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_full_update_is_not_allowed(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(name="original.pdf"),
        )
        url = reverse("document-detail", args=[document.id])

        payload = {
            "file": self._upload_test_file(name="new.pdf"),
            "title": "Updated title",
        }

        # Act
        response = self.client.put(url, payload, format="multipart")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_user_can_add_single_file_to_document(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(name="first.pdf"),
        )
        url = reverse("document-add-files", args=[document.id])

        payload = {
            "files": [self._upload_test_file(name="second.pdf")],
        }

        # Act
        response = self.client.post(url, payload, format="multipart")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document.refresh_from_db()
        self.assertEqual(document.files.count(), 2)

    def test_user_can_add_multiple_files_to_document(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(name="first.pdf"),
        )
        url = reverse("document-add-files", args=[document.id])

        payload = {
            "files": [
                self._upload_test_file(name="second.pdf"),
                self._upload_test_file(name="third.pdf"),
            ],
        }

        # Act
        response = self.client.post(url, payload, format="multipart")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        document.refresh_from_db()
        self.assertEqual(document.files.count(), 3)

    def test_user_cannot_add_file_to_other_users_document(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.other_user,
            uploaded_file=self._upload_test_file(),
        )
        url = reverse("document-add-files", args=[document.id])

        payload = {
            "files": [self._upload_test_file(name="intruder.pdf")],
        }

        # Act
        response = self.client.post(url, payload, format="multipart")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_delete_file_from_multi_file_document(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(name="first.pdf"),
        )
        second_file = document.add_file(
            uploaded_file=self._upload_test_file(name="second.pdf"),
        )

        url = reverse(
            "document-remove-file",
            args=[document.id, second_file.id],
        )

        # Act
        response = self.client.delete(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        document.refresh_from_db()
        self.assertEqual(document.files.count(), 1)

    def test_cannot_delete_last_file_from_document(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )
        document_file = document.files.first()

        url = reverse(
            "document-remove-file",
            args=[document.id, document_file.id],
        )

        # Act
        response = self.client.delete(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(document.files.count(), 1)

    def test_user_can_list_notes_from_document(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )
        document.add_note(
            author=self.user,
            content="My first note",
        )

        url = reverse("document-notes", args=[document.id])

        # Act
        response = self.client.get(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["content"], "My first note")

    def test_user_cannot_access_other_users_notes(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.other_user,
            uploaded_file=self._upload_test_file(),
        )
        document.add_note(
            author=self.other_user,
            content="Other user's note",
        )

        url = reverse("document-notes", args=[document.id])

        # Act
        response = self.client.get(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_add_note_to_document(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )
        url = reverse("document-notes", args=[document.id])

        payload = {
            "content": "My first note",
        }

        # Act
        response = self.client.post(url, payload, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(document.notes.count(), 1)

    def test_user_can_update_own_note(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )
        note = document.add_note(
            author=self.user,
            content="Old content",
        )

        url = reverse(
            "document-note-detail",
            args=[document.id, note.id],
        )

        payload = {
            "content": "Updated content",
        }

        # Act
        response = self.client.patch(url, payload, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note.refresh_from_db()
        self.assertEqual(note.content, "Updated content")

    def test_user_cannot_update_other_users_note(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )
        note = document.add_note(
            author=self.other_user,
            content="Other user's note",
        )

        url = reverse(
            "document-note-detail",
            args=[document.id, note.id],
        )

        payload = {
            "content": "Hacked content",
        }

        # Act
        response = self.client.patch(url, payload, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        note.refresh_from_db()
        self.assertEqual(note.content, "Other user's note")

    def test_user_can_delete_own_note(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )

        note = document.add_note(
            author=self.user,
            content="Temp note",
        )

        url = reverse(
            "document-note-detail",
            args=[document.id, note.id],
        )

        # Act
        response = self.client.delete(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(document.notes.count(), 0)

    def test_user_cannot_delete_other_users_note(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )

        note = document.add_note(
            author=self.other_user,
            content="Other user's note",
        )

        url = reverse(
            "document-note-detail",
            args=[document.id, note.id],
        )

        # Act
        response = self.client.delete(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(document.notes.count(), 1)

    def test_user_can_list_metadata_from_document(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )
        document.add_metadata(
            key="category",
            value="reports",
        )

        url = reverse("document-metadata", args=[document.id])

        # Act
        response = self.client.get(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["key"], "category")

    def test_user_cannot_access_other_users_metadata(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.other_user,
            uploaded_file=self._upload_test_file(),
        )
        document.add_metadata(
            key="category",
            value="reports",
        )

        url = reverse("document-metadata", args=[document.id])

        # Act
        response = self.client.get(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_add_metadata_to_document(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )
        url = reverse("document-metadata", args=[document.id])

        payload = {
            "key": "category",
            "value": "reports",
        }

        # Act
        response = self.client.post(url, payload, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(document.metadata.count(), 1)

    def test_user_can_update_document_metadata(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )

        metadata = document.add_metadata(
            key="category",
            value="invoices",
        )

        url = reverse(
            "document-metadata-detail",
            args=[document.id, metadata.id],
        )

        payload = {
            "value": "receipts",
        }

        # Act
        response = self.client.patch(url, payload, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        metadata.refresh_from_db()
        self.assertEqual(metadata.value, "receipts")

    def test_user_can_delete_document_metadata(self):
        # Arrange
        document = Document.create_from_file(
            owner=self.user,
            uploaded_file=self._upload_test_file(),
        )

        metadata = document.add_metadata(
            key="category",
            value="misc",
        )

        url = reverse(
            "document-metadata-detail",
            args=[document.id, metadata.id],
        )

        # Act
        response = self.client.delete(url)

        # Assert
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(document.metadata.count(), 0)

    def test_user_can_merge_documents_into_main_document(self):
        # Arrange
        main_document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file(name="main.pdf")
        )
        main_document.add_note(
            author=self.user,
            content="Main note",
        )
        main_document.add_tag_for_user(
            name="main",
            owner=self.user,
        )
        main_document.add_metadata(
            key="main-key",
            value="main-value",
        )

        source_document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file(name="source.pdf")
        )
        source_document.add_note(
            author=self.user,
            content="Source note",
        )
        source_document.add_tag_for_user(
            name="source",
            owner=self.user,
        )
        source_document.add_metadata(
            key="source-key",
            value="source-value",
        )

        url = reverse("document-merge", args=[main_document.id])
        payload = {"source_document_ids": [source_document.id]}

        # Act
        response = self.client.post(url, payload, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Document.objects.filter(id=source_document.id).exists())
        self.assertEqual(main_document.files.count(), 2)
        self.assertEqual(main_document.notes.count(), 2)
        self.assertEqual(main_document.document_tags.count(), 2)
        self.assertEqual(main_document.metadata.count(), 2)

    def test_merge_fails_if_source_belongs_to_other_user(self):
        # Arrange
        user_document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file()
        )

        other_user_document = Document.create_from_file(
            owner=self.other_user, uploaded_file=self._upload_test_file()
        )

        url = reverse("document-merge", args=[user_document.id])
        payload = {"source_document_ids": [other_user_document.id]}

        # Act
        response = self.client.post(url, payload, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_merge_fails_if_target_is_not_owned(self):
        # Arrange
        user_document = Document.create_from_file(
            owner=self.user, uploaded_file=self._upload_test_file()
        )

        other_user_document = Document.create_from_file(
            owner=self.other_user, uploaded_file=self._upload_test_file()
        )

        url = reverse("document-merge", args=[other_user_document.id])
        payload = {"source_document_ids": [user_document.id]}

        # Act
        response = self.client.post(url, payload, format="json")

        # Assert
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
