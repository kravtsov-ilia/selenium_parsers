import logging

logger = logging.getLogger(__name__)


class FacebookParseError(Exception):
    pass


class FacebookParseLikesError(FacebookParseError):
    pass
