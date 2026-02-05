"""Models for managing documents, files, metadata, notes, and tags.

These models form the core of the documents manager domain, providing
ownership, timestamps, and extensible metadata.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.db import models, transaction

from config.models import TimeStampedModel
from documents.querysets import DocumentFileQuerySet, DocumentQuerySet

User = get_user_model()

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser as UserType


class Document(TimeStampedModel):
    """Represents a logical document owned by a user.

    A document can have multiple uploaded files, metadata entries,
    notes, and tags.

    The title may be automatically derived from
    the first uploaded file if not explicitly set.
    """

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    objects: DocumentQuerySet = DocumentQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    @classmethod
    def create_from_file(
        cls,
        *,
        owner: "UserType",
        uploaded_file: UploadedFile,
        title: str | None = None,
        description: str = "",
    ) -> "Document":
        """Create a `Document` and its first `DocumentFile` atomically.

        Args:
            owner (UserType): The owner of the document.
            uploaded_file (UploadedFile): Uploaded file instance.
            title (str | None): Optional explicit title.
            description (str): Optional description.

        Returns:
            Document: The created document instance.
        """
        title = title.strip() if title else None
        derived_title = title or DocumentFile.derive_title(uploaded_file)

        with transaction.atomic():
            document = cls.objects.create(
                owner=owner,
                title=derived_title,
                description=description,
            )

            DocumentFile.create_for_document(
                document=document,
                uploaded_file=uploaded_file,
            )

        return document


class DocumentFile(TimeStampedModel):
    """Represents a file uploaded and associated with a document.

    Multiple files may belong to a single document, allowing multi-page
    documents, versioning, or alternate formats.
    """

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="files"
    )
    file = models.FileField(upload_to="documents/")

    @property
    def original_filename(self) -> str:
        """Return the original filename without the storage path.

        Returns:
            str: The base filename of the uploaded file.
        """
        return self.extract_filename(self.file)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["document", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.original_filename

    def delete(self, *args, **kwargs):
        """Delete the DocumentFile instance and remove the associated file
        from storage."""
        storage = self.file.storage
        file_path = self.file.name

        super().delete(*args, **kwargs)

        if storage.exists(file_path):
            storage.delete(file_path)

    @staticmethod
    def extract_filename(file: File) -> str:
        """Return the base filename from a file.

        Args:
            file (File): A Django File or UploadedFile instance.

        Returns:
            str: The base filename of the file.
        """
        return Path(file.name).name

    @staticmethod
    def extract_extension(file: File) -> str:
        """Return the file extension from a file.

        Args:
            file (File): A Django File or UploadedFile instance.

        Returns:
            str: The file extension of the file.
        """
        return Path(file.name).suffix.lstrip(".")

    @classmethod
    def derive_title(cls, uploaded_file: UploadedFile) -> str:
        """Derive a document title from an uploaded file.

        Args:
            uploaded_file (UploadedFile): The uploaded file instance.

        Returns:
            str: The derived title.
        """
        return Path(cls.extract_filename(uploaded_file)).stem

    @classmethod
    def create_for_document(
        cls,
        *,
        document: Document,
        uploaded_file: UploadedFile,
    ) -> "DocumentFile":
        """Create a `DocumentFile` for a given `Document`.

        Args:
            document (Document): The document to associate the file with.
            file (UploadedFile): The uploaded file instance.

        Returns:
            DocumentFile: The created DocumentFile instance.
        """
        return cls.objects.create(
            document=document,
            file=uploaded_file,
        )


class DocumentMetadata(TimeStampedModel):
    """Stores arbitrary key-value metadata associated with a document.

    Each metadata key is unique per document.
    """

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="metadata"
    )
    key = models.CharField(max_length=255)
    value = models.CharField(max_length=255)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "key"], name="unique_metadata_per_doc"
            )
        ]
        indexes = [
            models.Index(fields=["key"]),
        ]

    def __str__(self) -> str:
        return f"{self.document.title[:7]}... - {self.key}: {self.value}"


class DocumentNote(TimeStampedModel):
    """Represents a note attached to a document."""

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="notes"
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="document_notes"
    )
    content = models.TextField()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["document", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"Note by {self.author} for {self.document.title[:7]}..."

    def clean(self):
        if not self.content.strip():
            raise ValidationError({"content": "Note content cannot be empty."})

        return super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Tag(TimeStampedModel):
    """Represents a reusable tag that can be applied to documents."""

    name = models.CharField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class DocumentTag(TimeStampedModel):
    """Associates a document with a tag for a specific owner.

    This allows different users to tag the same document independently and
    display the tags used by a specific user.
    """

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="document_tags"
    )
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="tag_documents")
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="document_tags"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "tag", "owner"], name="unique_document_tag_per_user"
            )
        ]
        indexes = [
            models.Index(fields=["document", "tag", "owner"]),
        ]

    def __str__(self) -> str:
        return f"{self.document.title} - {self.tag.name}"
