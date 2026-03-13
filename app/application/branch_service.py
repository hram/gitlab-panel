from app.domain.models.branch import Branch
from app.providers.gitlab_repository import GitLabRepository
from app.providers.jira_repository import JiraRepository
from app.infrastructure.sqlite_release_repository import SQLiteReleaseRepository
from app.application.stage_service import StageService
import re


class BranchService:

    def __init__(self):
        self.repo = GitLabRepository()
        self.release_repo = SQLiteReleaseRepository()
        self.stage_service = StageService()
        self.jira = JiraRepository()

    def list_branches(self, search: str | None = None, project_id: int | None = None):
        return self.repo.list_branches(search, project_id=project_id)

    def list_branches_by_releases(self, search: str | None = None, project_id: int | None = None) -> list[Branch]:
        """Возвращает только те ветки, для которых в БД есть релиз с соответствующей версией."""
        if project_id is None:
            return []

        all_branches = self.list_branches(search, project_id=project_id)
        release_versions = self.release_repo.get_release_versions(project_id)

        if not release_versions:
            return []

        filtered = []
        for branch in all_branches:
            # Ветка имеет формат <stage>/<release>, например "alpha/1.54.0"
            parts = branch.name.split("/")
            if len(parts) >= 2:
                version = parts[-1]  # Последняя часть - это версия релиза
                if version in release_versions:
                    filtered.append(branch)

        return filtered

    def create_release_branches(
        self,
        project_id: int,
        version: str,
        source_branch: str,
    ) -> tuple[list[str], list[str]]:
        """
        Создаёт цепочку веток для нового релиза.
        Возвращает кортеж (созданные_ветки, предупреждения).

        Логика:
        1. Первая ветка создаётся от указанной source_branch
        2. Каждую следующую ветку создавать от предыдущей новой ветки

        source_branch — ветка, отображённая пользователю в форме.
        """
        created_branches = []
        warnings = []

        # Получаем стадии проекта в порядке stage_order
        stages = self.stage_service.list_stages(project_id)
        if not stages:
            raise ValueError("У проекта нет стадий. Сначала создайте стадии.")

        # Инициализируем GitLabRepository для конкретного проекта
        gitlab_repo = GitLabRepository(project_id=project_id)

        # Создаём цепочку веток
        current_ref = source_branch

        for stage in stages:
            branch_name = f"{stage.name}/{version}"

            try:
                gitlab_repo.create_branch(branch_name, current_ref)
                created_branches.append(branch_name)
                # Следующая ветка создаётся от текущей
                current_ref = branch_name
            except Exception as e:
                # Если не удалось создать ветку — добавляем предупреждение и продолжаем
                warnings.append(f"Не удалось создать ветку '{branch_name}': {str(e)}")
                # Прерываем цепочку — следующая ветка не может быть создана от несуществующей
                break

        return created_branches, warnings

    def _get_latest_release(self, releases: list) -> object | None:
        """Возвращает релиз с максимальной версией (по SemVer)."""
        if not releases:
            return None

        def parse_version(v):
            parts = v.version.split('.')
            return tuple(int(p) for p in parts)

        return max(releases, key=parse_version)

    def get_next_release_source_branch(self, project_id: int) -> str:
        """
        Возвращает имя ветки, от которой будет создана первая ветка нового релиза.
        """
        all_releases = self.release_repo.list_releases(project_id)

        if all_releases:
            latest_release = self._get_latest_release(all_releases)
            if latest_release:
                return f"{latest_release.stage}/{latest_release.version}"

        return "main"

    def create_feature_branch_and_mr(
        self,
        project_id: int,
        old_stage: str,
        new_stage: str,
        version: str,
        jira_key: str,
    ) -> dict:
        """
        Создаёт feature-ветку и MR при смене стадии релиза.

        Возвращает dict с результатами:
        - success: bool
        - branch_created: str | None
        - mr_created: dict | None
        - jira_transition: bool
        - warnings: list[str]
        - errors: list[str]
        """
        result = {
            'success': True,
            'branch_created': None,
            'mr_created': None,
            'jira_transition': False,
            'warnings': [],
            'errors': [],
        }

        source_branch = f"{old_stage}/{version}"
        feature_branch = f"feature/{jira_key}"
        target_branch = f"{new_stage}/{version}"

        # 1. Создаём feature-ветку от source_branch
        try:
            self.repo.create_branch(feature_branch, source_branch)
            result['branch_created'] = feature_branch
        except Exception as e:
            result['errors'].append(f"Не удалось создать ветку {feature_branch}: {str(e)}")
            result['success'] = False
            return result  # Без feature-ветки дальше нет смысла

        # 2. Переводим таску в CodeReview (если получится)
        try:
            jira_issue = self.jira.get_issue(jira_key)
            if jira_issue:
                transitioned = self.jira.transition_issue(jira_key, "CodeReview")
                result['jira_transition'] = transitioned
                if not transitioned:
                    result['warnings'].append(
                        f"Не удалось перевести {jira_key} в статус CodeReview"
                    )
            else:
                result['warnings'].append(f"Задача {jira_key} не найдена в Jira")
        except Exception as e:
            result['warnings'].append(f"Ошибка при работе с Jira: {str(e)}")

        # 3. Создаём MR (если получится)
        try:
            jira_issue = self.jira.get_issue(jira_key)
            title = f"{jira_key} {jira_issue['summary']}" if jira_issue else jira_key
            description = f"MR для смены стадии релиза {version}\n" \
                         f"Старая стадия: {old_stage}\n" \
                         f"Новая стадия: {new_stage}\n" \
                         f"Jira: {jira_key}"

            mr = self.repo.create_merge_request(
                source_branch=feature_branch,
                target_branch=target_branch,
                title=title,
                description=description,
                squash=False,  # Squash отключён по требованию
            )
            result['mr_created'] = mr

            # 4. После создания MR — устанавливаем 'Merge when pipeline succeeds'
            if mr:
                self.repo.enable_merge_when_pipeline_succeeds(mr['iid'])

            # 5. После создания MR — добавляем комментарий с задачами в Jira
            if mr:
                mr_result = self.add_jira_comment_for_mr(mr['iid'], jira_key)
                if mr_result['success']:
                    result['jira_tasks_added'] = mr_result['tasks_added']
                else:
                    result['warnings'].append(
                        f"Не удалось добавить комментарий в Jira: {mr_result.get('error', 'Неизвестная ошибка')}"
                    )

        except Exception as e:
            result['warnings'].append(f"Не удалось создать MR: {str(e)}")

        return result

    def extract_jira_tasks_from_commits(self, commits: list[dict]) -> list[str]:
        """
        Извлекает список Jira-задач из коммитов MR.
        Фильтрует коммиты типа "Merge branch" и извлекает задачи в формате "<JIRA-KEY> <title>".
        """
        jira_tasks = []
        merge_branch_pattern = re.compile(r'^Merge branch')
        jira_key_pattern = re.compile(r'^([A-Z]+-\d+)\s+(.+)$')

        for commit in commits:
            message = commit.get('message', '')
            title = commit.get('title', '')

            # Пропускаем коммиты "Merge branch"
            if merge_branch_pattern.match(title):
                continue

            # Извлекаем Jira-ключ и описание из первой строки сообщения
            match = jira_key_pattern.match(title)
            if match:
                jira_key = match.group(1)
                task_title = match.group(2)
                jira_tasks.append(f"{jira_key} {task_title}")

        return jira_tasks

    def format_jira_comment(self, jira_tasks: list[str]) -> str:
        """
        Форматирует комментарий для Jira со списком влитых задач.
        """
        comment = "Влиты таски:\n"
        for task in jira_tasks:
            comment += f"- {task}\n"
        return comment.rstrip('\n')

    def add_jira_comment_for_mr(self, mr_iid: int, jira_key: str) -> dict:
        """
        Получает коммиты MR, извлекает Jira-задачи и добавляет комментарий в Jira.
        Возвращает dict с результатами операции.
        """
        result = {
            'success': False,
            'tasks_added': [],
            'comment_added': False,
            'error': None,
        }

        try:
            # Получаем коммиты MR
            commits = self.repo.get_merge_request_commits(mr_iid)
            
            # Извлекаем Jira-задачи
            jira_tasks = self.extract_jira_tasks_from_commits(commits)
            
            if not jira_tasks:
                result['error'] = "Не найдено задач в формате '<JIRA-KEY> <title>'"
                return result

            # Форматируем комментарий
            comment = self.format_jira_comment(jira_tasks)

            # Добавляем комментарий в Jira
            comment_added = self.jira.add_comment(jira_key, comment)
            
            result['tasks_added'] = jira_tasks
            result['comment_added'] = comment_added
            result['success'] = comment_added

            if not comment_added:
                result['error'] = "Не удалось добавить комментарий в Jira"

        except Exception as e:
            result['error'] = str(e)

        return result