from sqlalchemy import inspect


def column_names(model, exclude: set[str] = frozenset()) -> tuple[str, ...]:
    return tuple(attr.key for attr in inspect(model).mapper.column_attrs if attr.key not in exclude)


def model_kwargs(model, payload: dict) -> dict:
    columns = set(column_names(model))
    return {key: value for key, value in payload.items() if key in columns}
