from dotenv import load_dotenv
import os

# Load environment variables from the .env file
load_dotenv()

# Retrieve environment variables
db_host = os.getenv("DATABASE_HOST")
db_user = os.getenv("DATABASE_USER")
db_password = os.getenv("DATABASE_PASSWORD")
db_name = os.getenv("DATABASE_NAME")
db_port = os.getenv("DATABASE_PORT")

# Print values for debugging
print("Database Host:", db_host)
print("Database User:", db_user)
print("Database Password:", db_password)
print("Database Name:", db_name)
print("Database Port:", db_port)
