"""Public API for parsing and navigating OpenAPI documents."""

import functools
import json
import pathlib
import typing
from enum import StrEnum

import httpx
import openapi_pydantic.v3.v3_0 as _v30
import openapi_pydantic.v3.v3_1 as _v31
import yaml
from openapi_pydantic import parse_obj

OpenAPI = _v30.OpenAPI | _v31.OpenAPI
Operation = _v30.Operation | _v31.Operation
Schema = _v30.Schema | _v31.Schema
Parameter = _v30.Parameter | _v31.Parameter
"""An OpenAPI 3.0 or 3.1 operation parameter."""

Reference = _v30.Reference | _v31.Reference
"""An OpenAPI 3.0 or 3.1 reference."""

RequestBody = _v30.RequestBody | _v31.RequestBody
"""An OpenAPI 3.0 or 3.1 request body."""

Responses = _v30.Responses | _v31.Responses
"""An OpenAPI 3.0 or 3.1 responses mapping."""

Response = _v30.Response | _v31.Response
"""An OpenAPI 3.0 or 3.1 response."""

Info = _v30.Info | _v31.Info


class Method(StrEnum):
    """HTTP method supported by an OpenAPI operation.

    Attributes:
        GET: Retrieve a resource.
        POST: Submit data to a resource.
        PUT: Replace a resource.
        PATCH: Partially update a resource.
        DELETE: Delete a resource.
        HEAD: Retrieve response headers for a resource.
        OPTIONS: Retrieve communication options for a resource.
        TRACE: Perform a message loop-back test.
    """

    GET = "get"
    POST = "post"
    PUT = "put"
    PATCH = "patch"
    DELETE = "delete"
    HEAD = "head"
    OPTIONS = "options"
    TRACE = "trace"


type Endpoint = tuple[str, Method, Operation]
"""An endpoint represented by its path, HTTP method, and operation."""

type NamedSchema = tuple[str, Schema | Reference]
"""A component schema represented by its name and schema or reference."""


def _load_from_url(url: str) -> dict[str, typing.Any]:
    response = httpx.get(url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    text = response.text
    if "yaml" in content_type or url.endswith((".yaml", ".yml")):
        return yaml.safe_load(text)
    return json.loads(text)


def _load_from_file(path: str) -> dict[str, typing.Any]:
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if path.endswith((".yaml", ".yml")):
        return yaml.safe_load(content)
    return json.loads(content)


def _param_key(
    p: _v30.Parameter | _v31.Parameter | _v30.Reference | _v31.Reference,
) -> str:
    if isinstance(p, (_v30.Parameter, _v31.Parameter)):
        return p.name
    return p.ref


class OpenAPIParser:
    """Parser for navigating an OpenAPI document.

    Args:
        openapi: Parsed OpenAPI 3.0 or 3.1 document.

    Attributes:
        openapi: Parsed OpenAPI document exposed by the parser.
    """

    def __init__(self, openapi: OpenAPI) -> None:
        self.openapi = openapi

    @classmethod
    def from_source(cls, source: str | pathlib.Path) -> typing.Self:
        """Load an OpenAPI document from a file path or URL.

        JSON and YAML documents are supported. String sources beginning with
        ``http://`` or ``https://`` are treated as URLs; all other sources are
        treated as local file paths.

        Args:
            source: Local file path or HTTP(S) URL of the OpenAPI document.

        Returns:
            A parser containing the validated OpenAPI document.
        """
        if isinstance(source, pathlib.Path):
            raw = _load_from_file(str(source))
        elif source.startswith("http://") or source.startswith("https://"):
            raw = _load_from_url(source)
        else:
            raw = _load_from_file(source)
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, data: dict[str, typing.Any]) -> typing.Self:
        """Load an OpenAPI document from a dictionary.

        Args:
            data: Dictionary containing the OpenAPI document.

        Returns:
            A parser containing the validated OpenAPI document.
        """
        spec = parse_obj(data)
        return cls(spec)

    @property
    def info(self) -> Info:
        """Return metadata from the OpenAPI document.

        Returns:
            The document's Info object.
        """
        return self.openapi.info

    @functools.cached_property
    def endpoints(self) -> list[Endpoint]:
        """Return the endpoints in the OpenAPI document.

        Path-level parameters are merged into each operation unless overridden
        by an operation-level parameter with the same name.

        Returns:
            Tuples containing the path, HTTP method, and operation.
        """
        endpoints: list[Endpoint] = []
        paths = self.openapi.paths or {}

        for path, path_item in paths.items():
            path_level_params = path_item.parameters or []
            for method, operation in [
                (Method.GET, path_item.get),
                (Method.POST, path_item.post),
                (Method.PUT, path_item.put),
                (Method.PATCH, path_item.patch),
                (Method.DELETE, path_item.delete),
                (Method.HEAD, path_item.head),
                (Method.OPTIONS, path_item.options),
                (Method.TRACE, path_item.trace),
            ]:
                if operation is None:
                    continue
                if path_level_params:
                    op_param_names = {
                        _param_key(p) for p in (operation.parameters or [])
                    }
                    inherited = [
                        p
                        for p in path_level_params
                        if _param_key(p) not in op_param_names
                    ]
                    if inherited:
                        merged_params = list(inherited) + list(
                            operation.parameters or []
                        )
                        operation = operation.model_copy(
                            update={"parameters": merged_params}
                        )
                endpoints.append((path, method, operation))
        return endpoints

    @functools.cached_property
    def schemas(self) -> list[NamedSchema]:
        """Return the component schemas in the OpenAPI document.

        Returns:
            Tuples containing the schema name and its schema or reference.
        """
        components = self.openapi.components
        if not components or not components.schemas:
            return []
        return list(components.schemas.items())

    def resolve_reference(self, ref: Reference) -> typing.Any:
        """Resolve a component reference.

        Args:
            ref: OpenAPI reference to resolve.

        Returns:
            The referenced component.

        Raises:
            ValueError: If the reference format is unsupported or the target
                component does not exist.
        """
        ref_path = ref.ref.split("/")
        if len(ref_path) < 3 or ref_path[0] != "#" or ref_path[1] != "components":
            raise ValueError(f"Unsupported reference format: {ref.ref}")  # noqa: TRY003
        _, _, category, name = ref_path
        components = self.openapi.components
        if not components:
            raise ValueError("No components defined in the OpenAPI spec")  # noqa: TRY003
        category_dict = getattr(components, category, None)
        if not category_dict:
            raise ValueError(f"No such component category: {category}")  # noqa: TRY003
        resolved = category_dict.get(name)
        if not resolved:
            raise ValueError(  # noqa: TRY003
                f"No such component named '{name}' in category '{category}'"
            )
        return resolved

    def get_referenced[T](self, item: Reference | T) -> T:
        """Resolve an item when it is a reference.

        Args:
            item: Reference to resolve or concrete value to return unchanged.

        Returns:
            The resolved reference or the original concrete value.

        Raises:
            ValueError: If a reference cannot be resolved.
        """
        if isinstance(item, Reference):
            return self.resolve_reference(item)
        return item


__all__ = [
    "OpenAPIParser",
    "Endpoint",
    "Parameter",
    "Reference",
    "Method",
    "NamedSchema",
    "RequestBody",
    "Responses",
    "Response",
]
