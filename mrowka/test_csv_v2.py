import asyncio
import mrowka_data
import dc

async def main():
    coll = await mrowka_data.MrowkaShoeCollection.from_csv("storage/test_user.csv")
    print("SHOES:", coll.shoes)
    try:
        user = dc.User(id=123, name="test")
        item = await coll.take_one_order_item("test", "test", 123, 123, user)
        print("ITEM:", item)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
