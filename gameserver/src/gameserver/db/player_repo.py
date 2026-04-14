"""Player and character data access layer (PostgreSQL)."""

from __future__ import annotations

import uuid
import bcrypt
import asyncpg

from gameserver.db.postgres import get_pg


async def create_player(username: str, display_name: str, password: str) -> tuple[str, str]:
    """Create a new player. Returns (player_id, token).

    Raises ValueError if username already exists.
    """
    pool = get_pg()
    player_id = str(uuid.uuid4())
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    token = uuid.uuid4().hex + uuid.uuid4().hex  # 64-char hex token

    try:
        await pool.execute(
            """INSERT INTO players (id, username, display_name, password_hash)
               VALUES ($1, $2, $3, $4)""",
            uuid.UUID(player_id), username, display_name, password_hash,
        )
    except asyncpg.UniqueViolationError:
        raise ValueError(f"Username '{username}' already exists")

    return player_id, token


async def authenticate_player(username: str, password: str) -> tuple[str, str]:
    """Authenticate a player. Returns (player_id, token).

    Raises ValueError if credentials are invalid.
    """
    pool = get_pg()
    row = await pool.fetchrow(
        "SELECT id, password_hash FROM players WHERE username = $1 AND is_active = true",
        username,
    )
    if row is None:
        raise ValueError("Invalid username or password")

    if not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        raise ValueError("Invalid username or password")

    token = uuid.uuid4().hex + uuid.uuid4().hex
    await pool.execute(
        "UPDATE players SET last_login_at = now() WHERE id = $1", row["id"],
    )
    return str(row["id"]), token


async def create_character(
    player_id: str, name: str,
    str_: int, agi: int, vit: int, int_: int, dex: int, luk: int,
) -> str:
    """Create a character for a player. Returns character_id.

    Validates stat allocation: all base 10 + 10 free points.
    Raises ValueError on invalid stats or if character already exists.
    """
    total_bonus = (str_ - 10) + (agi - 10) + (vit - 10) + (int_ - 10) + (dex - 10) + (luk - 10)
    if total_bonus != 10:
        raise ValueError(f"Stat allocation must use exactly 10 bonus points, got {total_bonus}")
    for stat_name, val in [("STR", str_), ("AGI", agi), ("VIT", vit), ("INT", int_), ("DEX", dex), ("LUK", luk)]:
        if val < 1 or val > 30:
            raise ValueError(f"{stat_name} must be between 1 and 30, got {val}")

    pool = get_pg()
    pid = uuid.UUID(player_id)

    existing = await pool.fetchval(
        "SELECT id FROM player_characters WHERE player_id = $1", pid,
    )
    if existing:
        raise ValueError("Player already has a character")

    max_hp = 200 + 1 * 50 + vit * 10  # Level 1
    char_id = str(uuid.uuid4())
    await pool.execute(
        """INSERT INTO player_characters
           (id, player_id, name, max_hp, current_hp,
            stat_str, stat_agi, stat_vit, stat_int, stat_dex, stat_luk)
           VALUES ($1, $2, $3, $4, $4, $5, $6, $7, $8, $9, $10)""",
        uuid.UUID(char_id), pid, name, max_hp,
        str_, agi, vit, int_, dex, luk,
    )

    # Grant starting sword skills based on initial gear concept
    starter_skills = ["sword_slant", "rapier_linear"]
    for skill_id in starter_skills:
        await pool.execute(
            """INSERT INTO character_sword_skills (character_id, skill_def_id, is_in_slot, slot_index)
               VALUES ($1, $2, true, $3)
               ON CONFLICT DO NOTHING""",
            uuid.UUID(char_id), skill_id, starter_skills.index(skill_id),
        )

    # Grant starting items
    starter_items = [
        ("sword_anneal_blade", True, "main_hand"),
        ("armor_midnight_coat", True, "body"),
        ("potion_heal_low", False, None),
    ]
    for item_id, equipped, slot in starter_items:
        item_def = await pool.fetchrow("SELECT * FROM item_definitions WHERE id = $1", item_id)
        if item_def:
            await pool.execute(
                """INSERT INTO character_inventory
                   (character_id, item_def_id, quantity, current_durability, is_equipped, equipped_slot)
                   VALUES ($1, $2, $3, $4, $5, $6)""",
                uuid.UUID(char_id), item_id,
                5 if item_id == "potion_heal_low" else 1,
                item_def["weapon_durability"],
                equipped, slot,
            )

    return char_id


async def get_character(player_id: str) -> dict | None:
    """Get the full character record for a player."""
    pool = get_pg()
    row = await pool.fetchrow(
        "SELECT * FROM player_characters WHERE player_id = $1",
        uuid.UUID(player_id),
    )
    return dict(row) if row else None


async def update_character(player_id: str, **updates) -> None:
    """Update character fields."""
    if not updates:
        return
    pool = get_pg()
    # Allowlist of valid column names to prevent SQL injection
    valid_columns = {
        "name", "max_hp", "current_hp", "stat_str", "stat_agi", "stat_vit",
        "stat_int", "stat_dex", "stat_luk", "level", "experience", "exp_to_next",
        "stat_points_available", "col", "current_floor", "current_area", "current_location",
    }
    # Filter and validate field names
    filtered_updates = {k: v for k, v in updates.items() if k in valid_columns}
    if not filtered_updates:
        return
    sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(filtered_updates))
    query = f"UPDATE player_characters SET {sets}, updated_at = now() WHERE player_id = $1"
    await pool.execute(query, uuid.UUID(player_id), *filtered_updates.values())
