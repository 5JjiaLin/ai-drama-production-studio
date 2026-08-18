import os
import unittest

os.environ["DEEPSEEK_API_KEY"] = "test-only-sentinel"

from app import app


class AppSmokeTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_health(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["status"], "healthy")

    def test_config_reports_presence_without_returning_secret(self):
        response = self.client.get("/api/config/check")
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["data"]["deepseek_api_key"], "已配置")
        self.assertNotIn("test-only-sentinel", response.get_data(as_text=True))

    def test_projects_require_authentication(self):
        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
