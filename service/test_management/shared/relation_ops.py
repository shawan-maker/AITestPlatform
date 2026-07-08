"""测试管理模块 - shared/relation_ops

relation ops
"""
from typing import TypeVar

from tortoise import models
from tortoise.transactions import in_transaction

T = TypeVar("T", bound=models.Model)


async def reorder_relations(
    model: type[T],
    parent_field: str,
    parent_id: int,
    ordered_ids: list[int],
    id_field: str = "id",
) -> None:
    if not ordered_ids:
        return
    relations = await model.filter(**{parent_field: parent_id}).all()
    rel_map = {getattr(r, id_field): r for r in relations}
    if len(rel_map) != len(set(ordered_ids)) or set(rel_map.keys()) != set(ordered_ids):
        from service.core.exceptions import AppException

        raise AppException("排序项与现有关联不匹配", 400)
    order_field = "case_order" if hasattr(model, "case_order") else "suite_order"
    for idx, rel_id in enumerate(ordered_ids, start=1):
        rel = rel_map[rel_id]
        setattr(rel, order_field, idx)
        await rel.save(update_fields=[order_field])


async def batch_delete_relations(
    model: type[T],
    parent_field: str,
    parent_id: int,
    relation_ids: list[int],
) -> int:
    if not relation_ids:
        return 0
    deleted = await model.filter(
        **{parent_field: parent_id},
        id__in=relation_ids,
    ).delete()
    return deleted


async def replace_relations(
    model: type[T],
    parent_field: str,
    parent_id: int,
    items: list[dict],
    *,
    order_key: str = "case_order",
) -> None:
    async with in_transaction():
        await model.filter(**{parent_field: parent_id}).delete()
        for idx, item in enumerate(items, start=1):
            data = {**item, parent_field: parent_id, order_key: idx}
            await model.create(**data)
