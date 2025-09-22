ExtraInfoType = dict[str, str | None]


class ServerError(Exception):
    """A request error from the GitHub Research server."""

    def __init__(self, message: str, extra_info: ExtraInfoType | None = None):
        msg = message
        if extra_info:
            msg += " (" + ", ".join([f"{key}: {value}" for key, value in extra_info.items() if value is not None]) + ")"
        super().__init__(msg)


class SamplingSupportRequiredError(ServerError):
    """A sampling support required error from the GitHub Research server."""

    def __init__(self):
        super().__init__(message="Your client does not support sampling. Sampling support is required to use the summarization tools.")
