"""Poetry plugin for AWS CodeArtifact repositories."""
from collections import UserString, namedtuple
from collections.abc import Callable, Iterator
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar, cast

from poetry.config.config import Config
from poetry.console.application import Application
from poetry.plugins import ApplicationPlugin
from poetry.publishing import Publisher
from poetry.repositories.legacy_repository import LegacyRepository

if TYPE_CHECKING:
    from mypy_boto3_codeartifact.client import CodeArtifactClient


class LazyString(UserString):
    """String that doesn't have a value until it is required.

    This implementation is a string but will not have an actual value
    until __str__ is called. This is so we can avoid unnecessary calls
    to authenticate with AWS when we don't need to.
    """

    def __init__(self, lazy_value_factory: Callable[[], str]) -> None:
        """Creates a new instance of DeferredString."""
        self._deferred_value: Any = lazy_value_factory
        super().__init__("ERROR_IN_DEFERRED_VALUE")

    def __str__(self) -> str:
        """Returns the string value.

        If this is the first time __str__ is called, then the passed
        in callable is used to get a value.

        Subsequent calls will return the same value as the first call.
        """
        if not isinstance(self._deferred_value, str):
            self._deferred_value = self._deferred_value()

        return cast(str, self._deferred_value)

    def __add__(self, other: Any) -> str:  # type: ignore[override]
        """Append another string to this string."""
        if not isinstance(other, str):
            raise NotImplementedError
        return str(self) + other

    def __radd__(self, other: Any) -> str:  # type: ignore[override]
        """Append this string to another string."""
        if not isinstance(other, str):
            raise NotImplementedError
        return other + str(self)


def get_auth_token(domain: str, owner: str) -> LazyString:
    """
    Get a LazyString that will contain the AWS auth token.

    :param domain: The AWS CodeArtifact domain.
    :param owner: The AWS CodeArtifact owner ID.
    :return: A LazyString that will getch the auth token.
    """

    def deferred_auth_token() -> str:
        """The factory to use for the LazyString."""
        import boto3  # type: ignore[import]

        client: CodeArtifactClient = boto3.client("codeartifact")
        try:
            response = client.get_authorization_token(
                domain=domain,
                domainOwner=owner,
            )
            auth_token = response.get("authorizationToken")
            assert auth_token is not None  # noqa: S101
            return auth_token
        finally:
            client.close()

    return LazyString(deferred_auth_token)


T = TypeVar("T")


def require_publish_url(
    config: Config,
    *,
    repository: str,
    url: str,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Gets a decorator that will reconfigure the repository url when called.

    :param config: The poetry configuration.
    :param repository: The name of the repository.
    :param url: The url to use for publishing.
    :return: A decorator to use to wrap another function.
    """

    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        """A decorator that will reconfigure the repository url when called.

        A decorator that will reconfigure the url for a repository when
        the wrapped function is called. This is needed as the publishing url
        and search/download (simple) urls are different for AWS CodeArtifact.
        """

        @wraps(f)
        def publish(*args: Any, **kwargs: Any) -> Any:
            config.get("repositories")[repository] = {"url": url}
            return f(*args, **kwargs)

        return publish

    return decorator


Source = namedtuple("Source", "name domain owner region repository")


def find_codeartifact_sources(application: Application) -> Iterator[Source]:
    """Get all CodeArtifact sources that are configured in pyproject.toml."""
    tool_section = application.poetry.pyproject.data.get("tool")
    assert isinstance(tool_section, dict)  # noqa: S101
    plugin_section = tool_section.get(
        "poetry-plugin-code-artifact",
        {},
    )
    for source in plugin_section.get("sources", []):
        name = source.get("name", None)
        domain = source.get("aws-codeartifact-domain", None)
        owner = source.get("aws-codeartifact-owner", None)
        region = source.get("aws-codeartifact-region", None)
        repository = source.get("aws-codeartifact-repository", None)
        yield Source(name, domain, owner, region, repository)


def add_codeartifact_repository(  # noqa: PLR0913
    application: Application,
    *,
    name: str,
    username: str,
    password: str,
    simple_url: str,
    publish_url: str,
) -> None:
    """Configure poetry to use code artifact repository."""
    disable_cache = application.poetry.disable_cache

    config = application.poetry.config

    # Set up authentication.
    config.merge(
        config={
            "http-basic": {name: {"username": username, "password": password}},
        },
    )

    # Add search/download (simple) url.
    config.get("repositories")[name] = {"url": simple_url}

    # Add publishing url.
    # * Couldn't find a better way to determine if we're publishing, so
    # * created decorator for Publisher.publish to tweak url in the case
    # * we're publishing.
    Publisher.publish = require_publish_url(  # type: ignore[method-assign]
        config=config,
        repository=name,
        url=publish_url,
    )(Publisher.publish)

    # Add repository to the pool.
    application.poetry.pool.add_repository(
        LegacyRepository(name, simple_url, config, disable_cache),
    )


class CodeArtifactApplicationPlugin(
    ApplicationPlugin,
):
    """Poetry plugin for adding support for AWS CodeArtifact repositories."""

    def activate(self, application: Application) -> None:
        """Activate the plugin."""
        super().activate(application)

        for source in find_codeartifact_sources(application):
            hostname_prefix = f"{source.domain}-{source.owner}"
            hostname_suffix = f"d.codeartifact.{source.region}.amazonaws.com"
            hostname = f"{hostname_prefix}.{hostname_suffix}"
            publish_url = f"https://{hostname}/pypi/{source.repository}/"
            simple_url = f"{publish_url}simple/"
            password = get_auth_token(
                source.domain,
                source.owner,
            )
            add_codeartifact_repository(
                application,
                name=source.name,
                username="aws",
                password=password,  # type: ignore[arg-type]
                simple_url=simple_url,
                publish_url=publish_url,
            )
