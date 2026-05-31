# Real Data Schema Map

This document is the handoff checklist for mapping one real FU13 export into the B08 canonical observation schema.

## Canonical Columns

| Canonical column | Meaning |
| --- | --- |
| `timestamp` | measurement timestamp with timezone policy documented |
| `device_id` | equipment identity, for example `FU13` |
| `batch_id` | production batch or reconstructed batch boundary |
| `stage` | mapped process stage such as `抽真空` or `冷却` |
| `sensor_id` | normalized sensor tag |
| `value` | numeric sensor value |
| `unit` | engineering unit |
| `domain` | physical domain |
| `quality_flag` | good, missing, invalid, maintenance, or another documented state |
| `degradation_label` | weak degradation label, default `normal` |
| `failure_proxy` | boolean weak failure proxy |

## Template

Use `configs/real_data_schema_map.template.yaml` as the starting point.

Run:

```bash
.venv/bin/b08-model-core real-data validate \
  --input path/to/real_export.csv \
  --schema-map configs/real_data_schema_map.template.yaml \
  --output reports/real_data_validation.md
```

## Review Checklist

- Every real sensor tag is mapped to `sensor_id`, `unit`, and `domain`.
- For wide-format exports, every configured sensor column is present or explicitly removed from the schema map.
- Stage names are mapped to the simulated stage vocabulary or documented as extensions.
- Missingness and invalid values are represented in `quality_flag`.
- Batch identity is explicit or reconstructable.
- Maintenance and alarm records are linked as weak labels when available.
