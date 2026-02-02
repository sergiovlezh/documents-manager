"""Models for managing documents, files, metadata, notes, and tags.

These models form the core of the documents manager domain, providing
ownership, timestamps, and extensible metadata.
"""

from django.db import models
from django.contrib.auth import get_user_model

from config.models import TimeStampedModel

User = get_user_model()


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

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["owner", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.title

    def set_title_from_file(self, document_file: "DocumentFile") -> None:
        """Set the document title from the provided file if no title exists.

        Args:
            document_file (DocumentFile): The document file whose original filename
                will be used as the title.
        """
        if not self.title:
            self.title = document_file.original_filename
            self.save(update_fields=["title"])


class DocumentFile(TimeStampedModel):
    """Represents a file uploaded and associated with a document.

    Multiple files may belong to a single document, allowing multi-page
    documents, versioning, or alternate formats.
    """

    document = models.ForeignKey(
        Document, on_delete=models.CASCADE, related_name="files"
    )
    file = models.FileField(upload_to="documents/")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["document", "created_at"]),
        ]

    def __str__(self) -> str:
        return self.filename

    @property
    def original_filename(self) -> str:
        """Return the original filename without the storage path.

        Returns:
            str: The base filename of the uploaded file.
        """
        return self.file.name.rsplit("/", 1)[-1]


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
        unique_together = ("document", "key")
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
        unique_together = ("document", "tag", "owner")
        indexes = [
            models.Index(fields=["document", "tag"]),
        ]

    def __str__(self) -> str:
        return f"{self.document.title} - {self.tag.name}"
