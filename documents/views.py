from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from documents.models import Document, DocumentFile, DocumentNote
from documents.serializers import (
    DocumentDetailSerializer,
    DocumentFileCreateSerializer,
    DocumentFileSerializer,
    DocumentListSerializer,
    DocumentMetadataSerializer,
    DocumentNoteCreateUpdateSerializer,
    DocumentNoteSerializer,
    DocumentUpdateSerializer,
    MultiFileDocumentCreateSerializer,
    SingleFileDocumentCreateSerializer,
)


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing documents.

    Supports:
    - list: list user documents
    - retrieve: retrieve a single document
    - create: upload a single-file document
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]

    def get_queryset(self):
        """Return the queryset of documents for the authenticated user,
        optimized with related files and tags.

        Returns:
            QuerySet: The optimized queryset of documents.
        """
        user = self.request.user

        queryset = Document.objects.for_user(user)

        if self.action == "list":
            return (
                queryset.with_files_count().with_user_tags(user).order_by("-created_at")
            )

        if self.action == "retrieve":
            return queryset.with_files().with_user_tags(user).order_by("-created_at")

        return queryset

    def get_serializer_class(self):
        """Return the appropriate serializer class based on the action.

        Returns:
            Serializer class: The serializer class to use.
        """

        if self.action == "create":
            return SingleFileDocumentCreateSerializer

        elif self.action == "upload_multiple":
            return MultiFileDocumentCreateSerializer

        if self.action == "retrieve":
            return DocumentDetailSerializer

        if self.action == "update" or self.action == "partial_update":
            return DocumentUpdateSerializer

        return DocumentListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()

        response_serializer = DocumentDetailSerializer(document)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="upload-multiple")
    def upload_multiple(self, request: HttpRequest):
        """Upload a new document with multiple files.

        Args:
            request (HttpRequest): The HTTP request object.

        Returns:
            Response: The HTTP response with the created document details.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = serializer.save()

        response_serializer = DocumentDetailSerializer(document)

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    # --- Document Files
    @action(detail=True, methods=["post"], url_path="files")
    def add_files(self, request: HttpRequest, pk: int = None):
        """Add a new file to an existing document.

        Args:
            request (HttpRequest): The HTTP request object.
            pk (int): The primary key of the document.

        Returns:
            Response: The HTTP response with the document file details.
        """
        document = self.get_object()

        serializer = DocumentFileCreateSerializer(
            data=request.data, context={"document": document}
        )
        serializer.is_valid(raise_exception=True)

        new_files = serializer.save()

        response_serializer = DocumentFileSerializer(new_files, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["delete"], url_path="files/(?P<file_id>[^/.]+)")
    def remove_file(self, request: HttpRequest, pk: int = None, file_id: int = None):
        """Delete a specific file from a document.

        The document must have at least one file remaining after deletion.

        Args:
            request (HttpRequest): The HTTP request object.
            pk (int): The primary key of the document.
            file_id (int): The primary key of the document file to delete.

        Returns:
            Response: The HTTP response indicating the result of the deletion.
        """
        document = self.get_object()

        document_file: DocumentFile = get_object_or_404(document.files, id=file_id)

        try:
            document.remove_file(document_file=document_file)
        except ValidationError as ex:
            raise serializers.ValidationError(str(ex))

        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- Notes
    @action(detail=True, methods=["get"], url_path="notes")
    def notes(self, request: HttpRequest, pk: int = None):
        """Retrieve notes associated with the document.

        Args:
            request (HttpRequest): The HTTP request object.
            pk (int): The primary key of the document.

        Returns:
            Response: The HTTP response with the list of document notes.
        """
        document = self.get_object()
        notes = document.notes.all().order_by("-created_at")

        response_serializer = DocumentNoteSerializer(notes, many=True)

        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @notes.mapping.post
    def create_note(self, request: HttpRequest, pk: int = None):
        """Add a new note to the document.

        Args:
            request (HttpRequest): The HTTP request object.
            pk (int): The primary key of the document.

        Returns:
            Response: The HTTP response with the created document note details.
        """
        document = self.get_object()

        serializer = DocumentNoteCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = document.add_note(
            author=request.user,
            content=serializer.validated_data["content"],
        )

        response_serializer = DocumentNoteSerializer(note)

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["patch"], url_path=r"notes/(?P<note_id>[^/.]+)")
    def note_detail(self, request, pk: int = None, note_id: int = None):
        document = self.get_object()

        note = get_object_or_404(document.notes, id=note_id)

        if note.author != request.user:
            raise PermissionDenied("You cannot edit this note.")

        serializer = DocumentNoteCreateUpdateSerializer(
            note, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(DocumentNoteSerializer(note).data)

    @note_detail.mapping.delete
    def delete_note(self, request, pk: int = None, note_id: int = None):
        document = self.get_object()

        try:
            note = document.notes.get(id=note_id)
        except DocumentNote.DoesNotExist:
            raise ValidationError({"note": "Note not found."})

        if note.author != request.user:
            raise PermissionDenied("You cannot detele this note.")

        note.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # --- Metadata
    @action(detail=True, methods=["get"], url_path="metadata")
    def metadata(self, request, pk: int = None):
        document = self.get_object()
        metadata = document.metadata.all().order_by("-created_at")

        response_serializer = DocumentMetadataSerializer(metadata, many=True)

        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @metadata.mapping.post
    def add_metadata(self, request, pk=None):
        document = self.get_object()

        serializer = DocumentMetadataSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        metadata = document.add_metadata(
            **serializer.validated_data,
        )

        return Response(
            DocumentMetadataSerializer(metadata).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True, methods=["patch"], url_path=r"metadata/(?P<metadata_id>[^/.]+)"
    )
    def metadata_detail(self, request, pk: int = None, metadata_id: int = None):
        document = self.get_object()

        metadata = get_object_or_404(document.metadata, id=metadata_id)

        serializer = DocumentMetadataSerializer(
            metadata, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(DocumentMetadataSerializer(metadata).data)

    @metadata_detail.mapping.delete
    def delete_metadata(self, request, pk: int = None, metadata_id: int = None):
        document = self.get_object()

        metadata = get_object_or_404(document.metadata, id=metadata_id)

        metadata.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

