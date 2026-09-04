import edge_tts
import asyncio

TEXT = "Namaste, yeh TaazaBhav hai. Aaj Uttar Pradesh mein pyaz ka bhav teen hazar rupaye prati quintal hai."

async def main():
    male = edge_tts.Communicate(TEXT, "hi-IN-MadhurNeural")
    await male.save("sample_male.mp3")
    print("Male sample ready: sample_male.mp3")

    female = edge_tts.Communicate(TEXT, "hi-IN-SwaraNeural")
    await female.save("sample_female.mp3")
    print("Female sample ready: sample_female.mp3")

asyncio.run(main())