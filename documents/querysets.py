from django.db import models
from django.apps import apps


class DocumentQuerySet(models.QuerySet):
    def for_user(self, user):
        """Filter documents owned by the given user.

        Args:
            user: The user who owns the documents.

        Returns:
            QuerySet: QuerySet of documents owned by the user.
        """
        return self.filter(owner=user)

    def with_files(self):
        """Prefetch related files for each document to avoid N+1 queries.

        Returns:
            QuerySet: QuerySet with related document files prefetched.
        """
        DocumentFile = apps.get_model("documents", "DocumentFile")

        return self.prefetch_related(
            models.Prefetch(
                "files",
                queryset=DocumentFile.objects.order_by("created_at"),
            )
        )

    def with_files_count(self):
        """Annotate each document with the count of its related files.

        Returns:
            QuerySet: QuerySet annotated with files_count.
        """
        return self.annotate(files_count=models.Count("files"))

    def with_user_tags(self, user):
        """Prefetch document tags belonging to the given user, including
        the related Tag objects, to optimize tag access.

        Args:
            user: The user who owns the document tags.

        Returns:
            QuerySet: Documents with document_tags prefetched for the given user.
        """
        DocumentTag = apps.get_model("documents", "DocumentTag")

        return self.prefetch_related(
            models.Prefetch(
                "document_tags",
                queryset=DocumentTag.objects.filter(owner=user).select_related("tag"),
            )
        )


class DocumentFileQuerySet(models.QuerySet):
    def most_recent(self):
        """Return the most recently created document file.

        Returns:
            DocumentFile: The latest DocumentFile instance, or None if no files exist.
        """
        return self.order_by("-created_at").first()
