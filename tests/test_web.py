"""Проверка точки входа frontend без проверки backend-логики."""

import unittest

from fastapi.testclient import TestClient

from app.main import app


class WebTests(unittest.TestCase):
    def test_assistant_start_page_is_served(self) -> None:
        with TestClient(app) as client:
            response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Здравствуйте! Чем помочь?", response.text)
        self.assertIn("Введите команду", response.text)
        self.assertIn("Начать голосовой ввод", response.text)
        self.assertIn('id="voice-response-toggle"', response.text)
        self.assertIn("Озвучка: включена", response.text)
        self.assertIn("Голосовой ввод работает в тестовом режиме", response.text)
        self.assertIn('id="help-dialog"', response.text)
        self.assertIn("Доступные команды", response.text)
        self.assertIn("Найди &lt;запрос&gt;", response.text)
        self.assertIn("Сайты открываются только из настроенного белого списка", response.text)
        self.assertIn("Открой РМРС", response.text)

    def test_frontend_loads_and_handles_assistant_commands_from_api(self) -> None:
        with TestClient(app) as client:
            response = client.get("/static/app.js")

        self.assertEqual(response.status_code, 200)
        self.assertIn('fetch("/api/assistant/commands")', response.text)
        self.assertIn("getCommandAlias", response.text)
        self.assertIn('commandAlias?.action_code === "create_document"', response.text)
        self.assertIn('commandAlias?.action_code === "open_mail"', response.text)
        self.assertIn('commandAlias?.action_code === "open_site"', response.text)
        self.assertIn('alias.action_code === "web_search"', response.text)
        self.assertIn("getSecureWebsiteUrl", response.text)
        self.assertIn("encodeURIComponent(query)", response.text)
        self.assertIn("window.open(targetUrl", response.text)
        self.assertNotIn("https://e.mail.ru/", response.text)
        self.assertNotIn("https://yandex.ru/", response.text)
        self.assertNotIn("https://rs-class.org/", response.text)
        self.assertIn("openHelp", response.text)


if __name__ == "__main__":
    unittest.main()
