from app.database import add_log, list_logs


def register_log(action, person_id=None, message=None):
    return add_log(action=action, person_id=person_id, message=message)


def get_logs(limit=200):
    return list_logs(limit=limit)
