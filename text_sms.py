import asyncio
import sys
sys.path.insert(0, '.')

from services.sms import send_sms

async def test():
    result = await send_sms('08022562432', 'KoboSats test SMS!')
    print('Sent:', result)

asyncio.run(test())