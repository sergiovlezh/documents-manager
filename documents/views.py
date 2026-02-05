from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from documents.models import Document
from documents.serializers import (
    DocumentDetailSerializer,
    DocumentListSerializer,
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
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
