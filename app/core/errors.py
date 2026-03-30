class AppError(RuntimeError):
    """Базовая ошибка."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AppConfigurationError(AppError):
    """Возникает при неверных настройках приложения."""


class TaskTrackerError(AppError):
    """Базовая ошибка таск-трекера."""


class TaskNotFoundError(TaskTrackerError):
    """Возникает когда таск не найден."""
