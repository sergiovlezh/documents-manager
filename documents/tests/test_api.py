from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from documents.models import Document, DocumentFile
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
