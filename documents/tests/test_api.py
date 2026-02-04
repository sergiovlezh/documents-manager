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
