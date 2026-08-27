import asyncio
import random
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder

BOT_TOKEN = "8872287810:AAFmI0W22D1amaaThUCdE5mIwx1WYia1_XY"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Размеры мира в блоках (ширина х высота)
WIDTH = 9
HEIGHT = 8

# Эмодзи блоков
SKY = "🟦"
CLOUD = "☁️"
GRASS = "🟩"
DIRT = "🟫"
STONE = "⬛"
DIAMOND = "💎"
PLAYER = "😳"

# Блоки для строительства
BUILD_BLOCKS = [DIRT, STONE, GRASS, DIAMOND]

games = {}


def generate_world():
    world = []
    for y in range(HEIGHT):
        row = []
        for x in range(WIDTH):
            if y < 2:
                # Небо и случайные облака
                row.append(CLOUD if random.random() < 0.2 else SKY)
            elif y == 2:
                # Поверхность — трава
                row.append(GRASS)
            elif y in (3, 4):
                # Под землей — грязь
                row.append(DIRT)
            else:
                # Глубоко — камень и редкие алмазы
                row.append(DIAMOND if random.random() < 0.15 else STONE)
        world.append(row)
    return world


def get_keyboard(game):
    builder = InlineKeyboardBuilder()

    # Стрелки управления
    builder.button(text="⬅️ Left", callback_data="left")
    builder.button(text="⬆️ Jump", callback_data="jump")
    builder.button(text="➡️ Right", callback_data="right")

    # Действия
    builder.button(text="⛏️ Ломать под собой", callback_data="mine")
    builder.button(
        text=f"📦 Поставить {game['selected_block']}", callback_data="place"
    )

    # Переключение блока для стройки
    builder.button(
        text="🔄 Выбрать другой блок", callback_data="switch_block"
    )

    builder.adjust(3, 2, 1)
    return builder.as_markup()


def render_world(game):
    # Копируем сетку мира
    rendered = [row[:] for row in game["world"]]

    px, py = game["px"], game["py"]

    # Рисуем игрока
    rendered[py][px] = PLAYER

    world_str = "\n".join("".join(row) for row in rendered)
    block_name = game["selected_block"]

    return (
        f"⛏️ **MINECRAFT TELEGRAM**\n"
        f"Инвентарь: Алмазов найдено: `{game['diamonds']}`\n"
        f"Выбран блок: {block_name}\n\n"
        f"{world_str}"
    )


@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id

    games[user_id] = {
        "world": generate_world(),
        "px": WIDTH // 2,
        "py": 1,  # Спавнится над травой
        "selected_block": DIRT,
        "diamonds": 0,
    }

    game = games[user_id]
    await message.answer(
        render_world(game),
        parse_mode="Markdown",
        reply_markup=get_keyboard(game),
    )


@dp.callback_query(
    F.data.in_({"left", "right", "jump", "mine", "place", "switch_block"})
)
async def handle_action(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if user_id not in games:
        await callback.answer(
            "Мир не найден! Напиши /start для создания.", show_alert=True
        )
        return

    game = games[user_id]
    action = callback.data
    px, py = game["px"], game["py"]
    world = game["world"]

    # 1. Движение Влево / Вправо
    if action == "left" and px > 0:
        game["px"] -= 1
    elif action == "right" and px < WIDTH - 1:
        game["px"] += 1

    # 2. Прыжок / Подъем вверх
    elif action == "jump":
        if py > 0:
            game["py"] -= 1

    # 3. Гравитация (падение, если под ногами воздух/небо)
    # Проверяем после любого перемещения
    px, py = game["px"], game["py"]
    if py < HEIGHT - 1 and world[py + 1][px] in (SKY, CLOUD):
        game["py"] += 1

    # 4. Копать блок под собой
    elif action == "mine":
        if py < HEIGHT - 1:
            target_block = world[py + 1][px]
            if target_block != SKY:
                if target_block == DIAMOND:
                    game["diamonds"] += 1
                    await callback.answer("💎 Ты копанул алмаз!", show_alert=False)

                world[py + 1][px] = SKY
                game["py"] += 1  # Падаем в выкопанную яму

    # 5. Поставить блок под себя (или застроить под собой)
    elif action == "place":
        if py > 0 and world[py][px] in (SKY, CLOUD):
            world[py][px] = game["selected_block"]
            game["py"] -= 1  # Игрок поднимается на поставленный блок

    # 6. Сменить строительный блок
    elif action == "switch_block":
        curr_idx = BUILD_BLOCKS.index(game["selected_block"])
        next_idx = (curr_idx + 1) % len(BUILD_BLOCKS)
        game["selected_block"] = BUILD_BLOCKS[next_idx]

    try:
        await callback.message.edit_text(
            render_world(game),
            parse_mode="Markdown",
            reply_markup=get_keyboard(game),
        )
    except Exception:
        pass

    await callback.answer()


async def main():
    print("Майнкрафт бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
