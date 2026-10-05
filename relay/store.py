tasks: dict[str, dict] = {}


def save_task(task: dict) -> None:
    tasks[task["task_id"]] = task


def get_task(task_id: str) -> dict | None:
    return tasks.get(task_id)