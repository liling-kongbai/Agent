import json
import time
import typing
import uuid
from concurrent.futures import Future
from typing import Any, Optional

from langchain_core.runnables import Runnable, RunnableConfig
from langgraph.constants import CONFIG_KEY_STORE
from langgraph.store.base import BaseStore
from langgraph.store.postgres import PostgresStore
from langmem.reflection import LocalReflectionExecutor
from psycopg import Connection
from psycopg_pool import ConnectionPool

PENDING_REFLECTION_TASKS_NAMESPACE = 'pending_reflection_tasks'
SENTINEL = object()


class PersistenceExecutor:
    '''持久化执行器。LocalReflectionExecutor 包装器，持久化待办反思任务并提供重启恢复，增强 LocalReflectionExecutor'''

    def __init__(self, reflector: Runnable, store: BaseStore):
        self._inner_executor = LocalReflectionExecutor(reflector, store=None)
        self.store = store

        self._resume_pending_reflection_tasks()

    @staticmethod
    def setup(connection: Connection) -> None:
        '''为 PersistenceExecutor 创建所需数据库表'''
        CREATE_TABLE_SQL = f'''
        CREATE TABLE IF NOT EXISTS {PENDING_REFLECTION_TASKS_NAMESPACE} (
            key TEXT PRIMARY KEY,
            value JSONB NOT NULL
        );
        '''
        try:
            with connection.cursor() as cur:
                cur.execute(CREATE_TABLE_SQL)
        except Exception as e:
            print(f'<setup> 创建表失败！！！！！\n{e}')
            raise

    def _resume_pending_reflection_tasks(self) -> None:
        '''恢复待办反思任务。从 store 中加载所有保存的待办反思任务并重新提交到内存队列'''
        try:
            task_item = []
            current_offset = 0
            while True:
                page_item = self.store.search(PENDING_REFLECTION_TASKS_NAMESPACE, offset=current_offset)
                if page_item:
                    task_item.extend(page_item)
                    current_offset += 10
                else:
                    break
        except Exception as e:
            print(f'<_resume_pending_reflection_tasks> 无法获取 store 中的待办反思任务！！！！！\n{e}')

        if not task_item:
            return

        now = time.time()
        for item in task_item:
            try:
                task_data = item.value
                payload = task_data['payload']
                config = task_data['config']
                thread_id = config['configurable']['thread_id']
                execute_at = task_data['execute_at']
                remaining_time = max(0, execute_at - now)
                self.submit(payload, config, after_seconds=remaining_time, thread_id=thread_id)
            except Exception as e:
                print(f'<_resume_pending_reflection_tasks> 恢复待办反思任务失败！！！！！\n{e}')

    def submit(
        self,
        payload: dict[str, Any],
        /,
        config: RunnableConfig | None = None,
        *,
        after_seconds: int = 0,
        thread_id: Optional[typing.Union[str, uuid.UUID]] = SENTINEL,
    ) -> Future:
        user_id = config['configurable']['langgraph_user_id']
        thread_id = config['configurable']['thread_id']
        composite_id = f'{user_id}: {thread_id}'
        execute_at = time.time() + after_seconds
        task_data = {'payload': payload, 'config': config, 'execute_at': execute_at}

        try:
            if (
                isinstance(self.store, PostgresStore)
                and isinstance(self.store.conn, ConnectionPool)
                and hasattr(self.store.conn, '_pool')
            ):
                with self.store.conn.connection() as conn:
                    with conn.cursor() as cur:
                        PUT_SQL = f'''INSERT INTO {PENDING_REFLECTION_TASKS_NAMESPACE} (key, value) VALUES (%s, %s) ON conflict (key) DO UPDATE SET value = EXCLUDED.value;'''
                        cur.execute(PUT_SQL, (composite_id, json.dumps(task_data)))
            else:
                self.store.put(PENDING_REFLECTION_TASKS_NAMESPACE, composite_id, task_data)
        except Exception as e:
            print(f'<submit> 持久化待办反思任务失败！！！！！\n{e}')
            raise

        config_for_runtime = config.copy()
        config_for_runtime['configurable'][CONFIG_KEY_STORE] = self.store
        future = self._inner_executor.submit(
            payload, config_for_runtime, after_seconds=after_seconds, thread_id=thread_id
        )

        def _clean_on_done(fut: Future):
            if (
                not fut.cancelled() and fut.exception() is None
            ):  # cancelled() 判断 Future 是否已被取消 exception() 取出 Future 抛出的异常
                try:
                    if (
                        isinstance(self.store, PostgresStore)
                        and isinstance(self.store.conn, ConnectionPool)
                        and hasattr(self.store.conn, '_pool')
                    ):
                        with self.store.conn.connection() as conn:
                            with conn.cursor() as cur:
                                DELETE_SQL = f'''DELETE FROM {PENDING_REFLECTION_TASKS_NAMESPACE} WHERE key = %s;'''
                                cur.execute(DELETE_SQL, (composite_id,))
                    else:
                        self.store.delete(PENDING_REFLECTION_TASKS_NAMESPACE, composite_id)
                except Exception as e:
                    print(f'<submit> 清理待办反思任务失败！！！！！\n{e}')

        future.add_done_callback(_clean_on_done)
        return future

    def search(self, *args, **kwargs):
        return self._inner_executor.search(*args, **kwargs)

    async def asearch(self, *args, **kwargs):
        return await self._inner_executor.asearch(*args, **kwargs)

    def shutdown(self, *args, **kwargs):
        self._inner_executor.shutdown(*args, **kwargs)

    def __enter__(self):
        return

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown(wait=True)
        return False
