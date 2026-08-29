from sqlalchemy import inspect


def model_kwargs(model, payload: dict) -> dict:
    columns = {attr.key for attr in inspect(model).mapper.column_attrs}
    return {key: value for key, value in payload.items() if key in columns}
