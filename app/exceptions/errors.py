from __future__ import annotations


class AppError(RuntimeError):
    """базовая ошибка приложения"""

    status_code = 400
    error_code = "app_error"

    def __init__(self, message: str, details: object | None = None) -> None:
        """сохраняет сообщение и детали ошибки"""

        super().__init__(message)
        self.message = message
        self.details = details


class AppConfigurationError(AppError):
    """ошибка конфигурации приложения"""

    error_code = "app_configuration_error"


class TaskTrackerError(AppError):
    """базовая ошибка домена задач"""


class TaskNotFoundError(TaskTrackerError):
    """задача не найдена"""

    status_code = 404
    error_code = "task_not_found"


class CommentNotFoundError(TaskTrackerError):
    """комментарий не найден"""

    status_code = 404
    error_code = "comment_not_found"


class UserNotFoundError(TaskTrackerError):
    """пользователь не найден"""

    status_code = 404
    error_code = "user_not_found"


class DataIntegrityError(TaskTrackerError):
    """нарушение ограничений данных"""

    error_code = "data_integrity_error"


class TaskConflictError(TaskTrackerError):
    """конфликт состояния задачи"""

    status_code = 409
    error_code = "task_conflict"


class TaskAlreadyClosedError(TaskConflictError):
    """задача уже закрыта"""

    error_code = "task_already_closed"
