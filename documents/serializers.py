from django.http import HttpRequest
from rest_framework import serializers

from documents.models import (
    Document,
    DocumentFile,
    DocumentMetadata,
    DocumentNote,
    DocumentTag,
    Tag,
)


def get_tags_from_document(document: Document) -> list[dict]:
    """Helper function to extract tags from a document's prefetched `document_tags`.

    Assumes `document_tags` was prefetched via `with_user_tags()`.

    Args:
        document (Document): The document instance.

    Returns:
        list: A list of serialized tags associated with the document.
    """
    document_tags = getattr(document, "document_tags", None)
    if document_tags is None:
        return []
    return DocumentTagDetailSerializer(document_tags.all(), many=True).data


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


class DocumentTagDetailSerializer(serializers.ModelSerializer):
    """Serializer to show the tag name and its user-specific color."""

    name = serializers.CharField(source="tag.name", read_only=True)

    class Meta:
        model = DocumentTag
        fields = ["id", "name", "color"]


class DocumentTagCreateUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=50)
    color = serializers.CharField(max_length=7, required=False)

    def validate_name(self, value: str) -> str:
        return value.strip()

    def save(self, **kwargs):
        document: Document = self.context["document"]
        request: HttpRequest = self.context["request"]
        user = request.user

        return document.add_tag_for_user(
            name=self.validated_data["name"],
            owner=user,
            color=self.validated_data.get("color"),
        )


class SingleFileDocumentCreateSerializer(serializers.Serializer):
    """Serializer for creating a Document with a single uploaded file."""

    file = serializers.FileField(write_only=True)
    description = serializers.CharField(required=False, allow_blank=True)

    def validate_file(self, value):
        if not value:
            raise serializers.ValidationError("No file was uploaded.")

        if not value.size:
            raise serializers.ValidationError("The uploaded file is empty.")

        return value

    def create(self, validated_data):
        request: HttpRequest = self.context["request"]
        user = request.user

        uploaded_file = validated_data.pop("file")
        description = validated_data.get("description", "").strip()

        return Document.create_from_file(
            owner=user,
            uploaded_file=uploaded_file,
            description=description,
        )


class MultiFileDocumentCreateSerializer(serializers.Serializer):
    """Serializer for creating a Document with multiple uploaded files."""

    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        min_length=1,
    )
    description = serializers.CharField(required=False, allow_blank=True)

    def validate_files(self, value):
        if not value:
            raise serializers.ValidationError("No files were uploaded.")

        for uploaded_file in value:
            if not uploaded_file.size:
                raise serializers.ValidationError(
                    f"The uploaded file '{uploaded_file.name}' is empty."
                )

        return value

    def create(self, validated_data):
        request: HttpRequest = self.context["request"]
        user = request.user

        uploaded_files = validated_data.pop("files")
        description = validated_data.get("description", "").strip()

        return Document.create_from_multiple_files(
            owner=user,
            uploaded_files=uploaded_files,
            description=description,
        )


class DocumentFileSerializer(serializers.ModelSerializer):
    """Read-only serializer for document files."""

    original_filename = serializers.CharField(read_only=True)
    extension = serializers.SerializerMethodField()
    url = serializers.FileField(source="file", read_only=True)

    def get_extension(self, obj: DocumentFile) -> str:
        return obj.extract_extension(obj.file)

    class Meta:
        model = DocumentFile
        fields = [
            "id",
            "original_filename",
            "extension",
            "url",
            "created_at",
        ]
        read_only_fields = fields


class DocumentListSerializer(serializers.ModelSerializer):
    """Serializer for listing documents."""

    files_count = serializers.IntegerField(read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "title",
            "description",
            "files_count",
            "tags",
            "created_at",
        )

    def get_tags(self, obj: Document):
        return get_tags_from_document(obj)


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Serializer for retrieving a single document."""

    files = DocumentFileSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "id",
            "title",
            "description",
            "files",
            "tags",
            "created_at",
        )

    def get_tags(self, obj: Document):
        return get_tags_from_document(obj)


class DocumentUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating document details."""

    class Meta:
        model = Document
        fields = ("title", "description")

    def validate(self, attrs):
        forbidden = {"file", "files"}
        if forbidden & set(self.initial_data.keys()):
            raise serializers.ValidationError(
                "Files cannot be modified via this endpoint."
            )
        return attrs


class DocumentFileCreateSerializer(serializers.Serializer):
    """Serializer to upload one or multiple files to an existing document."""

    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        min_length=1,
    )

    def validate_files(self, value):
        if not value:
            raise serializers.ValidationError("No files were uploaded.")

        for uploaded_file in value:
            if not uploaded_file.size:
                raise serializers.ValidationError(
                    f"The uploaded file '{uploaded_file.name}' is empty."
                )

        return value

    def create(self, validated_data):
        document: Document = self.context["document"]
        uploaded_files = validated_data.pop("files")

        return document.add_files(uploaded_files=uploaded_files)


class DocumentNoteSerializer(serializers.ModelSerializer):
    """Serializer to read document notes."""

    author = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = DocumentNote
        fields = ["id", "author", "content", "created_at"]
        read_only_fields = ["id", "author", "created_at"]


class DocumentNoteCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer to create or update document notes."""

    class Meta:
        model = DocumentNote
        fields = ["content"]


class DocumentMetadataSerializer(serializers.ModelSerializer):
    """Serializer for document metadata."""

    class Meta:
        model = DocumentMetadata
        fields = ["id", "key", "value", "created_at"]
        read_only_fields = ["id", "created_at"]


class DocumentMetadataCreateUpdateSerializer(serializers.Serializer):
    """Serializer to add or update a metadata entry for a document."""

    key = serializers.CharField(max_length=255)
    value = serializers.CharField(max_length=255)

    def save(self, **kwargs) -> DocumentMetadata:
        document: Document = self.context["document"]

        # Delegamos en tu método de modelo: document.add_metadata(key, value)
        return document.add_metadata(
            key=self.validated_data["key"], value=self.validated_data["value"]
        )


class MergeDocumentsSerializer(serializers.Serializer):
    """Serializer to merge multiple documents into the current one."""

    source_document_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        min_length=1,
    )

    def validate_source_document_ids(self, value):
        main_doc_id = self.context["view"].get_object().id
        request: HttpRequest = self.context["request"]
        user = request.user

        if main_doc_id in value:
            raise serializers.ValidationError("Cannot merge a document with itself.")

        sources = Document.objects.filter(id__in=value, owner=user)

        if sources.count() != len(value):
            raise serializers.ValidationError(
                "One or more document IDs are invalid or don't belong to you."
            )

        return sources

    def save(self):
        main_document: Document = self.context["view"].get_object()
        source_documents: list[Document] = self.validated_data["source_document_ids"]

        main_document.merge_documents(source_documents)

        return main_document
