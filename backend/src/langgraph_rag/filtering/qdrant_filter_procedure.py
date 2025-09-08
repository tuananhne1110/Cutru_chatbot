from __future__ import annotations

"""
QdrantFilterProcedure
---------------------
A small utility to validate/normalize a filter spec (JSON/dict) for
Vietnam admin procedures (thủ tục hành chính) and convert it to a
Qdrant Filter (either Python client models or a plain REST dict).

Design goals
- No hard dependency on qdrant_client: if not installed, we fall back to dicts
- Friendly, permissive input schema: {must|should|must_not} with simple ops
- Light validation + type coercion using a declared payload schema
- Helpers for merging filters and converting to/from dict

Example
-------
filterer = QdrantFilterProcedure(global_config)
spec = {
    "must": [
        {"key": "field", "op": "in", "value": ["cư trú", "hộ tịch"]},
        {"key": "decision_year", "op": "gte", "value": 2021},
    ],
    "must_not": [
        {"key": "effect_status", "op": "eq", "value": "đã bãi bỏ"}
    ],
}
qf = filterer.build(spec)  # qdrant_client.http.models.Filter OR plain dict

# Use in a search call (Python client):
# client.search(collection_name, query_vector=..., limit=5, filter=qf)
"""

import json
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from .base_filter import BaseFilterConfig, FilterConfig
from ..utils.config_utils import BaseConfig
from ..utils.logger_utils import get_logger



logger = get_logger(__name__)


try:
    # Optional import: works when qdrant_client is installed
    from qdrant_client.http.models import (
        Filter as QFilter,
        FieldCondition as QFieldCondition,
        MatchValue as QMatchValue,
        MatchAny as QMatchAny,
        Range as QRange,
        IsEmptyCondition as QIsEmptyCondition,
    )

except Exception:  # pragma: no cover - soft dependency
    QFilter = QFieldCondition = QMatchValue = QMatchAny = QRange = QIsEmptyCondition = None  # type: ignore


FilterLike = Union[dict, "QFilter"]
ConditionLike = Union[dict, "QFieldCondition", "QIsEmptyCondition"]


class QdrantFilterProcedure(BaseFilterConfig):
    """Builds Qdrant-compatible filters for the *procedure* domain.

    Input spec format (permissive):
    {
      "must": [ {"key": "field", "op": "eq|in|gt|gte|lt|lte|between|exists|missing", "value": ...}, ...],
      "should": [ ... ],
      "must_not": [ ... ]
    }

    Shorthands:
    - op omitted => "eq"
    - value is list/tuple => defaults to op "in"
    - A group value can be a single dict instead of a list
    """

    def __init__(self, global_config: Optional[Any] = None) -> None:
        super().__init__(global_config)

        self._init_filter_config()
        

    def _init_filter_config(self) -> None:
        # You can inject domain defaults using your global_config
        base: Dict[str, Any] = getattr(self.global_config, "__dict__", {})

        # Allowed payload schema (lightweight typing for coercion)
        allowed_fields: Dict[str, str] = {
            # Core identifiers / names
            "procedure_code": "str",
            "decision_number": "str",
            "procedure_name": "str",
            # Domain facets
            "implementation_level": "str",  # "trung ương"|"tỉnh"|"huyện"|"xã" ...
            "procedure_type": "str",
            "field": "str",  # lĩnh vực
            "implementation_subject": "str",
            # Dates / status
            "effect_status": "str",
            "effective_date": "date",
            "expiry_date": "date",
            "decision_year": "int",
            # Misc
            "issuing_authority": "str",
            "tags": "list[str]",
            "is_active": "bool",
        }

        field_aliases: Dict[str, str] = {
            # common synonyms for convenience (feel free to extend)
            "code": "procedure_code",
            "mã_thủ_tục": "procedure_code",
            "số_quyết_định": "decision_number",
            "năm_quyết_định": "decision_year",
            "trạng_thái_hiệu_lực": "effect_status",
            "cơ_quan_ban_hành": "issuing_authority",
        }

        base.update({
            "allowed_fields": allowed_fields,
            "field_aliases": field_aliases,
        })

        self.filter_config = FilterConfig.from_dict(config_dict=base)
        logger.info("[QdrantFilterProcedure] FilterConfig initialized: %s", self.filter_config)

    # ------------------------------ Public API ----------------------------- #
    def build(self, spec: Union[str, Dict[str, Any]], *, prefer_models: bool = True) -> FilterLike:
        """Validate + normalize an input spec, then return a Qdrant Filter.

        If prefer_models=True and qdrant_client is available, returns
        qdrant_client.http.models.Filter; otherwise returns REST-style dict.
        """
        spec_dict = self._parse_spec(spec)
        spec_norm = self._normalize_spec(spec_dict)

        groups: Dict[str, List[ConditionLike]] = {"must": [], "should": [], "must_not": []}
        for grp in groups.keys():
            for cond in spec_norm.get(grp, []):
                qcond = self._to_qdrant_condition(cond, prefer_models=prefer_models)
                if qcond is not None:
                    groups[grp].append(qcond)

        return self._make_filter(groups, prefer_models=prefer_models)

    def merge(self, *filters: FilterLike, prefer_models: bool = True) -> FilterLike:
        """Merge multiple FilterLike into one (concatenate groups)."""
        if not filters:
            return self._make_filter({}, prefer_models=prefer_models)

        if prefer_models and QFilter is not None:
            merged: Dict[str, List[Any]] = {"must": [], "should": [], "must_not": []}
            for f in filters:
                f_dict = self._to_dict(f)
                for k in merged.keys():
                    merged[k].extend(f_dict.get(k, []))
            return self._make_filter(merged, prefer_models=True)
        else:
            merged_d: Dict[str, List[Any]] = {"must": [], "should": [], "must_not": []}
            for f in filters:
                f_dict = self._to_dict(f)
                for k in merged_d.keys():
                    merged_d[k].extend(f_dict.get(k, []))
            # Drop empty groups
            return {k: v for k, v in merged_d.items() if v}

    def to_dict(self, qdrant_filter: FilterLike) -> Dict[str, Any]:
        """Return a plain dict form for serialization/logging."""
        return self._to_dict(qdrant_filter)

    # ---------------------------- Normalization ---------------------------- #
    def _parse_spec(self, spec: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(spec, str):
            try:
                return json.loads(spec)
            except Exception as e:  # pragma: no cover - defensive
                raise ValueError(f"Spec must be a dict or JSON string: {e}")
        if not isinstance(spec, dict):
            raise TypeError("Spec must be a dict or JSON string")
        return spec

    def _normalize_key(self, key: str) -> str:
        aliases = getattr(self.filter_config, "field_aliases", {}) or {}
        return aliases.get(key, key)

    def _normalize_spec(self, spec: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = {"must": [], "should": [], "must_not": []}
        for grp in ("must", "should", "must_not"):
            items = spec.get(grp) or []
            if isinstance(items, dict):
                items = [items]
            for raw in items:
                if not isinstance(raw, dict) or "key" not in raw:
                    continue
                key = self._normalize_key(raw["key"])  # map alias -> canonical
                op = raw.get("op") or raw.get("operator")
                val = raw.get("value", raw.get("values"))
                if op is None:
                    op = "in" if isinstance(val, (list, tuple, set)) else "eq"
                out[grp].append({"key": key, "op": op, "value": val})
        return out

    # ---------------------------- Condition build -------------------------- #
    def _to_qdrant_condition(self, cond: Dict[str, Any], *, prefer_models: bool) -> ConditionLike:
        key = cond["key"]
        op = (cond.get("op") or "eq").lower()
        value = cond.get("value")
        coerced = self._coerce_value(key, value)

        if op in ("eq", "in", "neq"):
            match: Dict[str, Any]
            if op == "eq" or op == "neq":
                match = {"value": coerced}
            else:  # in
                arr = list(coerced) if isinstance(coerced, (list, tuple, set)) else [coerced]
                match = {"any": arr}
            q = self._make_field_condition(key, match=match, prefer_models=prefer_models)
            # NOTE: for "neq" you should place the condition into must_not group upstream
            return q

        if op in ("gt", "gte", "lt", "lte", "between"):
            rng: Dict[str, Any] = {}
            if op == "between":
                if isinstance(coerced, (list, tuple)) and len(coerced) == 2:
                    rng = {"gte": coerced[0], "lte": coerced[1]}
                else:  # pragma: no cover - forgiving fallback
                    raise ValueError("between expects a pair [lo, hi]")
            else:
                rng[op] = coerced
            return self._make_field_condition(key, range=rng, prefer_models=prefer_models)

        if op in ("exists", "missing"):
            is_empty = (op == "missing")
            return self._make_is_empty_condition(key, is_empty=is_empty, prefer_models=prefer_models)

        # Fallback: treat as equality
        return self._make_field_condition(key, match={"value": coerced}, prefer_models=prefer_models)

    # ------------------------------- Coercion ------------------------------ #
    def _coerce_value(self, key: str, value: Any) -> Any:
        schema: Dict[str, str] = getattr(self.filter_config, "allowed_fields", {}) or {}
        typ = schema.get(key, "str")
        if typ == "int":
            if isinstance(value, (list, tuple, set)):
                return [int(x) for x in value]
            return int(value)
        if typ == "float":
            if isinstance(value, (list, tuple, set)):
                return [float(x) for x in value]
            return float(value)
        if typ == "bool":
            if isinstance(value, (list, tuple, set)):
                return [self._to_bool(x) for x in value]
            return self._to_bool(value)
        if typ == "list[str]":
            if isinstance(value, (list, tuple, set)):
                return [str(x) for x in value]
            return [str(value)]
        # "date" -> pass-through (assume you stored comparable strings or timestamps)
        return value

    @staticmethod
    def _to_bool(x: Any) -> bool:
        if isinstance(x, bool):
            return x
        s = str(x).strip().lower()
        return s in {"1", "true", "t", "yes", "y", "on"}

    # ------------------------- Qdrant model/dict makers -------------------- #
    def _make_field_condition(
        self,
        key: str,
        *,
        match: Optional[Dict[str, Any]] = None,
        range: Optional[Dict[str, Any]] = None,
        prefer_models: bool = True,
    ) -> ConditionLike:
        if prefer_models and QFieldCondition is not None:
            if match is not None:
                if "any" in match and QMatchAny is not None:
                    return QFieldCondition(key=key, match=QMatchAny(any=match["any"]))
                if "value" in match and QMatchValue is not None:
                    return QFieldCondition(key=key, match=QMatchValue(value=match["value"]))
            if range is not None and QRange is not None:
                return QFieldCondition(key=key, range=QRange(**range))
        # Fallback dict (REST)
        d: Dict[str, Any] = {"key": key}
        if match is not None:
            d["match"] = match
        if range is not None:
            d["range"] = range
        return d

    def _make_is_empty_condition(
        self,
        key: str,
        *,
        is_empty: bool,
        prefer_models: bool = True,
    ) -> ConditionLike:
        if prefer_models and QIsEmptyCondition is not None:
            return QIsEmptyCondition(is_empty=is_empty, key=key)
        return {"is_empty": {"key": key, "is_empty": is_empty}}

    def _make_filter(self, groups: Dict[str, List[ConditionLike]] | Dict[str, List[dict]], *, prefer_models: bool) -> FilterLike:
        # Remove any empty group for cleanliness
        cleaned = {k: v for k, v in groups.items() if v}
        if prefer_models and QFilter is not None:
            return QFilter(
                must=cleaned.get("must"),
                should=cleaned.get("should"),
                must_not=cleaned.get("must_not"),
            )
        return cleaned

    # ------------------------- Converters / Utilities ---------------------- #
    @staticmethod
    def _cond_to_dict(c: Any) -> Dict[str, Any]:
        if isinstance(c, dict):
            return c
        out: Dict[str, Any] = {}
        key = getattr(c, "key", None)
        if key is not None:
            out["key"] = key
        match = getattr(c, "match", None)
        if match is not None:
            if hasattr(match, "value"):
                out["match"] = {"value": match.value}
            elif hasattr(match, "any"):
                out["match"] = {"any": list(match.any)}
        r = getattr(c, "range", None)
        if r is not None:
            rng: Dict[str, Any] = {}
            for k in ("gt", "gte", "lt", "lte"):
                v = getattr(r, k, None)
                if v is not None:
                    rng[k] = v
            if rng:
                out["range"] = rng
        is_empty = getattr(c, "is_empty", None)
        if is_empty is not None:
            out["is_empty"] = {"key": key, "is_empty": is_empty}
        return out

    @classmethod
    def _to_dict(cls, f: FilterLike) -> Dict[str, Any]:
        if isinstance(f, dict):
            return f
        d: Dict[str, Any] = {}
        for grp in ("must", "should", "must_not"):
            v = getattr(f, grp, None)
            if v:
                d[grp] = [cls._cond_to_dict(c) for c in v]
        return d

    # Convenience helpers
    def eq(self, key: str, value: Any, *, prefer_models: bool = True) -> FilterLike:
        return self.build({"must": [{"key": key, "op": "eq", "value": value}]}, prefer_models=prefer_models)

    def anyof(self, key: str, values: Iterable[Any], *, prefer_models: bool = True) -> FilterLike:
        return self.build({"must": [{"key": key, "op": "in", "value": list(values)}]}, prefer_models=prefer_models)

    def between(self, key: str, lo: Any, hi: Any, *, prefer_models: bool = True) -> FilterLike:
        return self.build({"must": [{"key": key, "op": "between", "value": [lo, hi]}]}, prefer_models=prefer_models)
