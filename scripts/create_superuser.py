from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

# Example of how to create a user record
username = "animeshdas738"
password = "Agent@123"
hashed_password = get_password_hash(password)

print(f"INSERT INTO users (username, hashed_password, is_superuser) VALUES ('{username}', '{hashed_password}', TRUE);")
