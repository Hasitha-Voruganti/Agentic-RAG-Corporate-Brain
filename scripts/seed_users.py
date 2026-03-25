"""
scripts/seed_users.py — Create default test users for all roles
Run: python scripts/seed_users.py
"""
import asyncio
import httpx

BASE = "http://localhost:8000/api"

USERS = [
    {"username": "admin",   "email": "admin@corp.com",   "password": "Admin@123",   "role": "admin"},
    {"username": "hr_user", "email": "hr@corp.com",      "password": "HR@123",      "role": "hr"},
    {"username": "fin_user","email": "finance@corp.com", "password": "Finance@123", "role": "finance"},
    {"username": "employee","email": "employee@corp.com","password": "Employee@123","role": "general"},
]


async def seed():
    async with httpx.AsyncClient() as client:
        for user in USERS:
            try:
                r = await client.post(f"{BASE}/auth/register", json=user)
                if r.status_code == 200:
                    print(f"✅ Created user: {user['username']} ({user['role']})")
                else:
                    print(f"⚠️  {user['username']}: {r.json()}")
            except Exception as e:
                print(f"❌ Error for {user['username']}: {e}")

    print("\nTest credentials:")
    for u in USERS:
        print(f"  {u['role']:10} — username: {u['username']}, password: {u['password']}")


if __name__ == "__main__":
    asyncio.run(seed())