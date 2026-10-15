import asyncio, random
from datetime import datetime, timezone
from sqlalchemy.orm.attributes import flag_modified
import logging
from .db import SessionLocal
from .models import NPC, Message, Event, Location, Weather
from .ai import generate_reply, FALLBACK_REPLY
from .config import PLAYER_NAME

logger = logging.getLogger(__name__)

DEFAULT_NPC_PROFILES = [
    {"name": "Анна", "profession": "Бариста", "personality": "дружелюбная, болтливая, оптимист"},
    {"name": "Пётр", "profession": "Полицейский", "personality": "строгий, справедливый, серьёзный"},
    {"name": "Оля", "profession": "Журналист", "personality": "любопытная, амбициозная, чуть драматична"},
    {"name": "Игорь", "profession": "Таксист", "personality": "шутник, практичный, наблюдательный"},
    {"name": "Мария", "profession": "Учитель", "personality": "терпеливая, заботливая"},
    {"name": "Сергей", "profession": "Программист", "personality": "скромный, аналитичный, любит кофе"},
    {"name": "Лена", "profession": "Врач", "personality": "серьёзная, эмпатичная"},
    {"name": "Дмитрий", "profession": "Механик", "personality": "рукастый, немного ворчлив"},
    {"name": "Ирина", "profession": "Художник", "personality": "романтичная, креативная"},
    {"name": "Николай", "profession": "Продавец", "personality": "прозорливый, хитрый"},
    {"name": "Виктория", "profession": "Студентка", "personality": "энергичная, соцсети-ориентированная"},
    {"name": "Алексей", "profession": "Пекарь", "personality": "теплый, гостеприимный"},
    {"name": "Галина", "profession": "Пенсионерка", "personality": "ворчливая, мудрая"},
]

def now_ts():
    return datetime.now(timezone.utc).isoformat()


def save_state(npc, state):
    """Записывает state и помечает JSON-поле изменённым, чтобы SQLAlchemy сохранил мутации."""
    npc.state = state
    flag_modified(npc, 'state')


class NPCManager:
    def __init__(self, broadcaster):
        self.broadcaster = broadcaster
        self.tasks = []
        self.seeded = False
        self.mayor = None

    def seed(self):
        db = SessionLocal()
        try:
            existing = db.query(NPC).count()
            if existing >= len(DEFAULT_NPC_PROFILES):
                return
            existing_names = {n for (n,) in db.query(NPC.name).all()}
            npcs = []
            for p in DEFAULT_NPC_PROFILES:
                if p['name'] in existing_names:
                    continue
                relations = {other['name']: random.choice(['friend', 'neutral', 'enemy']) for other in DEFAULT_NPC_PROFILES if other['name'] != p['name']}
                npcs.append(NPC(
                    name=p['name'],
                    profession=p['profession'],
                    personality=p['personality'],
                    state={"mood": "neutral", "money": 100, "location": "home", "relations": relations, "business": None},
                    x=random.random() * 800,
                    y=random.random() * 400
                ))
            db.add_all(npcs)
            db.commit()
        finally:
            db.close()
        self.seeded = True

    async def add_event(self, db, title, content):
        ev = Event(title=title, content=content, ts=now_ts())
        db.add(ev)
        db.commit()
        await self.broadcaster('news', {"title": ev.title, "content": ev.content, "ts": ev.ts})
        return ev

    async def npc_loop(self, npc_id):
        while True:
            await asyncio.sleep(random.randint(10, 30))  # Замедление перемещений
            try:
                await self.npc_step(npc_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Ошибка в цикле NPC %s", npc_id)

    async def npc_step(self, npc_id):
        # Свежая сессия на каждую итерацию, NPC перечитывается из БД
        db = SessionLocal()
        try:
            npc = db.get(NPC, npc_id)
            if npc is None:
                return
            weather = db.query(Weather).first().current
            actions = ['move', 'chat', 'work', 'shop', 'business', 'disaster']
            if weather == 'rainy':
                actions = ['move'] if random.random() > 0.5 else actions  # Чаще дома
            action = random.choice(actions)
            state = npc.state
            if action == 'move':
                locations = db.query(Location).all()
                target_loc = random.choice(locations)
                if weather == 'sunny' and random.random() < 0.3:
                    target_loc = db.query(Location).filter_by(name='park').first() or target_loc  # Предпочтение парку в солнце
                npc.x = random.uniform(target_loc.x_min, target_loc.x_max)
                npc.y = random.uniform(target_loc.y_min, target_loc.y_max)
                state['location'] = target_loc.name
                save_state(npc, state)
                db.commit()
                await self.broadcaster('map_update', {"id": npc.id, "x": npc.x, "y": npc.y, "location": target_loc.name})
            elif action == 'chat':
                others = db.query(NPC).filter(NPC.id != npc.id).all()
                if not others:
                    return  # Только пропуск итерации: цикл в npc_loop продолжается
                other = random.choice(others)
                relation = state['relations'].get(other.name, 'neutral')
                system = f"Ты {npc.name}, {npc.personality}. Отношение к {other.name}: {relation}. Общайся коротко."
                reply = await generate_reply(system, [], f"Привет, {other.name}! Как дела?")
                db.add(Message(npc_id=npc.id, role='assistant', content=reply))
                db.commit()
                await self.add_event(db, f"Разговор: {npc.name} и {other.name}", reply)
                if 'злость' in reply.lower():
                    state['relations'][other.name] = 'enemy'
                elif 'дружба' in reply.lower():
                    state['relations'][other.name] = 'friend'
                save_state(npc, state)
                db.commit()
            elif action == 'work' and state.get('location') == 'work':
                state['money'] += random.randint(10, 20)
                save_state(npc, state)
                db.commit()
                await self.broadcaster('state_update', {"id": npc.id, "state": npc.state})
            elif action == 'shop' and state.get('location') == 'shop':
                spent = random.randint(5, 15)
                state['money'] = max(0, state['money'] - spent)
                save_state(npc, state)
                db.commit()
                await self.add_event(db, f"Покупка: {npc.name}", f"{npc.name} купил вещи на {spent} монет.")
            elif action == 'business':
                if not state.get('business'):
                    system = f"Ты {npc.name}, {npc.profession}. Придумай бизнес-идею."
                    idea = await generate_reply(system, [], "Предложи идею бизнеса.")
                    if idea == FALLBACK_REPLY:
                        return  # ИИ недоступен — не сохраняем заглушку как бизнес
                    state['business'] = idea
                    save_state(npc, state)
                    db.commit()
                    await self.add_event(db, f"Новый бизнес: {npc.name}", idea)
                else:
                    state['money'] += random.randint(5, 10)  # Доход от бизнеса
                    save_state(npc, state)
                    db.commit()
            elif action == 'disaster':
                if random.random() < 0.1:  # Редко
                    disaster = random.choice(['fire', 'theft'])
                    system = f"Генерируй событие катастрофы для {npc.name}."
                    desc = await generate_reply(system, [], f"Опиши {disaster}.")
                    await self.add_event(db, f"Катастрофа: {disaster} у {npc.name}", desc)
                    state['money'] = max(0, state['money'] - random.randint(20, 50))  # Убыток
                    save_state(npc, state)
                    db.commit()
        finally:
            db.close()

    async def weather_loop(self):
        while True:
            await asyncio.sleep(300)  # Каждые 5 мин
            db = SessionLocal()
            try:
                weather = db.query(Weather).first()
                weather.current = random.choice(['sunny', 'rainy', 'stormy'])
                db.commit()
                ev = Event(title="Погода изменилась", content=f"Теперь {weather.current}.", ts=now_ts())
                db.add(ev)
                db.commit()
                # Поле weather — машиночитаемое значение для фронтенда
                await self.broadcaster('news', {"title": ev.title, "content": ev.content, "ts": ev.ts, "weather": weather.current})
            except Exception:
                logger.exception("Ошибка в цикле погоды")
            finally:
                db.close()

    def run_election(self, db):
        npcs = db.query(NPC).all()
        candidates = [n.name for n in npcs] + [PLAYER_NAME]
        votes = {c: 0 for c in candidates}
        for _ in npcs:
            votes[random.choice(candidates)] += 1
        winner = max(votes, key=votes.get)
        self.mayor = winner
        return winner, votes[winner]

    async def election_loop(self):
        while True:
            await asyncio.sleep(300)  # Каждые 5 мин
            db = SessionLocal()
            try:
                winner, count = self.run_election(db)
                ev = Event(title="Выборы мэра", content=f"Новый мэр: {winner} с {count} голосами.", ts=now_ts())
                db.add(ev)
                db.commit()
                await self.broadcaster('news', {"title": ev.title, "content": ev.content, "ts": ev.ts,
                                                "winner": winner, "is_player": winner == PLAYER_NAME})
            except Exception:
                logger.exception("Ошибка в цикле выборов")
            finally:
                db.close()

    async def start(self):
        self.seed()
        db = SessionLocal()
        try:
            npc_ids = [i for (i,) in db.query(NPC.id).all()]
        finally:
            db.close()
        for npc_id in npc_ids:
            self.tasks.append(asyncio.create_task(self.npc_loop(npc_id)))
        self.tasks.append(asyncio.create_task(self.weather_loop()))
        self.tasks.append(asyncio.create_task(self.election_loop()))

    def stop(self):
        for t in self.tasks:
            t.cancel()
        self.tasks = []
