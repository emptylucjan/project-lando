import asyncio
import mrowka_data

async def main():
    coll = await mrowka_data.MrowkaShoeCollection.from_csv("storage/test_user.csv")
    print("SHOES:", coll.shoes)
    
if __name__ == "__main__":
    asyncio.run(main())
