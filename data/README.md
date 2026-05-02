# KBO to MLB Transition Dataset

`transitions.csv` is the canonical calibration seed for KBO-to-MLB translations.
Each row pairs one pre-MLB KBO season with the player's first MLB season after
the move.

The initial seed intentionally favors rows that can be checked from a single
public stat page. Most rows use Baseball-Reference register pages because those
pages include KBO, minor league, and MLB seasons in one table. `source_note`
calls out exceptions and rows that need special handling.

## Column Conventions

- `transition_age` is the player's age during the MLB season.
- `transition_path` is `KBO_MLB` for direct moves and flags indirect cases such
  as `KBO_NPB_MLB`.
- Rate stats use decimal form: `.1206` means `12.06%`.
- Hitter `k_rate` and `bb_rate` are calculated as `SO / PA` and `BB / PA`.
- Pitcher innings use baseball notation from the source page, so `182.2` means
  182 and 2/3 innings, not 182.2 decimal innings.
- Blank fields mean the stat does not apply or was not collected for that row.

## Growth Rules

Add rows only when the KBO and MLB seasons are sourceable. Prefer:

1. The final full KBO season before MLB.
2. The first MLB regular season after signing.
3. One row per player for baseline calibration.

Later validation can add derived views for best-three-year MLB outcome, per-600
PA hitter rates, and per-150/per-60 IP pitcher rates without changing this raw
source table.
