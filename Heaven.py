"""
PROJECT GHURUR — THE HEAVENLY SYSTEM v4
OWO-style embeds: single description block, emojis inline via bold text outside code fences.
MongoDB Atlas. Guild sync. Accept/Reject duel. Deferred slow commands.
"""

import discord
from discord import app_commands
from discord.ext import commands
from pymongo import MongoClient
import random
import asyncio
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Heavenly Dao is Online"

def run():
    # Render provides a PORT environment variable automatically
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()


load_dotenv()
# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
BOT_TOKEN  =os.getenv('BOT_TOKEN')
MONGO_URI  =os.getenv('MONGO_URI')
OWNER_NAME = "tenkariel."
YOUR_GUILD_ID = 1491530689152024637  

# ─────────────────────────────────────────────
# MONGODB
# ─────────────────────────────────────────────
mongo_client = MongoClient(MONGO_URI)
mdb          = mongo_client["ghurur"]
cultivators  = mdb["cultivators"]
server_config = mdb["server_config"]
sects = mdb["sects"]

# ─────────────────────────────────────────────
# EMOJIS
# ─────────────────────────────────────────────
E = {
    "mortal":           "<:rank_mortal:1503023258239242350>",
    "qi_condensation":  "<:rank_qi_condensation:1503023209849815112>",
    "foundation":       "<:rank_foundation:1503023230057709568>",
    "core":             "<:rank_core:1503025178286755840>",
    "nascent":          "<:rank_nascent:1503025157126623322>",
    "spirit_severing":  "<:rank_spirit_severing:1503026026723151892>",
    "dao_seeking":      "<:rank_dao_seeking:1503026879467098242>",
    "dao_realm":        "<:rank_dao_realm:1503028428612305038>",
    "immortal":         "<:rank_immortal_ascendant:1503028496765550694>",
    "qi_orb":           "<:qi_orb:1503018390174826506>",
    "soul_coin":        "<:soul_coin:1503018307769602180>",
    "sword_clash":      "<:sword_clash:1503019828372443186>",
    "flame":            "<:breakthrough_flame:1503019738291376291>",
    "talisman":         "<:iron_talisman:1503019615415042212>",
    "scroll":           "<:dao_scroll:1502989548806733934>",
    "aperture":         "<:aperture_symbol:1502991256068948088>",
    "skull":            "<:skull_death:1503017153085968514>",
    "sect":             "<:sect_emblem:1503017383621689434>",
}

RANK_EMOJI = {
    "Mortal":                   E["mortal"],
    "Qi Condensation":          E["qi_condensation"],
    "Foundation Establishment": E["foundation"],
    "Core Formation":           E["core"],
    "Nascent Soul":             E["nascent"],
    "Spirit Severing":          E["spirit_severing"],
    "Dao Seeking":              E["dao_seeking"],
    "Dao Realm":                E["dao_realm"],
    "Immortal Ascendant":       E["immortal"],
}

# ─────────────────────────────────────────────
# RANKS
# ─────────────────────────────────────────────
RANKS = [
    {"name": "Mortal",                   "qi_required": 0,          "aperture": 500},
    {"name": "Qi Condensation",          "qi_required": 1_000,      "aperture": 2_000},
    {"name": "Foundation Establishment", "qi_required": 5_000,      "aperture": 8_000},
    {"name": "Core Formation",           "qi_required": 15_000,     "aperture": 25_000},
    {"name": "Nascent Soul",             "qi_required": 50_000,     "aperture": 80_000},
    {"name": "Spirit Severing",          "qi_required": 120_000,    "aperture": 180_000},
    {"name": "Dao Seeking",              "qi_required": 250_000,    "aperture": 350_000},
    {"name": "Dao Realm",               "qi_required": 500_000,    "aperture": 750_000},
    {"name": "Immortal Ascendant",       "qi_required": 1_000_000,  "aperture": 999_999_999},
]

def get_rank_data(qi: int) -> dict:
    current = RANKS[0]
    for rank in RANKS:
        if qi >= rank["qi_required"]:
            current = rank
    return current

def get_next_rank(rank_name: str):
    for i, r in enumerate(RANKS):
        if r["name"] == rank_name:
            return RANKS[i + 1] if i + 1 < len(RANKS) else None
    return None

def get_rank_index(rank_name: str) -> int:
    for i, rank in enumerate(RANKS):
        if rank["name"] == rank_name:
            return i
    return 0

# ─────────────────────────────────────────────
# INGREDIENTS
# ─────────────────────────────────────────────
GATHER_INGREDIENTS = [
    {"id": "spirit_herb",  "name": "Spirit Herb",         "tier": "Common", "weight": 50},
    {"id": "iron_ore",     "name": "Iron Ore",            "tier": "Common", "weight": 50},
    {"id": "beast_core",   "name": "Beast Core",          "tier": "Common", "weight": 40},
    {"id": "moonstone",    "name": "Moonstone",           "tier": "Rare",   "weight": 15},
    {"id": "dragon_vein",  "name": "Dragon Vein Crystal", "tier": "Rare",   "weight": 10},
    {"id": "void_silk",    "name": "Void Silk",           "tier": "Mystic", "weight": 3},
]

MEDITATE_INGREDIENTS = [
    {"id": "heaven_dew",   "name": "Heaven Dew",   "tier": "Rare",   "weight": 10},
    {"id": "dao_fragment", "name": "Dao Fragment", "tier": "Mystic", "weight": 4},
    {"id": "soul_essence", "name": "Soul Essence", "tier": "Mystic", "weight": 3},
    {"id": "qi_crystal",   "name": "Qi Crystal",   "tier": "Rare",   "weight": 12},
]

ALL_INGREDIENTS = {i["id"]: i for i in GATHER_INGREDIENTS + MEDITATE_INGREDIENTS}

def weighted_drop(pool: list):
    total   = sum(i["weight"] for i in pool)
    roll    = random.randint(1, total)
    running = 0
    for item in pool:
        running += item["weight"]
        if roll <= running:
            return item
    return None

# ─────────────────────────────────────────────
# RECIPES
# ─────────────────────────────────────────────
RECIPES = {
    "qi_pill": {
        "name": "Qi Condensation Pill", "type": "pill",
        "ingredients": {"spirit_herb": 3, "qi_crystal": 1},
        "effect": {"qi": 500},
        "description": "Grants +500 Qi upon consumption.",
    },
    "healing_pill": {
        "name": "Meridian Healing Pill", "type": "pill",
        "ingredients": {"spirit_herb": 2, "heaven_dew": 1},
        "effect": {"clear_injury": True},
        "description": "Clears injury state immediately.",
    },
    "breakthrough_pill": {
        "name": "Heaven Defying Pill", "type": "pill",
        "ingredients": {"dao_fragment": 1, "heaven_dew": 2, "beast_core": 2},
        "effect": {"breakthrough_bonus": 30},
        "description": "Reduces breakthrough failure chance by 30%.",
    },
    "iron_talisman": {
        "name": "Iron Body Talisman", "type": "talisman",
        "ingredients": {"iron_ore": 4, "beast_core": 1},
        "effect": {"iron_body": True},
        "description": "Absorbs next duel defeat. Qi will not shatter.",
    },
    "soul_talisman": {
        "name": "Soul Ward Talisman", "type": "talisman",
        "ingredients": {"soul_essence": 1, "void_silk": 1},
        "effect": {"soul_ward": True},
        "description": "Next duel victory yields +20% Souls.",
    },
    "iron_sword": {
        "name": "Iron Dao Sword", "type": "artifact",
        "ingredients": {"iron_ore": 5, "moonstone": 1},
        "effect": {"combat_bonus": 10},
        "description": "Equippable. +10% combat power in duels.",
    },
    "void_blade": {
        "name": "Void Severing Blade", "type": "artifact",
        "ingredients": {"void_silk": 2, "dragon_vein": 1, "moonstone": 2},
        "effect": {"combat_bonus": 25},
        "description": "Equippable. +25% combat power in duels.",
    },
}

# ─────────────────────────────────────────────
# SHOP
# ─────────────────────────────────────────────
SHOP_ITEMS = {
    "gather_boost": {
        "name": "Gatherer's Compass", "cost": 200,
        "effect": "gather_boost",
        "description": "Next /gather yields double ingredients.",
    },
    "luck_charm": {
        "name": "Fortune Jade", "cost": 500,
        "effect": "luck_boost", "value": 5,
        "description": "+5 Luck for 24 hours.",
    },
    "soul_lantern": {
        "name": "Soul Lantern", "cost": 300,
        "effect": "souls", "value": 400,
        "description": "Grants 400 Souls directly.",
    },
}

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────
def get_cultivator(user_id: int, username: str) -> dict:
    uid = str(user_id)
    doc = cultivators.find_one({"_id": uid})
    if not doc:
        doc = {
            "_id": uid, "username": username,
            "qi": 0, "rank": "Mortal", "souls": 0, "deaths": 0,
            "luck": random.randint(1, 20),
            "last_meditation": None, "last_gather": None, "last_daily": None,
            "injured_until": None,
            "iron_body": False, "soul_ward": False,
            "gather_boost": False, "breakthrough_pill": False,
            "equipped_artifact": None,
            "inventory": {}, "crafted": {},
            "luck_boost": 0, "luck_boost_until": None,
        }
        cultivators.insert_one(doc)
    return doc

def save_cultivator(doc: dict):
    cultivators.replace_one({"_id": doc["_id"]}, doc, upsert=True)

def get_effective_luck(doc: dict) -> int:
    luck = doc.get("luck", 10)
    if doc.get("luck_boost_until"):
        if datetime.now(timezone.utc).replace(tzinfo=None) < datetime.fromisoformat(doc["luck_boost_until"]):
            luck += doc.get("luck_boost", 0)
    return min(luck, 100)

# ─────────────────────────────────────────────
# BOT SETUP
# ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot  = commands.Bot(command_prefix="!", intents=intents, help_command=None)
tree = bot.tree

# ─────────────────────────────────────────────
# EMBED HELPER
# OWO style: plain description, no code block.
# Emojis render freely. Bold for labels.
# ─────────────────────────────────────────────
def dao_embed(title: str, lines: list, color: int = 0x1a1a2e) -> discord.Embed:
    """
    Single description block. No code fences.
    Emojis render inline. Use bold (**text**) for labels.
    Lines are joined with newlines.
    """
    embed = discord.Embed(
        title=title,
        description="\n".join(lines),
        color=color
    )
    embed.set_footer(text="Heavenly Dao System | Wonderland")
    return embed

async def log_event(bot, title, lines, color):
    config = server_config.find_one({"_id": str(YOUR_GUILD_ID)})
    if not config or not config.get("log_channel"):
        return

    channel_id = int(config["log_channel"])
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            return

    try:
        await channel.send(embed=dao_embed(title, lines, color))
    except (discord.Forbidden, discord.HTTPException):
        return

def denied(reason: str) -> discord.Embed:
    return dao_embed("❌ Access Denied", [f"> {reason}"], color=0x8b0000)

# ─────────────────────────────────────────────
# ON READY — GUILD SYNC
# Clears old global commands to fix duplicates, then guild-syncs for instant update.
# After first successful run, remove the two clear lines.
# ─────────────────────────────────────────────
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user_id = str(message.author.id)
    last_reward = message_reward_cooldowns.get(user_id)
    if last_reward and (now - last_reward).total_seconds() < 120:
        return

    doc = cultivators.find_one({"_id": user_id})
    if not doc:
        doc = get_cultivator(message.author.id, message.author.name)

    luck = doc.get("luck", 0)
    rank_name = doc.get("rank", get_rank_data(doc.get("qi", 0))["name"])
    rank_index = get_rank_index(rank_name)

    current_rank_data = get_rank_data(doc.get("qi", 0))
    aperture_cap = current_rank_data["aperture"]

    base_qi = random.randint(3, 8)
    qi_gain = int((base_qi + (rank_index* 8)) * (1 + (luck / 100)))

    soul_gain = random.randint(3, 8) + (rank_index * 3)

    new_qi = min(doc.get("qi", 0) + qi_gain, aperture_cap)

    cultivators.update_one(
        {"_id": user_id},
        {
            "$set": {
                "username": message.author.name,
                "qi": new_qi,
            },
            "$inc": {"souls": soul_gain},
        },
        upsert=True,
    )
    message_reward_cooldowns[user_id] = now
@bot.event
async def on_ready():
    try:
        guild = discord.Object(id=YOUR_GUILD_ID)

        tree.copy_global_to(guild=guild)
        synced = await tree.sync(guild=guild)
        print(f"[GHURUR] Guild-synced {len(synced)} commands. Global commands cleared.")
    except Exception as e:
        print(f"[GHURUR] Sync error: {e}")
    print(f"[GHURUR] Online as {bot.user}")

# ─────────────────────────────────────────────
# /meditate
# ─────────────────────────────────────────────
@tree.command(name="meditate", description="Absorb ambient Qi. 30-minute cooldown.")
async def meditate(interaction: discord.Interaction):
    doc = get_cultivator(interaction.user.id, interaction.user.name)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if doc["injured_until"]:
        iu = datetime.fromisoformat(doc["injured_until"])
        if now < iu:
            mins = int((iu - now).total_seconds() / 60)
            await interaction.response.send_message(embed=dao_embed("🩸 Meditation Denied", [
                f"**{interaction.user.display_name}** — your meridians are disrupted.",
                f"> Recover in **{mins}m**.",
            ], color=0x8b0000), ephemeral=True)
            return

    if doc["last_meditation"]:
        end = datetime.fromisoformat(doc["last_meditation"]) + timedelta(minutes=30)
        if now < end:
            mins = int((end - now).total_seconds() / 60)
            await interaction.response.send_message(embed=dao_embed("⏳ Meditation Denied", [
                f"> Cooldown active. Return in **{mins}m**.",
            ], color=0x4a4a6a), ephemeral=True)
            return

    rank_data    = get_rank_data(doc["qi"])
    aperture_cap = rank_data["aperture"]
    if doc["qi"] >= aperture_cap:
        await interaction.response.send_message(embed=dao_embed(f"{E['aperture']} Aperture Full", [
            f"**{interaction.user.display_name}** — your aperture cannot hold more Qi.",
            f"> Current: **{doc['qi']:,} / {aperture_cap:,}**",
            "> Use **/breakthrough** to expand it.",
        ], color=0x664400), ephemeral=True)
        return

    luck       = get_effective_luck(doc)
    qi_gain    = random.randint(10, 50) + (luck // 5)
    souls_gain = random.randint(1, 5)
    doc["qi"]  = min(doc["qi"] + qi_gain, aperture_cap)
    doc["souls"] = doc.get("souls", 0) + souls_gain
    doc["rank"]  = get_rank_data(doc["qi"])["name"]
    doc["last_meditation"] = now.isoformat()

    lines = [
        f"{RANK_EMOJI.get(doc['rank'], '')} **{interaction.user.display_name}** meditates.",
        f"",
        f"{E['qi_orb']} Qi gained: **+{qi_gain}**  ›  {doc['qi']:,} / {aperture_cap:,}",
        f"{E['soul_coin']} Souls gained: **+{souls_gain}**",
        f"{RANK_EMOJI.get(doc['rank'], '')} Rank: **{doc['rank']}**",
    ]

    drop_chance = 5 + (luck // 4)
    if random.randint(1, 100) <= drop_chance:
        drop = weighted_drop(MEDITATE_INGREDIENTS)
        if drop:
            inv = doc.get("inventory", {})
            inv[drop["id"]] = inv.get(drop["id"], 0) + 1
            doc["inventory"] = inv
            lines.append(f"")
            lines.append(f"✨ Rare drop: **{drop['name']}** `{drop['tier']}`")

    save_cultivator(doc)
    await interaction.response.send_message(embed=dao_embed("Cultivating Complete", lines, color=0x003366))

# ─────────────────────────────────────────────
# /gather
# ─────────────────────────────────────────────
@tree.command(name="gather", description="Scour the wilds for crafting ingredients. 1-hour cooldown.")
async def gather(interaction: discord.Interaction):
    doc = get_cultivator(interaction.user.id, interaction.user.name)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if doc["last_gather"]:
        end = datetime.fromisoformat(doc["last_gather"]) + timedelta(hours=1)
        if now < end:
            mins = int((end - now).total_seconds() / 60)
            await interaction.response.send_message(embed=dao_embed("⏳ Gather Denied", [
                f"> Already gathered recently. Return in **{mins}m**.",
            ], color=0x4a4a6a), ephemeral=True)
            return

    luck    = get_effective_luck(doc)
    boosted = doc.get("gather_boost", False)
    count   = random.randint(4, 7) if boosted else random.randint(2, 4)
    if random.randint(1, 100) <= (20 + luck):
        count += 1

    inv   = doc.get("inventory", {})
    lines = [f"**{interaction.user.display_name}** scours the wilds...", ""]
    for _ in range(count):
        drop = weighted_drop(GATHER_INGREDIENTS)
        if drop:
            inv[drop["id"]] = inv.get(drop["id"], 0) + 1
            tier_icon = "🔵" if drop["tier"] == "Common" else "🟣" if drop["tier"] == "Rare" else "🌟"
            lines.append(f"{tier_icon} **{drop['name']}** `{drop['tier']}`")

    lines.append("")
    lines.append(f"> Use **/recipes** to see what you can craft.")

    doc["inventory"]    = inv
    doc["last_gather"]  = now.isoformat()
    doc["gather_boost"] = False
    save_cultivator(doc)

    await interaction.response.send_message(embed=dao_embed("🌿 Gathering Complete", lines, color=0x1a3300))

# ─────────────────────────────────────────────
# /inventory
# ─────────────────────────────────────────────
@tree.command(name="inventory", description="View your ingredients and crafted items.")
async def inventory(interaction: discord.Interaction):
    doc     = get_cultivator(interaction.user.id, interaction.user.name)
    inv     = doc.get("inventory", {})
    crafted = doc.get("crafted", {})

    lines = [f"{RANK_EMOJI.get(doc['rank'], '')} **{interaction.user.display_name}'s Inventory**", ""]

    if inv:
        lines.append("**— Ingredients —**")
        for iid, count in inv.items():
            info      = ALL_INGREDIENTS.get(iid, {"name": iid, "tier": "?"})
            tier_icon = "🔵" if info["tier"] == "Common" else "🟣" if info["tier"] == "Rare" else "🌟"
            lines.append(f"{tier_icon} {info['name']} `{info['tier']}` — x**{count}**")
    else:
        lines.append("**— Ingredients —** None.")

    lines.append("")

    if crafted:
        lines.append("**— Crafted Items —**")
        for cid, count in crafted.items():
            recipe   = RECIPES.get(cid, {"name": cid, "type": "?"})
            equipped = " ⚔️ `EQUIPPED`" if doc.get("equipped_artifact") == cid else ""
            lines.append(f"📦 **{recipe['name']}** `{recipe['type']}`{equipped} — x**{count}**")
    else:
        lines.append("**— Crafted Items —** None.")

    await interaction.response.send_message(embed=dao_embed("🎒 Inventory", lines, color=0x1a1a3e))

# ─────────────────────────────────────────────
# /recipes
# ─────────────────────────────────────────────
@tree.command(name="recipes", description="View all available refinement recipes.")
async def recipes(interaction: discord.Interaction):
    await interaction.response.defer()
    lines = [f"{E['scroll']} **Dao Refinement Hall — All Recipes**", ""]
    for rid, recipe in RECIPES.items():
        req = ", ".join([
            f"{ALL_INGREDIENTS.get(k, {}).get('name', k)} x{v}"
            for k, v in recipe["ingredients"].items()
        ])
        icon = "💊" if recipe["type"] == "pill" else "📜" if recipe["type"] == "talisman" else "⚔️"
        lines.append(f"{icon} **{recipe['name']}** `{recipe['type']}`")
        lines.append(f"> {recipe['description']}")
        lines.append(f"> Requires: {req}")
        lines.append(f"> Refine: `/refine item_id:{rid}`")
        lines.append("")
    await interaction.followup.send(embed=dao_embed(f"{E['scroll']} Refinement Recipes", lines, color=0x2a1a0e))

# ─────────────────────────────────────────────
# /refine
# ─────────────────────────────────────────────
@tree.command(name="refine", description="Refine ingredients into pills, talismans, or artifacts.")
@app_commands.describe(item_id="Recipe ID from /recipes.")
async def refine(interaction: discord.Interaction, item_id: str):
    if item_id not in RECIPES:
        await interaction.response.send_message(embed=denied(f"Unknown recipe `{item_id}`. Use **/recipes**."), ephemeral=True)
        return

    recipe  = RECIPES[item_id]
    doc     = get_cultivator(interaction.user.id, interaction.user.name)
    inv     = doc.get("inventory", {})
    missing = []

    for iid, needed in recipe["ingredients"].items():
        have = inv.get(iid, 0)
        if have < needed:
            name = ALL_INGREDIENTS.get(iid, {}).get("name", iid)
            missing.append(f"{name} — need **{needed}**, have **{have}**")

    if missing:
        lines = [f"**{recipe['name']}** — insufficient ingredients.", ""]
        for m in missing:
            lines.append(f"> ❌ {m}")
        await interaction.response.send_message(embed=dao_embed("🔥 Refinement Failed", lines, color=0x8b0000), ephemeral=True)
        return

    for iid, needed in recipe["ingredients"].items():
        inv[iid] -= needed
        if inv[iid] <= 0:
            del inv[iid]

    doc["inventory"] = inv
    crafted          = doc.get("crafted", {})
    crafted[item_id] = crafted.get(item_id, 0) + 1
    doc["crafted"]   = crafted
    save_cultivator(doc)

    icon   = "💊" if recipe["type"] == "pill" else "📜" if recipe["type"] == "talisman" else "⚔️"
    result = "Use **/equip**." if recipe["type"] == "artifact" else f"Use `/use item_id:{item_id}`."
    await interaction.response.send_message(embed=dao_embed("🔥 Refinement Complete", [
        f"{icon} **{recipe['name']}** `{recipe['type']}` crafted.",
        f"> {recipe['description']}",
        f"> {result}",
    ], color=0x006644))

# ─────────────────────────────────────────────
# /use
# ─────────────────────────────────────────────
@tree.command(name="use", description="Consume a crafted pill or talisman.")
@app_commands.describe(item_id="Item ID from /inventory.")
async def use_item(interaction: discord.Interaction, item_id: str):
    if item_id not in RECIPES:
        await interaction.response.send_message(embed=denied("Unknown item."), ephemeral=True)
        return

    recipe = RECIPES[item_id]
    if recipe["type"] == "artifact":
        await interaction.response.send_message(embed=denied("Artifacts cannot be consumed — use **/equip**."), ephemeral=True)
        return

    doc     = get_cultivator(interaction.user.id, interaction.user.name)
    crafted = doc.get("crafted", {})

    if crafted.get(item_id, 0) < 1:
        await interaction.response.send_message(embed=denied(f"You don't have **{recipe['name']}**."), ephemeral=True)
        return

    crafted[item_id] -= 1
    if crafted[item_id] <= 0:
        del crafted[item_id]
    doc["crafted"] = crafted

    effect  = recipe["effect"]
    results = []

    if "qi" in effect:
        cap       = get_rank_data(doc["qi"])["aperture"]
        doc["qi"] = min(doc["qi"] + effect["qi"], cap)
        doc["rank"] = get_rank_data(doc["qi"])["name"]
        results.append(f"{E['qi_orb']} Qi **+{effect['qi']}** → {doc['qi']:,}")
    if effect.get("clear_injury"):
        doc["injured_until"] = None
        results.append("💚 Injury cleared. Meridians restored.")
    if "breakthrough_bonus" in effect:
        doc["breakthrough_pill"] = True
        results.append(f"{E['flame']} Breakthrough failure reduced by **{effect['breakthrough_bonus']}%**.")
    if effect.get("iron_body"):
        doc["iron_body"] = True
        results.append(f"{E['talisman']} Iron Body active. Next defeat absorbed.")
    if effect.get("soul_ward"):
        doc["soul_ward"] = True
        results.append(f"{E['soul_coin']} Soul Ward active. Next victory yields +20% Souls.")

    save_cultivator(doc)
    await interaction.response.send_message(embed=dao_embed("💊 Item Consumed", [
        f"**{recipe['name']}** consumed.",
        "",
    ] + results, color=0x004466))

# ─────────────────────────────────────────────
# /equip
# ─────────────────────────────────────────────
@tree.command(name="equip", description="Equip a crafted artifact.")
@app_commands.describe(item_id="Artifact ID from /inventory.")
async def equip(interaction: discord.Interaction, item_id: str):
    if item_id not in RECIPES or RECIPES[item_id]["type"] != "artifact":
        await interaction.response.send_message(embed=denied("That is not an artifact."), ephemeral=True)
        return

    doc = get_cultivator(interaction.user.id, interaction.user.name)
    if doc.get("crafted", {}).get(item_id, 0) < 1:
        await interaction.response.send_message(embed=denied(f"You don't have **{RECIPES[item_id]['name']}**."), ephemeral=True)
        return

    doc["equipped_artifact"] = item_id
    save_cultivator(doc)
    await interaction.response.send_message(embed=dao_embed("⚔️ Artifact Equipped", [
        f"⚔️ **{RECIPES[item_id]['name']}** equipped.",
        f"> {RECIPES[item_id]['description']}",
        "> Combat bonus is now active.",
    ], color=0x003355))

# ─────────────────────────────────────────────
# COMBAT
# Attack > Defend > Technique > Attack
# ─────────────────────────────────────────────
STANCES = ["Attack", "Defend", "Technique"]

STANCE_FLAVOR = {
    "Attack":    "unleashes a ferocious strike",
    "Defend":    "assumes an iron defensive stance",
    "Technique": "channels a devastating technique",
}

STANCE_WINS = {
    "Attack":    "Defend",
    "Technique": "Attack",
    "Defend":    "Technique",
}

def resolve_round(a: str, b: str) -> str:
    if a == b:
        return "draw"
    return "a" if STANCE_WINS[a] == b else "b"

def get_combat_power(doc: dict) -> float:
    luck  = get_effective_luck(doc)
    base  = doc["qi"] * (1 + luck / 200)
    art   = doc.get("equipped_artifact")
    if art and art in RECIPES:
        base *= (1 + RECIPES[art]["effect"].get("combat_bonus", 0) / 100)
    return base

# Active duel registry
active_duels: dict = {}

# Message reward cooldowns
message_reward_cooldowns: dict[int, datetime] = {}

# ─────────────────────────────────────────────
# DUEL VIEWS
# ─────────────────────────────────────────────
class DuelChallengeView(discord.ui.View):
    """Public accept/reject buttons. Only the challenged player can click."""
    def __init__(self, challenger: discord.Member, opponent: discord.Member):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent   = opponent
        self.accepted   = None  # True = accepted, False = rejected, None = timeout

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "This challenge is not yours to answer.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="⚔️ Accept", style=discord.ButtonStyle.danger)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.accepted = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            embed=dao_embed(f"{E['sword']} Duel Accepted", [
                f"{RANK_EMOJI.get(self.challenger.display_name, '')} **{self.challenger.display_name}** vs {RANK_EMOJI.get(self.opponent.display_name, '')} **{self.opponent.display_name}**",
                "",
                "> The heavens bear witness. Choose your stances.",
                "> ⚠️ You have **30 seconds**. Hesitation yields defeat.",
            ], color=0x660000),
            view=self
        )
        self.stop()

    @discord.ui.button(label="🚫 Reject", style=discord.ButtonStyle.secondary)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.accepted = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            embed=dao_embed("🚫 Duel Rejected", [
                f"**{self.opponent.display_name}** refuses the challenge.",
                f"> The Dao records this. **{self.challenger.display_name}** stands uncontested.",
            ], color=0x4a4a6a),
            view=self
        )
        self.stop()


class StanceView(discord.ui.View):
    """Ephemeral stance buttons sent to each duelist separately."""
    def __init__(self, duel_id: str, role: str):
        super().__init__(timeout=30)
        self.duel_id = duel_id
        self.role    = role  # "c" or "t"

    async def _lock(self, interaction: discord.Interaction, stance: str):
        duel = active_duels.get(self.duel_id)
        if not duel:
            await interaction.response.send_message("Duel expired.", ephemeral=True)
            self.stop()
            return
        duel[self.role] = stance
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"Stance locked: **{stance}** — awaiting opponent...",
            view=self
        )
        self.stop()
        if duel["c"] and duel["t"]:
            duel["event"].set()

    @discord.ui.button(label="⚔️ Attack",    style=discord.ButtonStyle.danger)
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._lock(interaction, "Attack")

    @discord.ui.button(label="🛡️ Defend",    style=discord.ButtonStyle.primary)
    async def defend(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._lock(interaction, "Defend")

    @discord.ui.button(label="✨ Technique", style=discord.ButtonStyle.success)
    async def technique(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._lock(interaction, "Technique")

# ─────────────────────────────────────────────
# /duel
# ─────────────────────────────────────────────
@tree.command(name="duel", description="Challenge a cultivator to a true duel.")
@app_commands.describe(opponent="The cultivator you wish to challenge.")
async def duel(interaction: discord.Interaction, opponent: discord.Member):
    if opponent.id == interaction.user.id:
        await interaction.response.send_message(embed=denied("Self-destruction is not permitted."), ephemeral=True)
        return
    if opponent.bot:
        await interaction.response.send_message(embed=denied("Machines do not cultivate."), ephemeral=True)
        return

    c_doc = get_cultivator(interaction.user.id, interaction.user.name)
    t_doc = get_cultivator(opponent.id, opponent.name)
    c_re  = RANK_EMOJI.get(c_doc["rank"], "")
    t_re  = RANK_EMOJI.get(t_doc["rank"], "")

    # Step 1 — Public challenge with Accept / Reject
    challenge_view = DuelChallengeView(interaction.user, opponent)
    await interaction.response.send_message(
        content=f"{opponent.mention} — you have been challenged.",
        embed=dao_embed(f"{E['sword']} Duel Challenge", [
            f"{c_re} **{interaction.user.display_name}** challenges {t_re} **{opponent.display_name}**",
            "",
            f"> {c_re} Challenger Qi: **{c_doc['qi']:,}**",
            f"> {t_re} Opponent Qi:   **{t_doc['qi']:,}**",
            "",
            "> Accept or reject within **60 seconds**.",
        ], color=0x440000),
        view=challenge_view
    )

    await challenge_view.wait()

    # Timeout
    if challenge_view.accepted is None:
        await interaction.followup.send(embed=dao_embed("💨 Duel Expired", [
            f"> **{opponent.display_name}** did not respond. The challenge dissolves.",
        ], color=0x2a2a2a))
        return

    # Rejected — message already shown in the view
    if not challenge_view.accepted:
        return

    # Step 2 — Accepted: send ephemeral stance pickers
    duel_id = f"{interaction.user.id}-{opponent.id}-{int(datetime.now(timezone.utc).replace(tzinfo=None).timestamp())}"
    event   = asyncio.Event()
    active_duels[duel_id] = {"c": None, "t": None, "event": event}

    c_view = StanceView(duel_id, "c")
    t_view = StanceView(duel_id, "t")

    await interaction.followup.send(
        content=f"{interaction.user.mention} — choose your stance:",
        embed=dao_embed("⚔️ Choose Your Stance", [
            f"> **Attack** beats Defend",
            f"> **Technique** beats Attack",
            f"> **Defend** beats Technique",
        ], color=0x330000),
        view=c_view,
        ephemeral=True
    )
    await interaction.followup.send(
        content=f"{opponent.mention} — choose your stance:",
        embed=dao_embed("⚔️ Choose Your Stance", [
            f"> **Attack** beats Defend",
            f"> **Technique** beats Attack",
            f"> **Defend** beats Technique",
        ], color=0x330000),
        view=t_view,
        ephemeral=True
    )

    # Step 3 — Wait for both or timeout (30s)
    try:
        await asyncio.wait_for(event.wait(), timeout=30)
    except asyncio.TimeoutError:
        pass

    duel_data = active_duels.pop(duel_id, {})
    c_stance  = duel_data.get("c") or random.choice(STANCES)
    t_stance  = duel_data.get("t") or random.choice(STANCES)

    # Step 4 — Resolve
    result  = resolve_round(c_stance, t_stance)
    c_name  = interaction.user.display_name
    t_name  = opponent.display_name
    c_power = get_combat_power(c_doc)
    t_power = get_combat_power(t_doc)

    narration = [
        f"{c_re} **{c_name}** {STANCE_FLAVOR[c_stance]}.",
        f"{t_re} **{t_name}** {STANCE_FLAVOR[t_stance]}.",
        "",
    ]

    if result == "draw":
        result = "a" if c_power >= t_power else "b"
        narration.append("> Equal stances — the stronger foundation prevails.")

    if result == "a":
        winner_doc, loser_doc   = c_doc, t_doc
        winner_name, loser_name = c_name, t_name
        w_re, l_re              = c_re, t_re
    else:
        winner_doc, loser_doc   = t_doc, c_doc
        winner_name, loser_name = t_name, c_name
        w_re, l_re              = t_re, c_re

    narration.append(f"🏆 **Victor: {winner_name}**")

    # Iron Body
    if loser_doc.get("iron_body"):
        loser_doc["iron_body"] = False
        narration += [
            "",
            f"{E['talisman']} **{loser_name}**'s Iron Body Talisman shatters.",
            "> Qi loss negated. Defeat recorded, foundation preserved.",
        ]
        save_cultivator(winner_doc)
        save_cultivator(loser_doc)
        await interaction.followup.send(embed=dao_embed(f"{E['sword']} Duel Concluded", narration, color=0x886600))
        return

    spoils       = int(loser_doc["qi"] * 0.20)
    spoils_souls = int(spoils * 1.20) if winner_doc.get("soul_ward") else spoils
    if winner_doc.get("soul_ward"):
        winner_doc["soul_ward"] = False

    sect_tithe = 0
    winner_sect = sects.find_one({"members": winner_doc["_id"]})
    if winner_sect:
        sect_tithe = int(spoils_souls * 0.10)
        if sect_tithe > 0:
            sects.update_one({"_id": winner_sect["_id"]}, {"$inc": {"vault": sect_tithe}})

    winner_doc["qi"]   += spoils
    winner_doc["souls"] = winner_doc.get("souls", 0) + spoils_souls - sect_tithe
    winner_doc["rank"]  = get_rank_data(winner_doc["qi"])["name"]

    loser_floor         = get_rank_data(loser_doc["qi"])["qi_required"]
    loser_doc["qi"]     = loser_floor
    loser_doc["deaths"] = loser_doc.get("deaths", 0) + 1
    loser_doc["rank"]   = get_rank_data(loser_doc["qi"])["name"]

    save_cultivator(winner_doc)
    save_cultivator(loser_doc)

    narration += [
        "",
        f"{E['qi_orb']} Qi seized: **{spoils:,}**",
        f"{E['soul_coin']} Souls gained: **{spoils_souls - sect_tithe:,}**",
        f"{E['skull']} **{loser_name}** — Qi shattered. Returned to rank floor.",
        f"> Deaths: **{loser_doc['deaths']}**",
    ]
    if sect_tithe > 0 and winner_sect:
        narration.append(f"> {E['soul_coin']} Sect vault tithe: **{sect_tithe:,}** Souls to **{winner_sect['name']}**.")

    await interaction.followup.send(embed=dao_embed(f"{E['sword']} Duel Concluded", narration, color=0x660000))

# ─────────────────────────────────────────────
# /breakthrough
# ─────────────────────────────────────────────
@tree.command(name="breakthrough", description="Attempt to break through to the next rank.")
async def breakthrough(interaction: discord.Interaction):
    doc = get_cultivator(interaction.user.id, interaction.user.name)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    current = get_rank_data(doc["qi"])
    nxt     = get_next_rank(current["name"])

    if nxt is None:
        await interaction.response.send_message(embed=dao_embed("👑 Peak Reached", [
            f"{RANK_EMOJI.get(doc['rank'], '')} **{interaction.user.display_name}** — you stand at the peak of existence.",
            "> The Dao offers no further paths.",
        ], color=0xffd700))
        return

    if doc["qi"] < nxt["qi_required"]:
        needed = nxt["qi_required"] - doc["qi"]
        await interaction.response.send_message(embed=dao_embed(f"{E['flame']} Breakthrough Denied", [
            f"> Target: **{nxt['name']}**",
            f"> Qi deficit: **{needed:,}** more needed.",
            "> Foundation insufficient.",
        ], color=0x4a4a6a), ephemeral=True)
        return

    if doc["injured_until"]:
        iu = datetime.fromisoformat(doc["injured_until"])
        if now < iu:
            mins = int((iu - now).total_seconds() / 60)
            await interaction.response.send_message(embed=dao_embed("🩸 Breakthrough Denied", [
                f"> Meridians damaged. Recover in **{mins}m**.",
            ], color=0x8b0000), ephemeral=True)
            return

    luck        = get_effective_luck(doc)
    fail_chance = 40
    if doc.get("breakthrough_pill"):
        fail_chance -= 30
        doc["breakthrough_pill"] = False
    fail_chance = max(fail_chance - (luck // 10), 5)

    if random.randint(1, 100) <= fail_chance:
        loss      = nxt["qi_required"] // 2
        doc["qi"] = max(doc["qi"] - loss, current["qi_required"])
        doc["injured_until"] = (now + timedelta(hours=3)).isoformat()
        save_cultivator(doc)
        await interaction.response.send_message(embed=dao_embed(f"{E['flame']} Breakthrough Failed", [
            f"**{interaction.user.display_name}** — the heavens reject you.",
            "",
            f"> {E['qi_orb']} Qi lost: **{loss:,}**",
            "> Cultivation base damaged.",
            "> Stagnation: **3 hours**.",
        ], color=0x8b0000))
    else:
        doc["rank"] = nxt["name"]
        save_cultivator(doc)
        await interaction.response.send_message(embed=dao_embed(f"{E['flame']} Breakthrough!", [
            f"**{interaction.user.display_name}** — the Dao acknowledges your foundation.",
            "",
            f"{RANK_EMOJI.get(nxt['name'], '')} New rank: **{nxt['name']}**",
            f"{E['aperture']} Aperture expanded to **{nxt['aperture']:,}** Qi.",
            "> The heavens tremble.",
        ], color=0x00aaff))

# ─────────────────────────────────────────────
# /status
# ─────────────────────────────────────────────
@tree.command(name="status", description="View your cultivation dossier.")
@app_commands.describe(member="View another cultivator's status (optional).")
async def status(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    doc    = get_cultivator(target.id, target.name)

    current = get_rank_data(doc["qi"])
    nxt     = get_next_rank(current["name"])
    luck    = get_effective_luck(doc)
    re      = RANK_EMOJI.get(doc["rank"], "")

    if nxt:
        floor = current["qi_required"]
        ceil  = nxt["qi_required"]
        pct   = min((doc["qi"] - floor) / (ceil - floor), 1.0)
        bar   = "█" * int(pct * 20) + "░" * (20 - int(pct * 20))
        prog  = f"`[{bar}]` {int(pct*100)}%  →  **{nxt['name']}** in {ceil - doc['qi']:,} Qi"
    else:
        prog  = "`[████████████████████]` **PEAK** — The Dao is complete."

    now         = datetime.now(timezone.utc).replace(tzinfo=None)
    status_line = "✅ Active"
    if doc.get("injured_until"):
        iu = datetime.fromisoformat(doc["injured_until"])
        if now < iu:
            mins = int((iu - now).total_seconds() / 60)
            status_line = f"🩸 Injured — **{mins}m** remaining"

    artifact_line = "None"
    if doc.get("equipped_artifact") and doc["equipped_artifact"] in RECIPES:
        artifact_line = f"⚔️ **{RECIPES[doc['equipped_artifact']]['name']}**"

    lines = [
        f"{re} **{target.display_name}** — {doc['rank']}",
        "",
        f"{E['aperture']} Qi: **{doc['qi']:,}** / {current['aperture']:,}",
        f"{E['soul_coin']} Souls: **{doc.get('souls', 0):,}**",
        f"{E['skull']} Deaths: **{doc.get('deaths', 0)}**",
        f"🍀 Luck: **{luck}**",
        "",
        f"📊 {prog}",
        "",
        f"⚕️ Status: {status_line}",
        f"⚔️ Artifact: {artifact_line}",
    ]

    await interaction.response.send_message(embed=dao_embed(
        f"{re} Cultivation Dossier", lines, color=0x0d1b2a
    ))

# ─────────────────────────────────────────────
# /rankings
# ─────────────────────────────────────────────
@tree.command(name="rankings", description="View the Top 10 Cultivators of Wonderland.")
async def rankings(interaction: discord.Interaction):
    await interaction.response.defer()
    top = list(cultivators.find().sort("qi", -1).limit(10))

    if not top:
        await interaction.followup.send(embed=dao_embed("📊 Rankings", [
            "> No cultivators registered. The void is empty.",
        ]))
        return

    lines = [f"{E['sect']} **Heavenly Rankings — Top Cultivators**", ""]
    for i, doc in enumerate(top, 1):
        m     = interaction.guild.get_member(int(doc["_id"]))
        name  = m.display_name if m else doc.get("username", "Unknown")
        re    = RANK_EMOJI.get(doc.get("rank", "Mortal"), "")
        medal = ["🥇", "🥈", "🥉"][i - 1] if i <= 3 else f"**#{i}**"
        lines.append(f"{medal} {re} **{name}** — {doc.get('rank','Mortal')} — {doc.get('qi',0):,} Qi")

    await interaction.followup.send(embed=dao_embed("📊 Heavenly Rankings", lines, color=0x1a0a2e))

# ─────────────────────────────────────────────
# /daily
# ─────────────────────────────────────────────
@tree.command(name="daily", description="Claim your daily Soul stipend from the Heavenly Treasury.")
async def daily(interaction: discord.Interaction):
    doc = get_cultivator(interaction.user.id, interaction.user.name)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if doc["last_daily"]:
        end = datetime.fromisoformat(doc["last_daily"]) + timedelta(hours=24)
        if now < end:
            hrs  = int((end - now).total_seconds() / 3600)
            mins = int(((end - now).total_seconds() % 3600) / 60)
            await interaction.response.send_message(embed=dao_embed("⏳ Daily Denied", [
                f"> Already claimed. Return in **{hrs}h {mins}m**.",
            ], color=0x4a4a6a), ephemeral=True)
            return

    luck         = get_effective_luck(doc)
    souls_gained = random.randint(50, 100) + (luck // 2)
    doc["souls"] = doc.get("souls", 0) + souls_gained
    doc["last_daily"] = now.isoformat()
    save_cultivator(doc)

    await interaction.response.send_message(embed=dao_embed("🏮 Daily Reward", [
        f"{E['soul_coin']} **{interaction.user.display_name}** receives the Heavenly Treasury's stipend.",
        "",
        f"> Souls gained: **+{souls_gained}**",
        f"> Total souls: **{doc['souls']:,}**",
        "> Return tomorrow for the next stipend.",
    ], color=0x004433))

# ─────────────────────────────────────────────
# /shop (Button UI)
# ─────────────────────────────────────────────
class ShopView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your shop session.", ephemeral=True)
            return False
        return True

    async def _buy(self, interaction: discord.Interaction, item_id: str):
        item = SHOP_ITEMS[item_id]
        doc  = get_cultivator(interaction.user.id, interaction.user.name)

        if doc.get("souls", 0) < item["cost"]:
            await interaction.response.send_message(embed=dao_embed("❌ Purchase Denied", [
                f"> **{item['name']}** costs **{item['cost']}** Souls.",
                f"> You have **{doc.get('souls', 0):,}** Souls. Insufficient.",
            ], color=0x8b0000), ephemeral=True)
            return

        doc["souls"] -= item["cost"]
        result = ""

        if item["effect"] == "gather_boost":
            doc["gather_boost"] = True
            result = "Next **/gather** yields double ingredients."
        elif item["effect"] == "luck_boost":
            doc["luck_boost"]       = item["value"]
            doc["luck_boost_until"] = (datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)).isoformat()
            result = f"🍀 Luck boosted by **+{item['value']}** for 24 hours."
        elif item["effect"] == "souls":
            doc["souls"] += item["value"]
            result = f"{E['soul_coin']} Received **{item['value']}** Souls."

        save_cultivator(doc)
        await interaction.response.send_message(embed=dao_embed("✅ Purchase Confirmed", [
            f"**{item['name']}** purchased.",
            f"> {result}",
            f"{E['soul_coin']} Remaining souls: **{doc['souls']:,}**",
        ], color=0x006644), ephemeral=True)

    @discord.ui.button(label="🧭 Gatherer's Compass (200)", style=discord.ButtonStyle.secondary)
    async def buy_compass(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._buy(interaction, "gather_boost")

    @discord.ui.button(label="🍀 Fortune Jade (500)", style=discord.ButtonStyle.success)
    async def buy_luck(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._buy(interaction, "luck_charm")

    @discord.ui.button(label="🏮 Soul Lantern (300)", style=discord.ButtonStyle.primary)
    async def buy_lantern(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._buy(interaction, "soul_lantern")

@tree.command(name="shop", description="Browse the Dao Merchant's wares.")
async def shop(interaction: discord.Interaction):
    doc   = get_cultivator(interaction.user.id, interaction.user.name)
    souls = doc.get("souls", 0)
    lines = [
        f"{E['soul_coin']} **{interaction.user.display_name}** — you have **{souls:,}** Souls.",
        "",
        f"🧭 **Gatherer's Compass** — 200 Souls",
        f"> Double ingredients on next /gather.",
        "",
        f"🍀 **Fortune Jade** — 500 Souls",
        f"> +5 Luck for 24 hours.",
        "",
        f"🏮 **Soul Lantern** — 300 Souls",
        f"> Grants 400 Souls directly.",
        "",
        f"> For pills, talismans, artifacts → **/recipes** & **/refine**",
    ]
    await interaction.response.send_message(
        embed=dao_embed(f"{E['scroll']} Soul Shop", lines, color=0x2a1a0e),
        view=ShopView(interaction.user.id)
    )

# ─────────────────────────────────────────────
# /sect_create
# ─────────────────────────────────────────────
@tree.command(name="sect_create", description="Create a Sect for 5,000 Souls. Requires Foundation Establishment.")
@app_commands.describe(name="Name of the Sect to establish.")
async def sect_create(interaction: discord.Interaction, name: str):
    doc = get_cultivator(interaction.user.id, interaction.user.name)
    rank_index = get_rank_index(doc.get("rank", get_rank_data(doc.get("qi", 0))["name"]))

    if rank_index < 2:
        await interaction.response.send_message(embed=denied("Foundation Establishment is required to create a Sect."), ephemeral=True)
        return

    if doc.get("souls", 0) < 5000:
        await interaction.response.send_message(embed=denied("Creating a Sect requires **5,000 Souls**."), ephemeral=True)
        return

    sect_name = name.strip()
    if not sect_name:
        await interaction.response.send_message(embed=denied("Sect name cannot be empty."), ephemeral=True)
        return

    sect_id = sect_name.lower()
    if sects.find_one({"_id": sect_id}):
        await interaction.response.send_message(embed=denied("A Sect with that name already exists."), ephemeral=True)
        return

    existing_sect = sects.find_one({"members": doc["_id"]})
    if existing_sect:
        await interaction.response.send_message(embed=denied("You already belong to a Sect."), ephemeral=True)
        return

    doc["souls"] -= 5000
    save_cultivator(doc)
    sects.insert_one({
        "_id": sect_id,
        "name": sect_name,
        "patriarch_id": doc["_id"],
        "members": [doc["_id"]],
        "vault": 0,
        "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
    })

    await interaction.response.send_message(embed=dao_embed(f"{E['sect']} Sect Established", [
        f"> **{sect_name}** has entered the Heavenly records.",
        f"> Patriarch: **{interaction.user.display_name}**",
        f"> Treasury offering paid: **5,000 Souls**",
    ], color=0x2a1a0e))
# ─────────────────────────────────────────────
# /sect_join, /sect_vault, /sect_distribute
# ─────────────────────────────────────────────
@tree.command(name="sect_join", description="Pledge your soul to a Sect.")
@app_commands.describe(name="The name of the Sect you wish to join.")
async def sect_join(interaction: discord.Interaction, name: str):
    doc = get_cultivator(interaction.user.id, interaction.user.name)
    if sects.find_one({"members": str(interaction.user.id)}):
        await interaction.response.send_message(embed=denied("You are already bound to a Sect."), ephemeral=True)
        return

    sect = sects.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
    if not sect:
        await interaction.response.send_message(embed=denied(f"The Sect '{name}' does not exist."), ephemeral=True)
        return

    sects.update_one({"_id": sect["_id"]}, {"$push": {"members": str(interaction.user.id)}})
    await interaction.response.send_message(embed=dao_embed(f"{E['sect']} Sect Joined", [
        f"**{interaction.user.display_name}** has joined the **{sect['name']}**.",
        f"> A 10% tithe of all duel winnings will flow to the Vault {E['soul_coin']}."
    ], color=0x00aaff))

@tree.command(name="sect_vault", description="View the wealth of your Sect.")
async def sect_vault(interaction: discord.Interaction):
    sect = sects.find_one({"members": str(interaction.user.id)})
    if not sect:
        await interaction.response.send_message(embed=denied("You belong to no Sect."), ephemeral=True)
        return

    await interaction.response.send_message(embed=dao_embed(f"{E['sect']} {sect['name']} Treasury", [
        f"**Vault Balance:** {sect.get('vault', 0):,} {E['soul_coin']}",
        f"**Total Members:** {len(sect['members'])}"
    ], color=0xffd700))

@tree.command(name="sect_distribute", description="[PATRIARCH] Distribute souls from the vault.")
@app_commands.describe(member="The member to receive souls", amount="Amount to send")
async def sect_distribute(interaction: discord.Interaction, member: discord.Member, amount: int):
    sect = sects.find_one({"patriarch_id": str(interaction.user.id)})
    if not sect:
        await interaction.response.send_message(embed=denied("Only a Patriarch may command the Treasury."), ephemeral=True)
        return

    if amount <= 0 or sect.get("vault", 0) < amount:
        await interaction.response.send_message(embed=denied("Insufficient souls in the Vault."), ephemeral=True)
        return

    if str(member.id) not in sect["members"]:
        await interaction.response.send_message(embed=denied("That individual is not a member of your Sect."), ephemeral=True)
        return

    sects.update_one({"_id": sect["_id"]}, {"$inc": {"vault": -amount}})
    cultivators.update_one({"_id": str(member.id)}, {"$inc": {"souls": amount}})
    await interaction.response.send_message(embed=dao_embed("Treasury Distribution", [
        f"The Patriarch bestowed **{amount:,}** {E['soul_coin']} upon **{member.display_name}**.",
        f"Remaining Balance: {sect['vault'] - amount:,} {E['soul_coin']}"
    ], color=0x00ffaa))

# ─────────────────────────────────────────────
# /set_logs (Admin-only)
# ─────────────────────────────────────────────
@tree.command(name="set_logs", description="[ADMIN] Set the channel for Heavenly Dao logs.")
@app_commands.describe(channel="Channel that should receive Heavenly Dao log embeds.")
async def set_logs(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.guild:
        await interaction.response.send_message(embed=denied("This command can only be used inside a server."), ephemeral=True)
        return

    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(embed=denied("Administrator permission is required."), ephemeral=True)
        return

    server_config.update_one(
        {"_id": str(interaction.guild_id)},
        {
            "$set": {
                "log_channel": channel.id,
                "updated_by": interaction.user.id,
                "updated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(),
            }
        },
        upsert=True,
    )

    await interaction.response.send_message(embed=dao_embed("✅ Logs Configured", [
        f"> Log channel set to {channel.mention}.",
        "> Future Heavenly Dao log events will be sent there.",
    ], color=0x006644), ephemeral=True)

# ─────────────────────────────────────────────
# /give (Riel-only)
# ─────────────────────────────────────────────
@tree.command(name="give", description="[SOVEREIGN ONLY] Adjust a cultivator's stats.")
@app_commands.describe(member="Target.", stat="qi / souls / luck", amount="Amount (negative to subtract).")
async def give(interaction: discord.Interaction, member: discord.Member, stat: str, amount: int):
    if interaction.user.name.lower() != OWNER_NAME:
        await interaction.response.send_message(embed=denied("Reserved for the Sovereign."), ephemeral=True)
        return

    stat = stat.lower()
    if stat not in ("qi", "souls", "luck"):
        await interaction.response.send_message(embed=denied("Invalid stat. Use `qi`, `souls`, or `luck`."), ephemeral=True)
        return

    doc       = get_cultivator(member.id, member.name)
    doc[stat] = max(0, doc.get(stat, 0) + amount)
    if stat == "qi":
        doc["rank"] = get_rank_data(doc["qi"])["name"]
    if stat == "luck":
        doc["luck"] = min(doc["luck"], 100)
    save_cultivator(doc)

    await interaction.response.send_message(embed=dao_embed("👑 Sovereign Decree", [
        f"> **{member.display_name}** — `{stat.upper()}` adjusted.",
        f"> Change: **{'+' if amount >= 0 else ''}{amount}**",
        f"> New value: **{doc[stat]}**",
    ], color=0x004466), ephemeral=True)

# ─────────────────────────────────────────────
# RUN
# ─────────────────────────────────────────────
bot.run(BOT_TOKEN)
keep_alive()
