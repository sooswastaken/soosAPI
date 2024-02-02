from enum import Enum
from discord.ext import commands


class BucketType(Enum):
    ip = 0

    def get_key(self, request):
        print(request.headers.get("cf-connecting-ip"))
        return request.headers.get("cf-connecting-ip")

    def __call__(self, request):
        return self.get_key(request)


ratelimiting = commands.CooldownMapping.from_cooldown(200, 60, BucketType.ip)


async def ratelimiter(request):
    bucket = ratelimiting.get_bucket(request)
    retry_after = bucket.update_rate_limit()
    return retry_after
