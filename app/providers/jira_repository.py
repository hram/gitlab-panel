import requests
from requests.auth import HTTPBasicAuth
import logging

from app.infrastructure.config import (
    JIRA_URL,
    JIRA_LOGIN,
    JIRA_PASSWORD,
)

logger = logging.getLogger(__name__)


class JiraRepository:

    def __init__(self):
        self.base_url = JIRA_URL.rstrip('/')
        self.auth = HTTPBasicAuth(JIRA_LOGIN, JIRA_PASSWORD)
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def get_issues_by_fix_version(self, fix_version: str, project_key: str = "TBLT", issue_types: list[str] = None) -> list[dict]:
        """
        Получает все задачи из Jira по полю fixVersion.
        
        Args:
            fix_version: Значение поля fixVersion (например, "19027")
            project_key: Ключ проекта Jira (по умолчанию "TBLT")
            issue_types: Список типов задач (по умолчанию ["Task", "Bug"])
        
        Returns:
            Список задач с полями: key, summary, status
        """
        if issue_types is None:
            issue_types = ["Task", "Bug"]
        
        types_str = ", ".join(f'"{t}"' for t in issue_types)
        jql = f'project = "{project_key}" AND fixVersion = "{fix_version}" AND issuetype in ({types_str})'
        
        logger.info(f"Jira JQL Query: {jql}")
        logger.info(f"Jira Base URL: {self.base_url}")
        
        try:
            all_issues = []
            start_at = 0
            max_results = 100
            
            while True:
                request_body = {
                    "jql": jql,
                    "startAt": start_at,
                    "maxResults": max_results,
                    "fields": ["key", "summary", "status"]
                }
                
                logger.info(f"=== Jira API Request ===")
                logger.info(f"URL: {self.base_url}/rest/api/2/search")
                logger.info(f"Method: POST")
                logger.info(f"Body: {request_body}")
                logger.info(f"Auth: Basic {JIRA_LOGIN}:***")
                logger.info(f"========================")
                
                # Логируем как curl для удобства
                curl_command = (
                    f"curl -X POST '{self.base_url}/rest/api/2/search' "
                    f"-u '{JIRA_LOGIN}:{JIRA_PASSWORD}' "
                    f"-H 'Accept: application/json' "
                    f"-H 'Content-Type: application/json' "
                    f"-d '{request_body}'"
                )
                logger.info(f"curl command: {curl_command}")
                
                response = requests.post(
                    f"{self.base_url}/rest/api/2/search",
                    auth=self.auth,
                    headers=self.headers,
                    json=request_body
                )
                
                logger.info(f"Jira API Response Status: {response.status_code}")
                
                if response.status_code != 200:
                    logger.error(f"Jira API Error Response: {response.text[:500]}")
                    break
                
                data = response.json()
                issues = data.get('issues', [])
                
                logger.info(f"Received {len(issues)} issues (startAt={start_at})")
                
                if not issues:
                    break
                
                for issue in issues:
                    all_issues.append({
                        'key': issue['key'],
                        'summary': issue['fields'].get('summary', ''),
                        'status': issue['fields'].get('status', {}).get('name', ''),
                        'status_id': issue['fields'].get('status', {}).get('id', ''),
                    })
                
                # Проверка на наличие ещё задач
                if len(issues) < max_results:
                    break
                
                start_at += max_results
            
            logger.info(f"Total issues collected: {len(all_issues)}")
            return all_issues
        except Exception as e:
            logger.error(f"Error fetching issues from Jira: {e}")
            return []

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

    def get_project_versions(self, project_key: str) -> list[dict]:
        """
        Возвращает все версии Jira-проекта.
        GET /rest/api/2/project/{projectKey}/versions
        Каждый элемент содержит поля id, name, released и др.
        """
        try:
            response = requests.get(
                f"{self.base_url}/rest/api/2/project/{project_key}/versions",
                auth=self.auth,
                headers=self.headers,
            )
            if response.status_code == 200:
                return response.json()
            logger.error(f"Jira get_project_versions error {response.status_code}: {response.text[:200]}")
            return []
        except Exception as e:
            logger.error(f"Jira get_project_versions exception: {e}")
            return []

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
