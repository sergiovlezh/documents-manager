"""Models for managing documents, files, metadata, notes, and tags.

These models form the core of the documents manager domain, providing
ownership, timestamps, and extensible metadata.
"""

from pathlib import Path
from random import randint
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.db import models, transaction

from config.models import TimeStampedModel
from documents.querysets import DocumentQuerySet

User = get_user_model()

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser as UserType


def get_random_color() -> str:
    """Generate a random hex color code.

    Returns:
        str: A random hex color code in the format #RRGGBB.
    """

    return "#{:06x}".format(randint(0, 0xFFFFFF))


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

    @staticmethod
    def get_clean_title(
        uploaded_file: UploadedFile,
        title: str | None = None,
    ) -> str:
        """Determine the document title based on the provided title

        Args:
            uploaded_file (UploadedFile): The uploaded file instance.
            title (str | None): An optional explicit title.

        Returns:
            str: The final document title.
        """
        passed_title = title.strip() if title else None
        return passed_title or DocumentFile.derive_title(uploaded_file)

    def add_file(
        self,
        *,
        uploaded_file: UploadedFile,
    ) -> "DocumentFile":
        """Add a new file to the document.

        Args:
            uploaded_file (UploadedFile): The uploaded file instance.

        Returns:
            DocumentFile: The created DocumentFile instance.
        """
        return DocumentFile.create_for_document(
            document=self,
            uploaded_file=uploaded_file,
        )

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

        with transaction.atomic():
            document: "Document" = cls.objects.create(
                owner=owner,
                title=cls.get_clean_title(title=title, uploaded_file=uploaded_file),
                description=description,
            )

            document.add_file(
                uploaded_file=uploaded_file,
            )

        return document

    def add_files(
        self,
        *,
        uploaded_files: list[UploadedFile],
    ) -> list["DocumentFile"]:
        """Add multiple files to the document.

        Args:
            uploaded_files (list[UploadedFile]): List of uploaded file instances.

        Returns:
            list[DocumentFile]: List of created DocumentFile instances.
        """
        new_files = [
            DocumentFile(
                document=self,
                file=uploaded_file,
            )
            for uploaded_file in uploaded_files
        ]

        return DocumentFile.objects.bulk_create(new_files)

    @classmethod
    def create_from_multiple_files(
        cls,
        *,
        owner: "UserType",
        uploaded_files: list[UploadedFile],
        title: str | None = None,
        description: str = "",
    ) -> "Document":
        """Create a `Document` and multiple `DocumentFile` instances atomically.

        Args:
            owner (UserType): The owner of the document.
            uploaded_files (list[UploadedFile]): List of uploaded file instances.
            title (str | None): Optional explicit title.
            description (str): Optional description.

        Returns:
            Document: The created document instance.
        """
        if not uploaded_files:
            raise ValidationError("At least one uploaded file is required.")

        with transaction.atomic():
            document: "Document" = cls.objects.create(
                owner=owner,
                title=cls.get_clean_title(title=title, uploaded_file=uploaded_files[0]),
                description=description,
            )

            document.add_files(uploaded_files=uploaded_files)

        return document

    def remove_file(self, document_file: "DocumentFile"):
        """Remove a file from the document.

        Args:
            document_file (DocumentFile): The document file to remove.
        """
        if document_file.document != self:
            raise ValueError("The specified file does not belong to this document.")

        with transaction.atomic():
            all_files = DocumentFile.objects.select_for_update().filter(document=self)

            if all_files.count() <= 1:
                raise ValidationError("A document must have at least one file.")

            document_file.delete()

    def add_note(
        self,
        *,
        author: "UserType",
        content: str,
    ) -> "DocumentNote":
        """Add a note to the document.

        Args:
            author (AbstractUser): The author of the note.
            content (str): The content of the note.

        Returns:
            DocumentNote: The created document note instance.
        """
        return DocumentNote.objects.create(
            document=self,
            author=author,
            content=content,
        )

    def remove_note(self, note_id: int):
        """Remove a note from the document.

        Args:
            note_id (int): The document note id to remove.
        """
        self.notes.filter(id=note_id).delete()

    def add_metadata(self, key: str, value: str) -> "DocumentMetadata":
        """Add or update a metadata entry for the document.

        Args:
            key (str): The metadata key.
            value (str): The metadata value.

        Returns:
            DocumentMetadata: The created or updated metadata instance.
        """
        metadata, _ = DocumentMetadata.objects.update_or_create(
            document=self,
            key=key,
            defaults={"value": value},
        )
        return metadata

    def remove_metadata(self, key: str):
        """Remove a metadata entry from the document.

        Args:
            key (str): The metadata key to remove.
        """
        self.metadata.filter(key=key).delete()

    def add_tag_for_user(
        self, name: str, owner: "UserType", color: str | None = None
    ) -> "DocumentTag":
        """Add a tag to the document for a specific user.

        Args:
            tag_name (str): The tag to add.
            owner (AbstractUser): The owner of the tag.
            color (str): The color associated with the tag.

        Returns:
            DocumentTag: The created document tag instance.
        """

        with transaction.atomic():
            tag, _ = Tag.objects.get_or_create(name=name)

            defaults = {}
            if color:
                defaults["color"] = color

            document_tag, _ = DocumentTag.objects.get_or_create(
                document=self,
                tag=tag,
                owner=owner,
                defaults=defaults,
            )
        return document_tag

    def remove_tag_for_user(self, name: str, owner: "UserType"):
        """Remove a tag from the document for a specific user.

        Args:
            tag_name (str): The tag to remove.
            owner (AbstractUser): The owner of the tag.
        """
        tag_name = name.strip()

        with transaction.atomic():
            try:
                tag = Tag.objects.get(name=tag_name)
            except Tag.DoesNotExist:
                return

            DocumentTag.objects.filter(document=self, tag=tag, owner=owner).delete()

            if not tag.tag_documents.exists():
                tag.delete()

    def merge_documents(self, source_documents: list["Document"]):
        """Merge multiple documents into the current one (the main document).

        Files, notes, metadata, and tags from the source documents are reassigned to this
        document, and the source documents are then deleted.

        Args:
            source_documents (list[Document]): The documents to merge into this one.
        """
        sources = [document for document in source_documents if document.id != self.id]
        if not sources:
            return

        with transaction.atomic():
            for source in sources:
                source.files.update(document=self)
                source.notes.update(document=self)

                for document_tag in source.document_tags.all():
                    self.add_tag_for_user(
                        name=document_tag.tag.name,
                        owner=document_tag.owner,
                        color=document_tag.color,
                    )

                for metadata in source.metadata.all():
                    self.add_metadata(key=metadata.key, value=metadata.value)

                source.delete()


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

    def save(self, *args, **kwargs):
        self.name = self.name.strip()
        return super().save(*args, **kwargs)


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
    color = models.CharField(max_length=7, default=get_random_color)

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
