from django.http import HttpRequest
from rest_framework import serializers

from documents.models import Document, DocumentFile, Tag


def get_tags_from_document(document: Document) -> list[dict]:
    """Helper function to extract tags from a document's prefetched `document_tags`.

    Assumes `document_tags` was prefetched via `with_user_tags()`.

    Args:
        document (Document): The document instance.

    Returns:
        list: A list of serialized tags associated with the document.
    """
    document_tags = getattr(document, "document_tags", [])

    return [
        TagSerializer(document_tag.tag).data for document_tag in document_tags.all()
    ]


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name"]


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
