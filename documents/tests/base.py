import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APITestCase


class _TempMediaManagerBase:
    def _setup_media(self):
        self._temp_media_dir = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self._temp_media_dir)
        self.override.enable()

        self.addCleanup(self.override.disable)
        self.addCleanup(
            shutil.rmtree,
            self._temp_media_dir,
            ignore_errors=True,
        )

    def _upload_test_file(
        self,
        *,
        name="example.pdf",
        content=b"dummy content",
        content_type="application/pdf",
    ):
        return SimpleUploadedFile(name, content, content_type)


class TemporaryMediaTestCase(_TempMediaManagerBase, TestCase):
    def setUp(self):
        super().setUp()

        self._setup_media()
