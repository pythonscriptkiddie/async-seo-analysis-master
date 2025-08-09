import concurrent.futures
import asyncio
from functools import partial
from typing import List, Dict, Callable, Iterable, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor


class DataProcessor:
    def __init__(self):
        self.executor = ThreadPoolExecutor()
        self.steps = []

    async def _process_item(self, items: List[Dict], func: Callable):
        '''Creates a ThreadPoolExecutor object and applies a function to a series of items.'''
        loop = asyncio.get_running_loop()
        calls = [partial(func, item) for item in items]
        with self.executor as pool:
            return await asyncio.gather(*[loop.run_in_executor(pool, call) for call in calls])

    def _merge(self, a, b):
        '''Merges two dictionaries. Is an instance method'''
        return dict(a, **b)

    def _omit(self, d: Dict, omitted_keys: Iterable = []):
        '''Takes a dictionary and a list. Converts the dictionary into a dict_items object
        using i.tems(). Then it checks for membership in "omitted keys," deleting any keys
        that are in that list, and thus marked for deletion.'''
        return {k: v for k, v in d.items() if k not in omitted_keys}

    def process_funcs(self, element: Dict, fields: List[Tuple[Callable, str, str]], omitted_keys: List = []):
        new_element = self._omit(d=element, omitted_keys=omitted_keys)
        for func, existing_field, new_field in fields:
            new_element[new_field] = func(element[existing_field])
        return new_element

    async def apply_process(self, items: List[Dict], fields: List[Tuple], processing_func: Callable,
                            formatter_func: Callable, omitted_keys: List[str] = []):
        apply_funcs = partial(processing_func, fields=fields, omitted_keys=omitted_keys)
        return await formatter_func(items=items, func=apply_funcs)

    async def step(self, items: Iterable, fields: List[Tuple[Callable, str]], omitted_keys: Optional[str]):
        if omitted_keys:
            if not isinstance(omitted_keys, list):
                raise ValueError('Omitted keys must be a list of strings')
            return await self.apply_process(items=items, fields=fields, processing_func=self.process_funcs,
                                            formatter_func=partial(self._process_item, func=self.process_funcs),
                                            omitted_keys=omitted_keys)
        else:
            return await self.apply_process(items=items, fields=fields, processing_func=self.process_funcs,
                                            formatter_func=partial(self._process_item, func=self.process_funcs))

    def add_step(self, fields: List[Tuple[Callable, str]], omitted_keys: Optional[str] = None):
        self.steps.append((fields, omitted_keys))

    async def get_step_result(self, step_index: int, items: Iterable):
        if step_index < 0 or step_index >= len(self.steps):
            raise ValueError('Invalid step index')
        fields, omitted_keys = self.steps[step_index]
        return await self.step(items=items, fields=fields, omitted_keys=omitted_keys)

    async def get_step_results(self, items: Iterable):
        results = []
        for step_index in range(len(self.steps)):
            result = await self.get_step_result(step_index, items)
            results.append(result)
        return results
    
async def step(data: List[Dict], fields: List[Tuple[Callable, str, str]],
              omitted_keys: List[str]):
   
    '''Coroutine that takes a list, applies a series of functions to specified keys, and
    returns the modified list.'''
   # print(omitted_keys)

    processor = DataProcessor()



    processed_data = await processor.step(items=data, fields=fields, omitted_keys=omitted_keys)

    #@for item in processed_data:
    #    print(item.get('content_hash'))
    return processed_data