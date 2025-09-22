ExtraInfoType = dict[str, str | None]


class ClientError(Exception):
    """A request error from the GitHub Research client."""

    def __init__(self, message: str, extra_info: ExtraInfoType | None = None):
        msg = message
        if extra_info:
            msg += " (" + ", ".join([f"{key}: {value}" for key, value in extra_info.items() if value is not None]) + ")"
        super().__init__(msg)


class RequestError(ClientError):
    """A request error from the GitHub Research client."""

    def __init__(self, action: str, message: str | None = None, extra_info: ExtraInfoType | None = None):
        if not extra_info:
            extra_info = {}
        super().__init__(message="A request error occured.", extra_info={"action": action, "message": message, **extra_info})


class ResourceNotFoundError(RequestError):
    """A not found error from the GitHub Research client."""

    def __init__(self, action: str, resource: str | None = None, extra_info: ExtraInfoType | None = None):
        if not extra_info:
            extra_info = {}
        super().__init__(
            action=action,
            message="The resource could not be found.",
            extra_info={"resource": resource, **extra_info},
        )


class ResourceTypeMismatchError(RequestError):
    """A type mismatch error from the GitHub Research client."""

    def __init__(self, action: str, resource: str, expected_type: type, actual_type: type):
        super().__init__(action, f"{resource}: Expected {expected_type}, got {actual_type}")


class GraphQLRequestError(ClientError):
    """A request error from the GitHub Research client."""

    def __init__(self, action: str, message: str | None = None):
        msg = f"{action}: {message}" if message else action
        super().__init__(msg)


class GraphQLResourceNotFoundError(GraphQLRequestError):
    """A not found error from the GitHub Research client."""
