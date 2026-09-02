from google_auth_oauthlib.flow import InstalledAppFlow
import pickle

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_secrets_file(
    "client_secret.json", SCOPES
)
creds = flow.run_local_server(port=0)

with open("token.pickle", "wb") as f:
    pickle.dump(creds, f)

print("Authorization complete — token.pickle saved.")