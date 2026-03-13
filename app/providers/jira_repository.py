import requests
from requests.auth import HTTPBasicAuth

from app.infrastructure.config import (
    JIRA_URL,
    JIRA_LOGIN,
    JIRA_PASSWORD,
)


class JiraRepository:

    def __init__(self):
        self.base_url = JIRA_URL.rstrip('/')
        self.auth = HTTPBasicAuth(JIRA_LOGIN, JIRA_PASSWORD)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_issue(self, issue_key: str) -> dict | None:
        """
        Получает информацию о задаче Jira по ключу (например, TBLT-5677).
        Возвращает dict с полями summary, status, status_id или None если не найдено.
        """
        try:
            response = requests.get(
                f"{self.base_url}/rest/api/2/issue/{issue_key}",
                auth=self.auth,
                headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    'key': issue_key,
                    'summary': data['fields'].get('summary', ''),
                    'status': data['fields'].get('status', {}).get('name', ''),
                    'status_id': data['fields'].get('status', {}).get('id', ''),
                }
            return None
        except Exception:
            return None

    def transition_issue(self, issue_key: str, target_status: str) -> bool:
        """
        Переводит задачу в указанный статус.
        Возвращает True если успешно, False если не удалось.
        """
        try:
            # Получаем доступные переходы
            response = requests.get(
                f"{self.base_url}/rest/api/2/issue/{issue_key}/transitions",
                auth=self.auth,
                headers=self.headers
            )
            if response.status_code != 200:
                return False

            transitions = response.json().get('transitions', [])

            # Ищем переход в нужный статус
            target_transition = None
            for t in transitions:
                if t.get('to', {}).get('name', '').lower() == target_status.lower():
                    target_transition = t
                    break

            if not target_transition:
                return False

            # Выполняем переход
            response = requests.post(
                f"{self.base_url}/rest/api/2/issue/{issue_key}/transitions",
                auth=self.auth,
                headers=self.headers,
                json={
                    "transition": {"id": target_transition['id']}
                }
            )
            return response.status_code in (200, 204)
        except Exception:
            return False

    def add_comment(self, issue_key: str, comment: str) -> bool:
        """
        Добавляет комментарий к задаче Jira.
        Возвращает True если успешно, False если не удалось.
        """
        try:
            response = requests.post(
                f"{self.base_url}/rest/api/2/issue/{issue_key}/comment",
                auth=self.auth,
                headers=self.headers,
                json={
                    "body": comment
                }
            )
            return response.status_code in (200, 201)
        except Exception:
            return False
