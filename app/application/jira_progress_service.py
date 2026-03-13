import json
import os
import logging
from app.providers.jira_repository import JiraRepository

logger = logging.getLogger(__name__)


class JiraProgressService:
    """
    Сервис для расчёта прогресса выполнения релиза на основе статусов задач в Jira.
    """

    def __init__(self):
        self.jira = JiraRepository()
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """Загружает конфигурацию из JSON файла."""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "jira_status_config.json"
        )
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading Jira status config: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        """Возвращает конфигурацию по умолчанию."""
        return {
            "status_progress": {
                "ЗАДАЧИ": 0,
                "АНАЛИЗ": 10,
                "К РАЗРАБОТКЕ": 20,
                "РАЗРАБОТКА": 30,
                "К ТЕСТИРОВАНИЮ": 40,
                "ТЕСТИРОВАНИЕ": 50,
                "CODE REVIEW": 60,
                "ГОТОВО К ПЕРЕНЕСЕНО": 70,
                "ПЕРЕНЕСЕНО": 90,
                "ПЕРЕНЕСЕНО В PROD": 100
            },
            "special_statuses": {
                "ДОРАБОТКА": 30,
                "К ДОРАБОТКЕ": 30,
                "REVIEW": 60
            },
            "exclude_statuses": ["ПРИОСТАНОВЛЕН", "ОТМЕНЕН"],
            "issue_types": ["Task", "Bug"]
        }

    def _get_status_progress(self, status: str) -> int | None:
        """
        Возвращает процент прогресса для статуса.
        
        Returns:
            int: процент прогресса (0-100)
            None: если статус должен быть исключён из расчёта
        """
        status_upper = status.upper().strip()
        
        logger.info(f"Processing status: '{status}' (upper: '{status_upper}')")
        
        # Проверяем статусы для исключения
        if status_upper in [s.upper() for s in self.config.get("exclude_statuses", [])]:
            logger.info(f"  -> Status '{status}' is EXCLUDED")
            return None
        
        # Проверяем основные статусы
        status_progress = self.config.get("status_progress", {})
        for key, value in status_progress.items():
            if key.upper() == status_upper:
                logger.info(f"  -> Status '{status}' matched '{key}' = {value}%")
                return value
        
        # Проверяем специальные статусы
        special_statuses = self.config.get("special_statuses", {})
        for key, value in special_statuses.items():
            if key.upper() == status_upper:
                logger.info(f"  -> Status '{status}' matched special '{key}' = {value}%")
                return value
        
        # Если статус не найден, возвращаем 0
        logger.info(f"  -> Status '{status}' not found, defaulting to 0%")
        return 0

    def calculate_release_progress(self, fix_version: str, project_key: str = "TBLT") -> dict:
        """
        Вычисляет прогресс выполнения релиза.
        
        Args:
            fix_version: Значение поля fixVersion в Jira
            project_key: Ключ проекта Jira
        
        Returns:
            dict: {
                "progress": float,  # общий прогресс в процентах
                "total_issues": int,  # всего задач
                "processed_issues": int,  # обработано задач (исключая excluded)
                "issues": list,  # детали по задачам
                "error": str | None  # ошибка если есть
            }
        """
        if not fix_version:
            return {
                "progress": 0.0,
                "total_issues": 0,
                "processed_issues": 0,
                "issues": [],
                "error": "Jira Fix Version не указан"
            }

        try:
            issues = self.jira.get_issues_by_fix_version(
                fix_version=fix_version,
                project_key=project_key,
                issue_types=self.config.get("issue_types", ["Task", "Bug"])
            )

            if not issues:
                return {
                    "progress": 0.0,
                    "total_issues": 0,
                    "processed_issues": 0,
                    "issues": [],
                    "error": None
                }

            total_progress = 0.0
            processed_count = 0
            issues_details = []

            for issue in issues:
                status = issue.get("status", "")
                progress = self._get_status_progress(status)
                
                issue_detail = {
                    "key": issue.get("key", ""),
                    "summary": issue.get("summary", ""),
                    "status": status,
                    "progress": progress if progress is not None else "excluded"
                }
                issues_details.append(issue_detail)

                if progress is not None:
                    total_progress += progress
                    processed_count += 1

            # Вычисляем средний прогресс
            if processed_count > 0:
                avg_progress = total_progress / processed_count
            else:
                avg_progress = 0.0

            return {
                "progress": round(avg_progress, 2),
                "total_issues": len(issues),
                "processed_issues": processed_count,
                "issues": issues_details,
                "error": None
            }

        except Exception as e:
            return {
                "progress": 0.0,
                "total_issues": 0,
                "processed_issues": 0,
                "issues": [],
                "error": str(e)
            }
