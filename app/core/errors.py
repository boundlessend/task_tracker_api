from __future__ import annotations


class AppError(RuntimeError):
    """базовая ошибка приложения"""

    status_code = 400
    code = "app_error"

    def __init__(self, message: str, details: object | None = None) -> None:
        """сохраняет сообщение и детали ошибки"""

        super().__init__(message)
        self.message = message
        self.details = details


class AppConfigurationError(AppError):
    """ошибка конфигурации приложения"""

    code = "app_configuration_error"


class TaskTrackerError(AppError):
    """базовая ошибка домена задач"""


class TaskNotFoundError(TaskTrackerError):
    """задача не найдена"""

    status_code = 404
    code = "task_not_found"


class DataIntegrityError(TaskTrackerError):
    """нарушение ограничений данных"""

    code = "data_integrity_error"


class TaskConflictError(TaskTrackerError):
    """конфликт состояния задачи"""

    status_code = 409
    code = "task_conflict"
