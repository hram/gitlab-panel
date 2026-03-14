from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from app.domain.models.release_stage_history import ReleaseStageHistory
from app.domain.models.stage import Stage
from app.application.stage_service import StageService


@dataclass
class StageDuration:
    """Результат расчёта длительности стадии."""
    id: Optional[int]
    release_id: int
    old_stage: Optional[str]
    new_stage: str
    changed_at: datetime
    duration_days: Optional[int]


@dataclass
class StageSLAMetric:
    """Метрика SLA для стадии."""
    stage_name: str
    average_duration_days: float
    min_duration_days: int
    max_duration_days: int
    total_transitions: int
    sla_compliance_rate: float  # процент соблюдения SLA (0-100)


@dataclass
class ReleaseCycleMetrics:
    """Метрики цикла релиза."""
    total_cycle_days: int
    average_stage_duration_days: float
    longest_stage: Optional[str]
    shortest_stage: Optional[str]
    stages_passed: int


class StageAnalyticsService:
    """
    Универсальный сервис для аналитики стадий релизов.
    Предоставляет методы для расчёта длительностей, SLA-метрик и статистики.
    """

    def __init__(self):
        self.stage_service = StageService()

    def calculate_stage_durations(
        self,
        history: list[ReleaseStageHistory]
    ) -> list[StageDuration]:
        """
        Вычисляет длительность каждой стадии в днях.
        
        Длительность = разница между датой текущей записи и датой предыдущей записи.
        Для первой записи (создание) длительность не вычисляется.
        
        Args:
            history: Список записей истории стадий, отсортированный по дате.
            
        Returns:
            Список StageDuration с рассчитанными длительностями.
        """
        result = []
        for i, h in enumerate(history):
            duration_days = None
            # Для записей после первой (i > 0) вычисляем длительность
            # как разницу между текущей датой и предыдущей
            if i > 0:
                prev_entry = history[i - 1]
                delta = h.changed_at - prev_entry.changed_at
                duration_days = delta.days

            result.append(StageDuration(
                id=h.id,
                release_id=h.release_id,
                old_stage=h.old_stage,
                new_stage=h.new_stage,
                changed_at=h.changed_at,
                duration_days=duration_days,
            ))
        return result

    def calculate_release_cycle_metrics(
        self,
        history: list[ReleaseStageHistory]
    ) -> Optional[ReleaseCycleMetrics]:
        """
        Вычисляет метрики полного цикла релиза.
        
        Args:
            history: Список записей истории стадий.
            
        Returns:
            ReleaseCycleMetrics или None, если история пуста.
        """
        if not history or len(history) < 2:
            return None

        durations = self.calculate_stage_durations(history)
        duration_values = [d.duration_days for d in durations if d.duration_days is not None]

        if not duration_values:
            return None

        total_cycle_days = sum(duration_values)
        avg_duration = total_cycle_days / len(duration_values)

        # Находим самую длинную и короткую стадии
        stage_durations = [
            (d.new_stage, d.duration_days)
            for d in durations
            if d.duration_days is not None
        ]
        
        longest_stage = max(stage_durations, key=lambda x: x[1])[0] if stage_durations else None
        shortest_stage = min(stage_durations, key=lambda x: x[1])[0] if stage_durations else None

        return ReleaseCycleMetrics(
            total_cycle_days=total_cycle_days,
            average_stage_duration_days=round(avg_duration, 2),
            longest_stage=longest_stage,
            shortest_stage=shortest_stage,
            stages_passed=len(duration_values),
        )

    def calculate_stage_sla_metrics(
        self,
        all_history: list[tuple[int, ReleaseStageHistory]],  # list of (release_id, history_entry)
        stage_order_map: dict[str, int],
        sla_limits: Optional[dict[str, int]] = None,  # stage_name -> max_days
    ) -> list[StageSLAMetric]:
        """
        Вычисляет SLA-метрики для всех стадий на основе истории множества релизов.
        
        Args:
            all_history: Список кортежей (release_id, запись_истории) для анализа.
            stage_order_map: Маппинг названий стадий в их порядок.
            sla_limits: Опциональные лимиты SLA для каждой стадии (в днях).
            
        Returns:
            Список StageSLAMetric для каждой стадии.
        """
        # Группируем длительности по стадиям
        stage_durations: dict[str, list[int]] = {}
        
        # Сортируем по release_id и дате
        sorted_history = sorted(all_history, key=lambda x: (x[0], x[1].changed_at))
        
        # Вычисляем длительности для каждого релиза
        current_release_id = None
        prev_entry = None
        
        for release_id, entry in sorted_history:
            if release_id != current_release_id:
                current_release_id = release_id
                prev_entry = entry
                continue
            
            if entry.old_stage is not None and prev_entry is not None:
                delta = entry.changed_at - prev_entry.changed_at
                duration_days = delta.days
                
                if entry.old_stage not in stage_durations:
                    stage_durations[entry.old_stage] = []
                stage_durations[entry.old_stage].append(duration_days)
            
            prev_entry = entry

        # Вычисляем метрики для каждой стадии
        metrics = []
        for stage_name in sorted(stage_order_map.keys(), key=lambda x: stage_order_map[x]):
            durations = stage_durations.get(stage_name, [])
            
            if not durations:
                continue

            avg_duration = sum(durations) / len(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            
            # Расчёт compliance rate
            sla_compliance = 100.0
            if sla_limits and stage_name in sla_limits:
                limit = sla_limits[stage_name]
                compliant_count = sum(1 for d in durations if d <= limit)
                sla_compliance = (compliant_count / len(durations)) * 100

            metrics.append(StageSLAMetric(
                stage_name=stage_name,
                average_duration_days=round(avg_duration, 2),
                min_duration_days=min_duration,
                max_duration_days=max_duration,
                total_transitions=len(durations),
                sla_compliance_rate=round(sla_compliance, 1),
            ))

        return metrics

    def get_stage_transition_duration(
        self,
        from_stage: str,
        to_stage: str,
        history: list[ReleaseStageHistory]
    ) -> Optional[int]:
        """
        Вычисляет длительность перехода между двумя конкретными стадиями.
        
        Args:
            from_stage: Название исходной стадии.
            to_stage: Название целевой стадии.
            history: Список записей истории стадий.
            
        Returns:
            Количество дней или None, если переход не найден.
        """
        for i, entry in enumerate(history):
            if entry.old_stage == from_stage and entry.new_stage == to_stage:
                if i > 0:
                    prev_entry = history[i - 1]
                    delta = entry.changed_at - prev_entry.changed_at
                    return delta.days
        return None

    def predict_release_completion(
        self,
        history: list[ReleaseStageHistory],
        stages: list[Stage],
        current_stage: str
    ) -> Optional[dict]:
        """
        Предсказывает дату завершения релиза на основе исторических данных.
        
        Args:
            history: История стадий текущего релиза.
            stages: Список всех стадий проекта.
            current_stage: Текущая стадия релиза.
            
        Returns:
            Словарь с предсказанной датой завершения и оставшимися днями,
            или None, если недостаточно данных.
        """
        if not history:
            return None

        # Получаем порядок стадий
        stage_order = {s.name: s.order for s in stages}
        
        if current_stage not in stage_order:
            return None

        # Находим оставшиеся стадии
        current_order = stage_order[current_stage]
        remaining_stages = [s for s in stages if s.order > current_order]
        
        if not remaining_stages:
            return None

        # Вычисляем средние длительности из истории
        durations = self.calculate_stage_durations(history)
        stage_avg_durations: dict[str, float] = {}
        
        for d in durations:
            if d.duration_days is not None and d.old_stage:
                if d.old_stage not in stage_avg_durations:
                    stage_avg_durations[d.old_stage] = []
                stage_avg_durations[d.old_stage].append(d.duration_days)
        
        # Усредняем
        for stage in stage_avg_durations:
            stage_avg_durations[stage] = sum(stage_avg_durations[stage]) / len(stage_avg_durations[stage])

        # Предсказываем оставшееся время
        predicted_days = 0
        for stage in remaining_stages[:-1]:  # Все стадии кроме последней
            predicted_days += round(stage_avg_durations.get(stage.name, 3))  # 3 дня по умолчанию
        
        # Для последней стадии (prod) берем среднее или 3 дня
        if remaining_stages:
            last_stage = remaining_stages[-1].name
            predicted_days += round(stage_avg_durations.get(last_stage, 3))

        last_entry_date = max(h.changed_at for h in history)
        predicted_date = last_entry_date.replace(
            day=last_entry_date.day + predicted_days
        )

        return {
            'predicted_completion_date': predicted_date,
            'remaining_days': predicted_days,
            'remaining_stages': [s.name for s in remaining_stages],
        }
