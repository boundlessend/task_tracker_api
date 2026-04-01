class AppError(RuntimeError):
    """базовая ошибка приложения"""

    def __init__(self, message: str) -> None:
        """сохраняет сообщение ошибки"""

        super().__init__(message)
        self.message = message


class AppConfigurationError(AppError):
    """ошибка конфигурации приложения"""


class TaskTrackerError(AppError):
    """базовая ошибка домена задач"""


class TaskNotFoundError(TaskTrackerError):
    """задача не найдена"""


class DataIntegrityError(TaskTrackerError):
    """нарушение ограничений данных"""
