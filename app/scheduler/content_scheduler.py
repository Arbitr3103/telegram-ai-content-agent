"""
Планировщик публикаций по расписанию
Вторник и Четверг, 09:00-12:00 с рандомным временем
"""
import asyncio
import random
import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.utils.post_types import get_random_publish_time, get_rotation_status

logger = logging.getLogger(__name__)


class ContentScheduler:
    """Планировщик публикации контента"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """Настройка задач планировщика"""

        # Задача планирования на следующий день (запускается каждый день в 00:05)
        self.scheduler.add_job(
            self._schedule_next_post,
            CronTrigger(hour=0, minute=5),
            id='daily_schedule_check',
            name='Check and schedule next post'
        )

        logger.info("Scheduler jobs configured")

    async def _schedule_next_post(self):
        """Проверить, нужно ли планировать пост на сегодня"""
        today = datetime.now()
        weekday = today.weekday()  # 0=Пн, 1=Вт, 2=Ср, 3=Чт, 4=Пт, 5=Сб, 6=Вс

        # Публикуем только во Вторник (1) и Четверг (3)
        if weekday not in [1, 3]:
            logger.info(f"Today is {today.strftime('%A')}, no post scheduled")
            return

        # Генерируем случайное время между 09:00 и 12:00
        hour, minute = get_random_publish_time()

        # Планируем публикацию
        run_time = today.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Если время уже прошло, не планируем
        if run_time < datetime.now():
            logger.warning(f"Scheduled time {run_time} already passed")
            return

        self.scheduler.add_job(
            self._run_pipeline,
            'date',
            run_date=run_time,
            id=f'post_{today.strftime("%Y%m%d")}',
            name=f'Publish post at {hour:02d}:{minute:02d}',
            replace_existing=True
        )

        logger.info(f"📅 Post scheduled for {run_time.strftime('%Y-%m-%d %H:%M')}")

    async def _run_pipeline(self):
        """Запуск пайплайна публикации"""
        from app.main import ContentPipeline

        logger.info("=== Running scheduled post ===")

        pipeline = ContentPipeline()
        try:
            await pipeline.run_once(publish=True)
        finally:
            await pipeline.close()

    def start(self):
        """Запуск планировщика"""
        self.scheduler.start()
        logger.info("Content scheduler started")

        # Сразу проверяем, нужно ли запланировать на сегодня
        asyncio.create_task(self._schedule_next_post())

    def stop(self):
        """Остановка планировщика"""
        self.scheduler.shutdown()
        logger.info("Content scheduler stopped")

    def get_status(self) -> str:
        """Получить статус планировщика"""
        jobs = self.scheduler.get_jobs()
        status = "📅 Статус планировщика:\n\n"

        if not jobs:
            status += "Нет запланированных задач\n"
        else:
            for job in jobs:
                next_run = job.next_run_time
                if next_run:
                    status += f"• {job.name}: {next_run.strftime('%Y-%m-%d %H:%M')}\n"
                else:
                    status += f"• {job.name}: не запланировано\n"

        status += "\n" + get_rotation_status()
        return status

    def schedule_now(self, delay_seconds: int = 10):
        """Запланировать публикацию через N секунд (для тестирования)"""
        run_time = datetime.now() + timedelta(seconds=delay_seconds)

        self.scheduler.add_job(
            self._run_pipeline,
            'date',
            run_date=run_time,
            id='immediate_post',
            name='Immediate post',
            replace_existing=True
        )

        logger.info(f"Post scheduled in {delay_seconds} seconds")
        return run_time


async def run_scheduler():
    """Запуск планировщика как основного процесса"""
    scheduler = ContentScheduler()
    scheduler.start()

    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║     Content Scheduler                                     ║
    ║     Вт/Чт 09:00-12:00 (рандомное время)                  ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    print(scheduler.get_status())

    # Держим процесс запущенным
    try:
        while True:
            await asyncio.sleep(3600)  # Проверка каждый час
    except KeyboardInterrupt:
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(run_scheduler())
