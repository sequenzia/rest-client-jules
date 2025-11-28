from typing import Optional, Dict, Any, List, Iterator, AsyncIterator, Type, Generic, TypeVar
import httpx

T = TypeVar("T")

class PaginationStrategy:
    def get_next_request_params(self, response: httpx.Response, current_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        raise NotImplementedError

    def extract_items(self, response: httpx.Response) -> List[Any]:
        raise NotImplementedError

class OffsetLimitPagination(PaginationStrategy):
    def __init__(self, offset_param: str = "offset", limit_param: str = "limit", limit: int = 100, results_key: str = "data"):
        self.offset_param = offset_param
        self.limit_param = limit_param
        self.limit = limit
        self.results_key = results_key

    def get_next_request_params(self, response: httpx.Response, current_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        items = self.extract_items(response)
        if not items or len(items) < self.limit:
            return None

        current_offset = current_params.get(self.offset_param, 0)
        return {self.offset_param: current_offset + self.limit, self.limit_param: self.limit}

    def extract_items(self, response: httpx.Response) -> List[Any]:
        data = response.json()
        if self.results_key:
            # support nested keys "data.items"
            keys = self.results_key.split(".")
            for k in keys:
                data = data.get(k, [])
            return data
        return data

class Paginator(Generic[T]):
    def __init__(
        self,
        client: Any,
        url: str,
        strategy: PaginationStrategy,
        response_model: Optional[Type[T]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        self.client = client
        self.url = url
        self.strategy = strategy
        self.response_model = response_model
        self.params = params or {}
        self.kwargs = kwargs

    def __iter__(self) -> Iterator[T]:
        current_params = self.params.copy()
        while True:
            response = self.client.get(self.url, params=current_params, **self.kwargs)
            items = self.strategy.extract_items(response)

            for item in items:
                if self.response_model:
                     yield self.response_model(**item)
                else:
                     yield item

            next_params = self.strategy.get_next_request_params(response, current_params)
            if not next_params:
                break

            # Update params for next request
            current_params.update(next_params)

class AsyncPaginator(Generic[T]):
    def __init__(
        self,
        client: Any,
        url: str,
        strategy: PaginationStrategy,
        response_model: Optional[Type[T]] = None,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        self.client = client
        self.url = url
        self.strategy = strategy
        self.response_model = response_model
        self.params = params or {}
        self.kwargs = kwargs

    async def __aiter__(self) -> AsyncIterator[T]:
        current_params = self.params.copy()
        while True:
            response = await self.client.get(self.url, params=current_params, **self.kwargs)
            items = self.strategy.extract_items(response)

            for item in items:
                if self.response_model:
                     yield self.response_model(**item)
                else:
                     yield item

            next_params = self.strategy.get_next_request_params(response, current_params)
            if not next_params:
                break

            current_params.update(next_params)
