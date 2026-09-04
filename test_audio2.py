from make_audio import make_audio

text = "Namaste, yeh TaazaBhav hai. Aaj Uttar Pradesh mein pyaz ka bhav teen hazar rupaye prati quintal hai."
make_audio(text, out_path="final_test.mp3", lang="hi")
print("Audio ban gaya: final_test.mp3")