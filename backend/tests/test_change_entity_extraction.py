import os
import tempfile
import unittest
from textwrap import dedent

from app.services.change_impact.adapter import ChangeImpactAdapter


class ChangeEntityExtractionTest(unittest.TestCase):
    def test_extract_changed_schema_and_data_object_facts(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = os.path.join(tmp_dir, "schemas.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        from pydantic import BaseModel


                        class CreateProjectRequest(BaseModel):
                            name: str


                        class Helper:
                            pass
                        """
                    ).strip()
                )

            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_diff_for_file = lambda relative_path, staged=False: (
                "@@ -1,5 +1,5 @@\n"
                " from pydantic import BaseModel\n"
                "\n"
                "\n"
                " class CreateProjectRequest(BaseModel):\n"
                "-    name: int\n"
                "+    name: str\n"
            )

            facts = adapter._extract_changed_python_facts("schemas.py", " M")

            self.assertEqual(facts["changed_schemas"], ["CreateProjectRequest"])
            self.assertEqual(facts["affected_data_objects"], ["CreateProjectRequest"])

    def test_generate_change_analysis_populates_job_and_data_object_fields(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.mkdir(os.path.join(tmp_dir, ".git"))
            schema_path = os.path.join(tmp_dir, "app", "schemas.py")
            worker_path = os.path.join(tmp_dir, "workers", "sync_worker.py")
            os.makedirs(os.path.dirname(schema_path), exist_ok=True)
            os.makedirs(os.path.dirname(worker_path), exist_ok=True)

            with open(schema_path, "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        from pydantic import BaseModel


                        class PublishResponse(BaseModel):
                            ok: bool
                        """
                    ).strip()
                )

            with open(worker_path, "w", encoding="utf-8") as f:
                f.write(
                    dedent(
                        """
                        def background_sync_job():
                            return True
                        """
                    ).strip()
                )

            adapter = ChangeImpactAdapter(workspace_path=tmp_dir)
            adapter._git_status_lines = lambda: [" M app/schemas.py", " M workers/sync_worker.py"]

            def fake_git_diff(relative_path, staged=False):
                if relative_path == "app/schemas.py":
                    return (
                        "@@ -1,4 +1,4 @@\n"
                        " from pydantic import BaseModel\n"
                        "\n"
                        "\n"
                        " class PublishResponse(BaseModel):\n"
                        "-    ok: int\n"
                        "+    ok: bool\n"
                    )
                return (
                    "@@ -1,2 +1,2 @@\n"
                    " def background_sync_job():\n"
                    "-    return False\n"
                    "+    return True\n"
                )

            adapter._git_diff_for_file = fake_git_diff
            result = adapter.generate_change_analysis("ws_entities")

        self.assertEqual(result["workspace_snapshot_id"], "ws_entities")
        self.assertEqual(result["changed_schemas"], ["PublishResponse"])
        self.assertEqual(result["changed_jobs"], ["background_sync_job"])
        self.assertEqual(result["affected_data_objects"], ["PublishResponse"])


if __name__ == "__main__":
    unittest.main()
